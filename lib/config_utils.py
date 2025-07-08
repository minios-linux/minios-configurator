#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration utilities for MiniOS Configurator
Handles config file reading and writing.

Copyright (C) 2025 MiniOS Linux
Author: crims0n <crims0n@minios.dev>
"""

import re
import sys
import gettext
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
        with open(config_file_path, encoding='utf-8') as f:
            for line in f:
                match = re.match(r"^([A-Z0-9_]+)=(?:'(.*)'|\"(.*)\"|(.*))", line)
                if match:
                    key = match.group(1)
                    val = match.group(2) or match.group(3) or match.group(4) or ''
                    config_values[key] = val
    except Exception as e:
        raise Exception(_('Failed to load config: {}').format(e))
    return config_values

def save_config(config_file_path: str, config_values: Dict[str, str], updated: Dict[str, str]) -> None:
    """
    Save configuration to file.
    """
    try:
        with open(config_file_path, encoding='utf-8') as f:
            orig = f.read().splitlines()
        
        out = []
        seen = set()

        for line in orig:
            match = re.match(r"^([A-Z0-9_]+)=", line)
            if not match:
                out.append(line)
                continue
            
            k = match.group(1)
            seen.add(k)

            if k in PASSWORD_FIELD_MAP.values():
                # Handle password fields
                fld = next(f for f, e in PASSWORD_FIELD_MAP.items() if e == k)
                pwd = updated.get(fld, '')
                if pwd:
                    h = hash_system_password(pwd)
                    out.append(f"{k}='{h}'")
                else:
                    out.append(f"{k}='{config_values.get(k, '')}'")
            elif k in updated:
                out.append(f"{k}='{updated[k]}'")
            else:
                out.append(line)

        # Add any missing password fields
        for fld, enc in PASSWORD_FIELD_MAP.items():
            if enc not in seen:
                pwd = updated.get(fld, '')
                h = hash_system_password(pwd) if pwd else config_values.get(enc, '')
                out.append(f"{enc}='{h}'")

        # Add any other new fields
        for k, v in updated.items():
            if k not in seen and k not in PASSWORD_FIELD_MAP:
                out.append(f"{k}='{v}'")

        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(out) + "\n")

    except Exception as e:
        raise Exception(_('Failed to update config: {}').format(e))

def process_services_field(text: str) -> str:
    """
    Process services field to ensure proper .service suffix.
    """
    parts = [s.strip() for s in text.split(',') if s.strip()]
    parts = [p if p.endswith('.service') else p + '.service' for p in parts]
    return ','.join(parts)
