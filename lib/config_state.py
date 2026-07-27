#!/usr/bin/env python3
"""Non-graphical state model for MiniOS Configurator."""

import gettext
from typing import Dict, Iterable, List


_ = gettext.gettext


class ConfigState:
    """Track persisted, inherited, and edited values without GTK dependencies."""

    def __init__(self, source: Dict[str, str], inherited: Dict[str, str] = None,
                 password_fields: Iterable[str] = ("USER_PASSWORD", "ROOT_PASSWORD")):
        self.source = dict(source)
        self.inherited = dict(inherited or {})
        self._baseline = dict(self.source)
        self._baseline.update(self.inherited)
        self.current = dict(self._baseline)
        self.password_fields = set(password_fields)
        for key in self.password_fields:
            self.current[key] = ""
            self._baseline[key] = ""

    def get(self, key: str, default: str = "") -> str:
        return self.current.get(key, default)

    def set(self, key: str, value: str) -> None:
        self.current[key] = value

    def set_default(self, key: str, value: str) -> None:
        """Set a UI default without reporting it as a user edit."""
        if not self.current.get(key):
            self.current[key] = value
            self._baseline[key] = value

    def update(self, values: Dict[str, str]) -> None:
        self.current.update(values)

    @property
    def dirty_keys(self) -> List[str]:
        keys = set(self.current) | set(self._baseline)
        return sorted(key for key in keys if self.current.get(key, "") != self._baseline.get(key, ""))

    @property
    def dirty_count(self) -> int:
        return len(self.dirty_keys)

    def reset(self) -> None:
        self.current = dict(self._baseline)

    def changes(self) -> Dict[str, str]:
        return {key: self.current.get(key, "") for key in self.dirty_keys}

    def diff(self) -> List[Dict[str, str]]:
        result = []
        for key in self.dirty_keys:
            if key in self.password_fields:
                before = _("Password unchanged")
                after = _("Password will be changed") if self.current.get(key) else _("Password unchanged")
            else:
                before = self._baseline.get(key, "")
                after = self.current.get(key, "")
            result.append({"key": key, "before": before, "after": after,
                           "inherited": key in self.inherited})
        return result

    def mark_saved(self, persisted: Dict[str, str] = None) -> None:
        if persisted is not None:
            self.source = dict(persisted)
        for key in self.dirty_keys:
            if key not in self.password_fields:
                self._baseline[key] = self.current.get(key, "")
        for key in self.password_fields:
            self.current[key] = ""
            self._baseline[key] = ""
