#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration utilities for MiniOS Configurator
Handles config file reading and writing.

Copyright (C) 2025 MiniOS Linux
Author: crims0n <crims0n@minios.dev>
"""

import os
import re
import shlex
import stat
import sys
import gettext
import tempfile
from typing import Dict

# Add lib directory to Python path
sys.path.insert(0, '/usr/lib/minios-configurator')

from password_utils import PASSWORD_FIELD_MAP, hash_system_password

# Internationalization
APP_NAME = 'minios-configurator'
LOCALE_DIRECTORY = '/usr/share/locale'
gettext.bindtextdomain(APP_NAME, LOCALE_DIRECTORY)
gettext.textdomain(APP_NAME)
_ = gettext.gettext

def load_config(config_file_path: str) -> Dict[str, str]:
    """
    Load configuration from file.
    """
    config_values = {}
    try:
        # Configuration is privileged input; never follow an attacker-controlled link.
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(config_file_path, flags)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise ValueError(_('Config file must be a regular file.'))
        with os.fdopen(fd, encoding='utf-8') as f:
            for line in f:
                match = re.match(r"^([A-Z0-9_]+)=(.*)$", line.rstrip('\n'))
                if match:
                    key = match.group(1)
                    raw = match.group(2)
                    try:
                        parts = shlex.split(raw, comments=False, posix=True)
                        val = ''.join(parts) if parts else ''
                    except ValueError:
                        val = raw
                    config_values[key] = val
    except Exception as e:
        raise Exception(_('Failed to load config: {}').format(e))
    return config_values

def save_config(config_file_path: str, config_values: Dict[str, str], updated: Dict[str, str]) -> None:
    """
    Save configuration to file.
    """
    try:
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
        source_fd = os.open(config_file_path, flags)
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode):
            os.close(source_fd)
            raise ValueError(_('Config file must be a regular file.'))
        source_xattrs = {
            name: os.getxattr(source_fd, name)
            for name in os.listxattr(source_fd)
        }
        with os.fdopen(source_fd, encoding='utf-8') as f:
            orig = f.read().splitlines()
        
        out = []
        seen = set()
        replacements = dict(updated)

        for fld, encoded in PASSWORD_FIELD_MAP.items():
            password = replacements.pop(fld, '')
            if password:
                replacements[encoded] = hash_system_password(password)

        def assignment(key, value):
            # POSIX-shell safe single-quoted value, including embedded apostrophes.
            escaped = str(value).replace("'", "'\\''")
            return "{}='{}'".format(key, escaped)

        for line in orig:
            match = re.match(r"^([A-Z0-9_]+)=", line)
            if not match:
                out.append(line)
                continue
            
            k = match.group(1)
            seen.add(k)

            if k in replacements:
                out.append(assignment(k, replacements[k]))
            else:
                out.append(line)

        for key, value in replacements.items():
            if key not in seen:
                out.append(assignment(key, value))

        directory = os.path.dirname(os.path.abspath(config_file_path))
        fd, temporary_path = tempfile.mkstemp(prefix='.config.conf.', dir=directory)
        try:
            try:
                os.fchown(fd, source_stat.st_uid, source_stat.st_gid)
            except PermissionError:
                pass
            os.fchmod(fd, source_stat.st_mode & 0o7777)
            # ACLs and SELinux labels are stored as extended attributes.
            for name, value in source_xattrs.items():
                os.setxattr(fd, name, value)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                fd = -1
                f.write("\n".join(out) + "\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary_path, config_file_path)
            directory_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if fd >= 0:
                os.close(fd)
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    except Exception as e:
        raise Exception(_('Failed to update config: {}').format(e))

def process_services_field(text: str) -> str:
    """
    Process comma-separated service names without forcing an init-specific suffix.
    """
    parts = [s.strip() for s in text.split(',') if s.strip()]
    return ','.join(parts)

def normalize_default_target(value: str) -> str:
    """
    Normalize default boot target aliases to canonical systemd target names.
    """
    mapping = {
        'graphical': 'graphical.target',
        'graphical.target': 'graphical.target',
        'multi-user': 'multi-user.target',
        'multi-user.target': 'multi-user.target',
        'rescue': 'rescue.target',
        'rescue.target': 'rescue.target',
    }
    return mapping.get(value, value)
