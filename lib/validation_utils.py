#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation utilities for MiniOS Configurator
Handles field validation logic.

Copyright (C) 2025 MiniOS Linux
Author: crims0n <crims0n@minios.dev>
"""

import re
import sys
import gettext
from typing import Set, Dict

# Add lib directory to Python path
sys.path.insert(0, '/usr/lib/minios-configurator')

from password_utils import PASSWORD_FIELD_MAP
from system_utils import PERSISTENCE_MODES, get_available_timezones, read_available_locales

_ = gettext.gettext

ENUM_VALUES = {
    'LIVE_SUDO_MODE': {'passwordless', 'password', 'disabled'},
    'LIVE_POLKIT_MODE': {'passwordless', 'password', 'disabled'},
    'LIVE_XRDP_MODE': {'relaxed', 'hardened', 'disabled'},
    'LIVE_X11_MODE': {'relaxed', 'hardened'},
    'LIVE_LOCKSCREEN_MODE': {'relaxed', 'hardened'},
}

BOOLEAN_VALUES = {'LIVE_SSH_PERMIT_ROOT_LOGIN', 'LIVE_SSH_PASSWORD_AUTHENTICATION', 'LIVE_ISSUE_PASSWORD_HINTS'}


def validate_perchmode(value: str, initrd_crypto_available: bool = False) -> bool:
    """Validate a boot-time persistence mode without creating persistence."""
    value = (value or '').strip().lower()
    return value in PERSISTENCE_MODES and (value != 'luks' or initrd_crypto_available)


def validate_user_dirs_path(value: str) -> bool:
    """Validate a path interpreted relative to the MiniOS drive root."""
    value = (value or '').strip()
    if not value:
        return False
    relative = value.lstrip('/')
    if (
        not relative
        or len(relative) > 240
        or re.search(r'[\x00-\x1f\x7f]', relative)
        or not re.match(r'^[A-Za-z0-9._ /-]+$', relative)
    ):
        return False
    parts = relative.split('/')
    return all(part not in ('', '.', '..') for part in parts)


def validate_config(values: Dict[str, str]) -> Dict[str, str]:
    """Return cross-field errors keyed by the fields that need attention."""
    errors = {}
    enabled = {item.strip() for item in values.get('ENABLE_SERVICES', '').split(',') if item.strip()}
    disabled = {item.strip() for item in values.get('DISABLE_SERVICES', '').split(',') if item.strip()}
    overlap = enabled & disabled
    if overlap:
        message = _('A service cannot be both enabled and disabled: {}').format(', '.join(sorted(overlap)))
        errors['ENABLE_SERVICES'] = message
        errors['DISABLE_SERVICES'] = message
    if values.get('LIVE_LINK_USER_DIRS') == 'true' and values.get('LIVE_BIND_USER_DIRS') == 'true':
        message = _('Choose either linked or bind-mounted user directories, not both.')
        errors['LIVE_LINK_USER_DIRS'] = message
        errors['LIVE_BIND_USER_DIRS'] = message
    user_dirs_enabled = values.get('LIVE_LINK_USER_DIRS') == 'true' or values.get('LIVE_BIND_USER_DIRS') == 'true'
    if user_dirs_enabled and not validate_user_dirs_path(values.get('LIVE_USER_DIRS_PATH', '')):
        errors['LIVE_USER_DIRS_PATH'] = _('Enter a safe path inside the MiniOS drive, for example /minios/userdata.')
    if values.get('LIVE_CONFIG_NOROOT') == 'true' and values.get('LIVE_SSH_PERMIT_ROOT_LOGIN') == 'true':
        errors['LIVE_SSH_PERMIT_ROOT_LOGIN'] = _('SSH root login cannot be enabled while no-root mode is enabled.')
    return errors

def validate_hostname(value: str) -> bool:
    """
    Validate hostname format.
    """
    if not value.strip():
        return True  # Empty is valid
    return bool(re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', value))

def validate_username(value: str) -> bool:
    """
    Validate username is not empty.
    """
    if not value.strip():
        return True
    return bool(re.match(r'^[a-z_][a-z0-9_-]{0,31}$', value))


def read_available_timezones():
    return get_available_timezones()

def validate_password(value: str, is_required: bool = False) -> bool:
    """
    Validate password doesn't contain spaces and is not empty if required.
    """
    # First check for spaces
    if re.search(r'\s', value):
        return False
    # Then check if required but empty
    if is_required and not value:
        return False
    return True

def validate_locales(value: str, available_locales: Set[str] = None) -> bool:
    """
    Validate locales field.
    """
    if not value.strip():
        return True  # Empty is valid
    if available_locales is None:
        available_locales = read_available_locales()
    locales = [s.strip() for s in value.split(',') if s.strip()]
    return bool(locales) and all(loc in available_locales for loc in locales)

def validate_timezone(value: str, available_timezones: Set[str] = None) -> bool:
    """
    Validate timezone.
    """
    if not value.strip():
        return True  # Empty is valid
    if available_timezones is None:
        available_timezones = read_available_timezones()
    return value in available_timezones

def validate_services(value: str, available_services: Set[str]) -> bool:
    """
    Validate services field.
    """
    if not value.strip():
        return True  # Empty is valid
    svcs = [s.strip() for s in value.split(',') if s.strip()]
    for svc in svcs:
        full = svc if svc.endswith('.service') else svc + '.service'
        base = svc[:-8] if svc.endswith('.service') else svc
        if svc not in available_services and full not in available_services and base not in available_services:
            return False
    return True

def validate_field(key: str, value: str, available_locales: Set[str], 
                  available_timezones: Set[str], available_services: Set[str],
                  required_passwords: Dict[str, bool]) -> bool:
    """
    Validate a field based on its key and value.
    """
    value = value or ''
    if key == 'LIVE_HOSTNAME':
        return validate_hostname(value)
    elif key == 'LIVE_USERNAME':
        return validate_username(value)
    elif key in PASSWORD_FIELD_MAP:
        is_required = required_passwords.get(key, False)
        if is_required and not value:
            return False
        return validate_password(value, is_required)
    elif key == 'LIVE_LOCALES':
        return validate_locales(value, available_locales)
    elif key == 'LIVE_TIMEZONE':
        return validate_timezone(value, available_timezones)
    elif key in ('ENABLE_SERVICES', 'DISABLE_SERVICES'):
        return validate_services(value, available_services)
    elif key == 'LIVE_USER_DIRS_PATH':
        return not value or validate_user_dirs_path(value)
    elif key in ENUM_VALUES:
        return (not value.strip()) or value in ENUM_VALUES[key]
    elif key in BOOLEAN_VALUES:
        return value in ('', 'true', 'false')
    else:
        return True
