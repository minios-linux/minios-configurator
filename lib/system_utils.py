#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System utilities for MiniOS Configurator
Handles system data collection and availability checks.

Copyright (C) 2025 MiniOS Linux
Author: crims0n <crims0n@minios.dev>
"""

import subprocess
from typing import Set, Dict

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
    Read available locales from system, filtered to show only UTF-8 locales.
    """
    locales = set()
    try:
        with open('/usr/share/i18n/SUPPORTED', encoding='utf-8') as f:
            for line in f:
                parts = line.split()
                if parts and parts[0].endswith('.UTF-8'):
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

# Mapping from cmdline parameters to config.conf keys
CMDLINE_TO_CONFIG_MAP = {
    # User settings
    'live-config.username': 'LIVE_USERNAME',
    'username': 'LIVE_USERNAME',
    'live-config.user-fullname': 'LIVE_USER_FULLNAME',
    'user-fullname': 'LIVE_USER_FULLNAME',
    'live-config.user-default-groups': 'LIVE_USER_DEFAULT_GROUPS',
    'user-default-groups': 'LIVE_USER_DEFAULT_GROUPS',
    'live-config.user-password-crypted': 'LIVE_USER_PASSWORD_CRYPTED',
    'user-password-crypted': 'LIVE_USER_PASSWORD_CRYPTED',
    'live-config.root-password-crypted': 'LIVE_ROOT_PASSWORD_CRYPTED',
    'root-password-crypted': 'LIVE_ROOT_PASSWORD_CRYPTED',
    'live-config.link-user-dirs': 'LIVE_LINK_USER_DIRS',
    'link-user-dirs': 'LIVE_LINK_USER_DIRS',
    'live-config.bind-user-dirs': 'LIVE_BIND_USER_DIRS',
    'bind-user-dirs': 'LIVE_BIND_USER_DIRS',
    'live-config.user-dirs-path': 'LIVE_USER_DIRS_PATH',
    'user-dirs-path': 'LIVE_USER_DIRS_PATH',
    # System settings
    'live-config.noroot': 'LIVE_CONFIG_NOROOT',
    'noroot': 'LIVE_CONFIG_NOROOT',
    'live-config.hostname': 'LIVE_HOSTNAME',
    'hostname': 'LIVE_HOSTNAME',
    'live-config.locales': 'LIVE_LOCALES',
    'locales': 'LIVE_LOCALES',
    'live-config.timezone': 'LIVE_TIMEZONE',
    'timezone': 'LIVE_TIMEZONE',
    'default-target': 'DEFAULT_TARGET',
    'default_target': 'DEFAULT_TARGET',
    'enable-services': 'ENABLE_SERVICES',
    'enable_services': 'ENABLE_SERVICES',
    'disable-services': 'DISABLE_SERVICES',
    'disable_services': 'DISABLE_SERVICES',
    # Keyboard settings
    'live-config.keyboard-model': 'LIVE_KEYBOARD_MODEL',
    'keyboard-model': 'LIVE_KEYBOARD_MODEL',
    'live-config.keyboard-layouts': 'LIVE_KEYBOARD_LAYOUTS',
    'keyboard-layouts': 'LIVE_KEYBOARD_LAYOUTS',
    'live-config.keyboard-options': 'LIVE_KEYBOARD_OPTIONS',
    'keyboard-options': 'LIVE_KEYBOARD_OPTIONS',
    'live-config.keyboard-variants': 'LIVE_KEYBOARD_VARIANTS',
    'keyboard-variants': 'LIVE_KEYBOARD_VARIANTS',
    # Advanced settings
    'live-config.module-mode': 'LIVE_MODULE_MODE',
    'module-mode': 'LIVE_MODULE_MODE',
    'live-config.debug': 'LIVE_CONFIG_DEBUG',
    'debug': 'LIVE_CONFIG_DEBUG',
}

def parse_cmdline_params() -> Dict[str, str]:
    """
    Parse /proc/cmdline and extract live-config parameters.

    Returns a dictionary mapping config.conf keys to their values
    extracted from the kernel command line.
    """
    config_params = {}

    try:
        with open('/proc/cmdline', 'r') as f:
            cmdline = f.read().strip()
    except (IOError, OSError):
        return config_params

    # Split cmdline into individual parameters
    for param in cmdline.split():
        # Check for parameters with values (key=value)
        if '=' in param:
            key, value = param.split('=', 1)
            if key in CMDLINE_TO_CONFIG_MAP:
                config_key = CMDLINE_TO_CONFIG_MAP[key]
                config_params[config_key] = value
        # Check for boolean flags (just key, no value)
        else:
            if param in CMDLINE_TO_CONFIG_MAP:
                config_key = CMDLINE_TO_CONFIG_MAP[param]
                # Boolean flags are set to 'true'
                config_params[config_key] = 'true'

    return config_params
