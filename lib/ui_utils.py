#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI utilities for MiniOS Configurator
Handles UI helper functions and widgets.

Copyright (C) 2025 MiniOS Linux
Author: crims0n <crims0n@minios.dev>
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

# Icon names
ICON_WINDOW             = 'preferences-system'
ICON_WARNING            = 'dialog-warning'
ICON_EYE_OPEN           = 'eye-open-negative-filled-symbolic'
ICON_EYE_CLOSED         = 'eye-not-looking-symbolic'

def match_completion_by_token(completion: Gtk.EntryCompletion, key: str, 
                             tree_iter: Gtk.TreeIter, entry: Gtk.Entry) -> bool:
    """
    Custom match for inline completion: matches only the current comma-separated segment.
    """
    text = entry.get_text()
    cursor_pos = entry.get_position()
    segment = text[:cursor_pos].rpartition(',')[2].lstrip()

    # pull the ListStore out of the completion
    store = completion.get_model()
    candidate = store[tree_iter][0]
    base = candidate[:-8] if candidate.endswith('.service') else candidate
    return candidate.startswith(segment) or base.startswith(segment)

def on_completion_selected(completion: Gtk.EntryCompletion, model: Gtk.TreeModel,
                          tree_iter: Gtk.TreeIter, entry: Gtk.Entry) -> bool:
    """
    Handler when a completion is selected: replace only the current segment.
    """
    full_text = entry.get_text()
    cursor_pos = entry.get_position()
    comma_index = full_text[:cursor_pos].rfind(',') + 1
    prefix = full_text[:comma_index]
    suffix = full_text[cursor_pos:]
    candidate = model[tree_iter][0]
    new_text = prefix + candidate + suffix
    entry.set_text(new_text)
    entry.set_position(len(prefix) + len(candidate))
    return True

def create_completion(items: set, entry: Gtk.Entry) -> Gtk.EntryCompletion:
    """
    Create and configure entry completion.
    """
    completion = Gtk.EntryCompletion()
    store = Gtk.ListStore(str)
    
    for item in sorted(items):
        store.append([item])
    
    completion.set_model(store)
    completion.set_text_column(0)
    completion.set_inline_completion(True)
    completion.set_match_func(match_completion_by_token, entry)
    completion.connect('match-selected', on_completion_selected, entry)
    
    return completion
