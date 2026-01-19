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
    
    Security note: Passwords are passed via stdin to avoid exposure in process list.
    """
    if not plain_password:
        return ''
    
    # Try mkpasswd first (uses stdin to avoid password in process list)
    try:
        result = subprocess.run(
            ['mkpasswd', '--stdin'],
            input=plain_password,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            check=True,
            timeout=30
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    
    # Try mkpasswd without --stdin (some versions don't support it)
    # In this case, we use the method= argument to specify algorithm
    try:
        result = subprocess.run(
            ['mkpasswd', '-m', 'sha-512', '--stdin'],
            input=plain_password,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            check=True,
            timeout=30
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    
    # Fallback to openssl (uses stdin for password via -stdin flag)
    try:
        # Generate salt
        salt_result = subprocess.run(
            ['openssl', 'rand', '-base64', '12'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=True,
            timeout=10
        )
        salt = salt_result.stdout.strip()
        
        # Hash password using stdin (-stdin flag reads password from stdin)
        hash_result = subprocess.run(
            ['openssl', 'passwd', '-6', '-salt', salt, '-stdin'],
            input=plain_password,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=True,
            timeout=30
        )
        return hash_result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(
            f"Cannot hash password: neither mkpasswd nor openssl available or working. Error: {e}"
        )

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
