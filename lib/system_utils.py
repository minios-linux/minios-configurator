#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System utilities for MiniOS Configurator
Handles system data collection and availability checks.

Copyright (C) 2025 MiniOS Linux
Author: crims0n <crims0n@minios.dev>
"""

import subprocess
import os
import locale
import socket
from typing import Set, Dict


# This marker is created by a crypto-capable MiniOS initrd.  The configurator
# only observes it; initrd composition and LUKS lifecycle remain boot-time work.
INITRD_CRYPTO_MARKER = '/run/initramfs/etc/minios-initramfs-crypt'
LUKS_LAYER_CAPABILITY = 'luks-layer-v1'
PERSISTENCE_MODES = frozenset(('native', 'dynfilefs', 'dynblk', 'vmdk', 'raw', 'squashfs'))

try:
    from zoneinfo import available_timezones
except ImportError:
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
    Read available services from systemd unit files and sysvinit scripts.
    """
    services = set()
    try:
        output = subprocess.check_output(
            ['systemctl', 'list-unit-files', '--type=service', '--no-legend', '--no-pager'],
            universal_newlines=True
        )
        for line in output.splitlines():
            unit = line.split()[0]
            services.add(unit)
            if unit.endswith('.service'):
                services.add(unit[:-8])
    except Exception:
        pass

    try:
        for name in os.listdir('/etc/init.d'):
            path = os.path.join('/etc/init.d', name)
            if os.path.isfile(path) and not name.startswith('.'):
                services.add(name)
    except Exception:
        pass

    return services


def is_xrdp_installed(root: str = '/') -> bool:
    """Return whether XRDP payload or service definitions exist."""
    paths = (
        'usr/sbin/xrdp',
        'usr/bin/xrdp',
        'usr/lib/systemd/system/xrdp.service',
        'lib/systemd/system/xrdp.service',
        'etc/init.d/xrdp',
    )
    return any(os.path.exists(os.path.join(root, path)) for path in paths)


def initrd_crypto_supported(root: str = '/', marker: str = INITRD_CRYPTO_MARKER) -> bool:
    """Return whether the running initrd explicitly advertises crypto support."""
    try:
        with open(os.path.join(root, marker.lstrip('/')), encoding='utf-8') as stream:
            return LUKS_LAYER_CAPABILITY in {
                line.strip() for line in stream if line.strip()}
    except OSError:
        return False


def parse_perchmode(cmdline: str) -> str:
    """Return the requested persistence mode from a kernel command line."""
    for parameter in cmdline.split():
        if parameter.startswith('perchmode='):
            return parameter.split('=', 1)[1].strip().lower()
    return ''


def read_perchmode() -> str:
    """Read the persistence mode requested for the current boot, if any."""
    try:
        with open('/proc/cmdline', encoding='utf-8') as stream:
            return parse_perchmode(stream.read())
    except OSError:
        return ''


def parse_perchencrypt(cmdline: str) -> str:
    """Return the requested persistence encryption from a kernel command line."""
    for parameter in cmdline.split():
        if parameter.startswith('perchencrypt='):
            return parameter.split('=', 1)[1].strip().lower()
    return ''


def read_perchencrypt() -> str:
    try:
        with open('/proc/cmdline', encoding='utf-8') as stream:
            return parse_perchencrypt(stream.read())
    except OSError:
        return ''

def get_available_timezones() -> Set[str]:
    """
    Get available timezones.
    """
    return available_timezones()


def _read_assignments(path: str) -> Dict[str, str]:
    values = {}
    try:
        with open(path, encoding='utf-8') as stream:
            for raw in stream:
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('"\'')
    except OSError:
        pass
    return values


def detect_current_settings() -> Dict[str, str]:
    """Best-effort settings detected from the current running session."""
    detected = {}
    try:
        hostname = socket.gethostname().strip()
        if hostname:
            detected['LIVE_HOSTNAME'] = hostname
    except Exception:
        pass

    current_locale = os.environ.get('LANG', '').strip()
    if not current_locale:
        try:
            current_locale = locale.setlocale(locale.LC_CTYPE) or ''
        except Exception:
            current_locale = ''
    if current_locale and current_locale not in ('C', 'C.UTF-8', 'POSIX'):
        detected['LIVE_LOCALES'] = current_locale

    timezone = ''
    try:
        with open('/etc/timezone', encoding='utf-8') as stream:
            timezone = stream.read().strip()
    except OSError:
        try:
            timezone = subprocess.check_output(
                ['timedatectl', 'show', '--property=Timezone', '--value'],
                universal_newlines=True,
                timeout=3,
            ).strip()
        except Exception:
            pass
    if timezone:
        detected['LIVE_TIMEZONE'] = timezone

    keyboard = _read_assignments('/etc/default/keyboard')
    key_map = {
        'XKBMODEL': 'LIVE_KEYBOARD_MODEL',
        'XKBLAYOUT': 'LIVE_KEYBOARD_LAYOUTS',
        'XKBOPTIONS': 'LIVE_KEYBOARD_OPTIONS',
        'XKBVARIANT': 'LIVE_KEYBOARD_VARIANTS',
    }
    for source, target in key_map.items():
        if keyboard.get(source):
            detected[target] = keyboard[source].replace(' ', '')

    try:
        target = subprocess.check_output(
            ['systemctl', 'get-default'], universal_newlines=True, timeout=3
        ).strip()
        if target:
            detected['DEFAULT_TARGET'] = target
    except Exception:
        pass
    return detected

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
    'live-config.sudo-mode': 'LIVE_SUDO_MODE',
    'sudo-mode': 'LIVE_SUDO_MODE',
    'live-config.polkit-mode': 'LIVE_POLKIT_MODE',
    'polkit-mode': 'LIVE_POLKIT_MODE',
    'live-config.ssh-permit-root-login': 'LIVE_SSH_PERMIT_ROOT_LOGIN',
    'ssh-permit-root-login': 'LIVE_SSH_PERMIT_ROOT_LOGIN',
    'live-config.ssh-password-authentication': 'LIVE_SSH_PASSWORD_AUTHENTICATION',
    'ssh-password-authentication': 'LIVE_SSH_PASSWORD_AUTHENTICATION',
    'live-config.xrdp-mode': 'LIVE_XRDP_MODE',
    'xrdp-mode': 'LIVE_XRDP_MODE',
    'live-config.x11-mode': 'LIVE_X11_MODE',
    'x11-mode': 'LIVE_X11_MODE',
    'live-config.issue-password-hints': 'LIVE_ISSUE_PASSWORD_HINTS',
    'issue-password-hints': 'LIVE_ISSUE_PASSWORD_HINTS',
    'live-config.lockscreen-mode': 'LIVE_LOCKSCREEN_MODE',
    'lockscreen-mode': 'LIVE_LOCKSCREEN_MODE',
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
