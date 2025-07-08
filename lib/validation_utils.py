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
from typing import Set, Dict

# Add lib directory to Python path
sys.path.insert(0, '/usr/lib/minios-configurator')

from password_utils import PASSWORD_FIELD_MAP

def validate_hostname(value: str) -> bool:
    """
    Validate hostname format.
    """
    if not value.strip():
        return True  # Empty is valid
    return bool(re.match(r'^[a-zA-Z0-9-]+$', value))

def validate_username(value: str) -> bool:
    """
    Validate username is not empty.
    """
    return bool(value.strip())

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

def validate_locales(value: str, available_locales: Set[str]) -> bool:
    """
    Validate locales field.
    """
    if not value.strip():
        return True  # Empty is valid
    locales = [s.strip() for s in value.split(',') if s.strip()]
    return bool(locales) and all(loc in available_locales for loc in locales)

def validate_timezone(value: str, available_timezones: Set[str]) -> bool:
    """
    Validate timezone.
    """
    if not value.strip():
        return True  # Empty is valid
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
        if full not in available_services:
            return False
    return True

def validate_field(key: str, value: str, available_locales: Set[str], 
                  available_timezones: Set[str], available_services: Set[str],
                  required_passwords: Dict[str, bool]) -> bool:
    """
    Validate a field based on its key and value.
    """
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
    else:
        return True
