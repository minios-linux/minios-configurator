#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Password utilities for MiniOS Configurator
Handles password hashing and validation.

Copyright (C) 2025 MiniOS Linux
Author: crims0n <crims0n@minios.dev>
"""

import subprocess
import re
from typing import Dict

# Password field mapping
PASSWORD_FIELD_MAP = {
    'USER_PASSWORD': 'LIVE_USER_PASSWORD_CRYPTED',
    'ROOT_PASSWORD': 'LIVE_ROOT_PASSWORD_CRYPTED',
}

def hash_system_password(plain_password: str) -> str:
    """
    Hash a password using mkpasswd if available, otherwise openssl SHA-512.
    """
    try:
        output = subprocess.check_output(
            ['mkpasswd', plain_password],
            text=True,
            stderr=subprocess.DEVNULL
        )
        return output.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        salt = subprocess.check_output(
            ['openssl', 'rand', '-base64', '12'],
            text=True
        ).strip()
        hashed = subprocess.check_output(
            ['openssl', 'passwd', '-6', '-salt', salt, plain_password],
            text=True
        )
        return hashed.strip()

def validate_password(password: str) -> bool:
    """
    Validate password - check that it doesn't contain spaces.
    """
    return not bool(re.search(r'\s', password))

def get_required_passwords(config_values: Dict[str, str]) -> Dict[str, bool]:
    """
    Determine which password fields are required (empty in config).
    """
    return {
        field: (config_values.get(encrypted_key, '') == '')
        for field, encrypted_key in PASSWORD_FIELD_MAP.items()
    }

def get_previous_password_hashes(config_values: Dict[str, str]) -> Dict[str, str]:
    """
    Get previous password hashes from config.
    """
    return {
        field: config_values.get(encrypted_key, '')
        for field, encrypted_key in PASSWORD_FIELD_MAP.items()
    }
