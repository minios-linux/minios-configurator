#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System utilities for MiniOS Configurator
Handles system data collection and availability checks.

Copyright (C) 2025 MiniOS Linux
Author: crims0n <crims0n@minios.dev>
"""

import subprocess
from typing import Set

try:
    from zoneinfo import available_timezones
except ImportError:
    import os
    def available_timezones():
        """
        Fallback implementation for systems without zoneinfo.
        """
        tzdir = '/usr/share/zoneinfo'
        zones = set()
        for root, dirs, files in os.walk(tzdir):
            for file in files:
                rel = os.path.relpath(os.path.join(root, file), tzdir)
                zones.add(rel)
        return zones

def read_available_locales() -> Set[str]:
    """
    Read available locales from system.
    """
    locales = set()
    try:
        with open('/usr/share/i18n/SUPPORTED', encoding='utf-8') as f:
            for line in f:
                parts = line.split()
                if parts:
                    locales.add(parts[0])
    except Exception:
        pass
    return locales

def read_available_services() -> Set[str]:
    """
    Read available systemd services.
    """
    services = set()
    try:
        output = subprocess.check_output(
            ['systemctl', 'list-unit-files', '--type=service', '--no-legend', '--no-pager'],
            text=True
        )
        for line in output.splitlines():
            services.add(line.split()[0])
    except Exception:
        pass
    return services

def get_available_timezones() -> Set[str]:
    """
    Get available timezones.
    """
    return available_timezones()
