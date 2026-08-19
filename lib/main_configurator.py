#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniOS Configurator
A graphical tool for configuring MiniOS settings via GTK.
Allows modifying parameters in /etc/live/config.conf.

Usage:
    main_configurator.py [/path/to/config/file]

If no config file path is provided, it defaults to /etc/live/config.conf.

Copyright (C) 2025 MiniOS Linux
Author: crims0n <crims0n@minios.dev>
"""

import os
import sys
import gi
import gettext
import argparse
import threading

# Add lib directory to Python path
sys.path.insert(0, '/usr/lib/minios-configurator')

# Import our library modules
from config_utils import load_config, save_config, process_services_field, normalize_default_target
from config_state import ConfigState
from system_utils import (read_available_locales, read_available_services,
                           detect_current_settings, get_available_timezones,
                           is_xrdp_installed,
                           initrd_crypto_supported, parse_cmdline_params,
                           read_perchmode)
from validation_utils import validate_config, validate_field
from ui_utils import (ICON_WINDOW, ICON_WARNING, ICON_EYE_OPEN, ICON_EYE_CLOSED)
from minios_gui import (StatusBanner, TokenCompletionPopover, apply_minios_css, ask_confirmation, new_header_bar,
                         new_icon, resolve_icon, show_error_dialog, show_info_dialog)
from password_utils import PASSWORD_FIELD_MAP, get_required_passwords, get_previous_password_hashes
from minios_security.security_profiles import (
    SECURITY_PROFILE_IDS,
    live_config_for_profile,
    validate_security_profile,
)

gi.require_version('Gtk', '3.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Gdk, Gio, GLib

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
APPLICATION_ID          = 'org.minios.configurator'
APP_NAME                = 'minios-configurator'
APP_TITLE               = 'MiniOS Configurator'
LOCALE_DIRECTORY        = '/usr/share/locale'
DEFAULT_CONFIG_FILE     = '/etc/live/config.conf'
CSS_FILE_PATH           = '/usr/share/minios-configurator/style.css'

# ──────────────────────────────────────────────────────────────────────────────
# Internationalization
# ──────────────────────────────────────────────────────────────────────────────
gettext.bindtextdomain(APP_NAME, LOCALE_DIRECTORY)
gettext.textdomain(APP_NAME)
_ = gettext.gettext

# ──────────────────────────────────────────────────────────────────────────────
# Tab and field definitions
# ──────────────────────────────────────────────────────────────────────────────
TAB_DEFINITIONS = {
    _('User'): [
        (_("Username"), 'LIVE_USERNAME', Gtk.Entry,
         _("Set the default username for the live session.\n\n"
           "• This user is created automatically at boot.\n\n"
           "See: man 7 live-config (search 'username')")),
        (_("Full name"), 'LIVE_USER_FULLNAME', Gtk.Entry,
         _("Enter the full name for the default user.\n\n"
           "• Used for display purposes (e.g., on login screens).\n\n"
           "See: man 7 live-config (search 'user-fullname')")),
        (_("User groups"), 'LIVE_USER_DEFAULT_GROUPS', Gtk.Entry,
         _("Specify additional groups for the user, separated by commas or spaces.\n\n"
           "• Grants access to devices and features (e.g., 'audio, video, plugdev').\n\n"
           "See: man 7 live-config (search 'user-default-groups')")),
        (_("User password"), 'USER_PASSWORD', Gtk.Entry,
         _("Set the initial password for the default user.\n\n"
           "• Leave blank to keep the existing password.\n"
           "• Spaces are not allowed.\n\n"
           "See: man 7 live-config (search 'user-password')")),
        (_("Root password"), 'ROOT_PASSWORD', Gtk.Entry,
         _("Set the initial password for the root (administrator) account.\n\n"
           "• Leave blank to keep the existing password.\n"
           "• Spaces are not allowed; ignored if 'No-root mode' is enabled.\n\n"
           "See: man 7 live-config (search 'root-password')")),
        (_("Link user directories to storage"), 'LIVE_LINK_USER_DIRS', Gtk.CheckButton,
         _("If enabled, user home directories will be symlinked to persistent storage.\n\n"
            "• Uses the FAT32, exFAT, or NTFS MiniOS drive.\n"
            "• Unavailable with toram, toram=full, and toram=trim.\n"
            "• Conflicting non-empty folders are never merged automatically.\n\n"
           "See: man 7 live-config (search 'link-user-dirs')")),
        (_("Bind user directories to storage"), 'LIVE_BIND_USER_DIRS', Gtk.CheckButton,
         _("If enabled, user home directories will be bind-mounted to persistent storage.\n\n"
            "• Uses the FAT32, exFAT, or NTFS MiniOS drive.\n"
            "• Unavailable with toram, toram=full, and toram=trim.\n"
            "• Conflicting non-empty folders are never merged automatically.\n\n"
           "See: man 7 live-config (search 'bind-user-dirs')")),
        (_("User directories path on storage"), 'LIVE_USER_DIRS_PATH', Gtk.Entry,
         _("Set the base path on persistent storage for user directories.\n\n"
            "• Example: '/minios/userdirs'.\n\n"
            "• The path must stay inside the MiniOS drive; '.', '..', and empty segments are not allowed.\n\n"
           "See: man 7 live-config (search 'user-dirs-path')")),
    ],
    _('System'): [
        (_("No-root mode"), 'LIVE_CONFIG_NOROOT', Gtk.CheckButton,
         _("If enabled, disables the root account, enhancing security.\n\n"
           "• Prevents root login and administrator access.\n"
           "• Ideal for live sessions.\n\n"
           "See: man 7 live-config (search 'noroot')")),
        (_("Hostname"), 'LIVE_HOSTNAME', Gtk.Entry,
         _("Set the computer's network name (hostname).\n\n"
           "• Allowed characters: letters, numbers, hyphens.\n"
           "• Example: 'minios-pc'.\n\n"
           "See: man 7 live-config (search 'hostname')")),
        (_("Locales"), 'LIVE_LOCALES', Gtk.Entry,
         _("Set system language(s) and regional settings.\n\n"
           "• Enter locale codes separated by commas (e.g. 'de_DE.UTF-8, en_US.UTF-8').\n"
           "• The first locale is treated as default.\n\n"
           "See: man 7 live-config (search 'locales')")),
        (_("Timezone"), 'LIVE_TIMEZONE', Gtk.Entry,
         _("Set the system timezone (e.g., 'Europe/Berlin', 'America/New_York').\n\n"
           "• Affects system clock and displayed times.\n\n"
           "See: man 7 live-config (search 'timezone')")),
        (_("Default boot target"), 'DEFAULT_TARGET', Gtk.ComboBoxText,
         _("Set the default boot target:\n"
           "• 'graphical.target' – start with a desktop.\n"
           "• 'multi-user.target' – console mode.\n"
           "• 'rescue.target' – minimal rescue mode.\n\n"
           "Short aliases like 'graphical' and 'multi-user' are accepted.")),
        (_("Enable services"), 'ENABLE_SERVICES', Gtk.Entry,
         _("List services to enable at boot, separated by commas.\n\n"
           "• Example: 'ssh, NetworkManager'.\n"
           "• systemd units and sysvinit script names are supported.")),
        (_("Disable services"), 'DISABLE_SERVICES', Gtk.Entry,
         _("List services to disable at boot, separated by commas.\n\n"
           "• Example: 'bluetooth, ModemManager'.\n"
            "• systemd units and sysvinit script names are supported.")),
    ],
    _('Security'): [
        (_("Security preset"), '_SECURITY_PRESET', Gtk.ComboBoxText,
          _("Choose a preset to fill the settings below. You can customize any setting afterward. Only the individual settings are saved.")),
        (_("Sudo mode"), 'LIVE_SUDO_MODE', Gtk.ComboBoxText,
         _("passwordless keeps historical MiniOS behavior; password requires the user password; disabled removes the MiniOS sudo grant.")),
        (_("PolicyKit mode"), 'LIVE_POLKIT_MODE', Gtk.ComboBoxText,
         _("passwordless keeps historical MiniOS GUI admin convenience; password/disabled remove that rule and use normal PolicyKit authentication.")),
        (_("SSH root login"), 'LIVE_SSH_PERMIT_ROOT_LOGIN', Gtk.CheckButton,
         _("Allow or deny root login through OpenSSH.")),
        (_("SSH password authentication"), 'LIVE_SSH_PASSWORD_AUTHENTICATION', Gtk.CheckButton,
         _("Allow or deny password authentication through OpenSSH.")),
        (_("XRDP mode"), 'LIVE_XRDP_MODE', Gtk.ComboBoxText,
         _("relaxed keeps MiniOS defaults; hardened binds to localhost and disables root login; disabled disables common XRDP service links.")),
        (_("X11 mode"), 'LIVE_X11_MODE', Gtk.ComboBoxText,
         _("relaxed keeps compatibility; hardened removes the permissive -ac launch option and tightens Xwrapper where present.")),
        (_("Show password hints"), 'LIVE_ISSUE_PASSWORD_HINTS', Gtk.CheckButton,
         _("Show default root/live password hints in /etc/issue.")),
        (_("Lockscreen mode"), 'LIVE_LOCKSCREEN_MODE', Gtk.ComboBoxText,
         _("relaxed keeps live-session convenience; hardened preserves/enables screen locking where supported.")),
    ],
    _('Keyboard'): [
        (_("Keyboard model"), 'LIVE_KEYBOARD_MODEL', Gtk.Entry,
         _("Specify the keyboard hardware model (e.g., 'pc105').\n\n"
           "• Leave blank for automatic detection.\n\n"
           "See: man 7 live-config (search 'keyboard-model')")),
        (_("Keyboard layouts"), 'LIVE_KEYBOARD_LAYOUTS', Gtk.Entry,
         _("List one or more keyboard layouts, separated by commas (e.g., 'us, ru').\n\n"
           "• Controls which layouts are available in the session.\n\n"
           "See: man 7 live-config (search 'keyboard-layouts')")),
        (_("Keyboard options"), 'LIVE_KEYBOARD_OPTIONS', Gtk.Entry,
         _("Set additional keyboard options (XKB).\n\n"
           "• Example: 'grp:alt_shift_toggle' to switch layouts with Alt+Shift.\n\n"
           "See: man 7 live-config (search 'keyboard-options')")),
        (_("Keyboard variants"), 'LIVE_KEYBOARD_VARIANTS', Gtk.Entry,
         _("Specify keyboard variants for chosen layouts, separated by commas.\n\n"
           "• Customize layout (e.g., 'dvorak' for US).\n"
           "• Leave blank if not needed.\n\n"
           "See: man 7 live-config (search 'keyboard-variants')")),
    ],
    _('Advanced'): [
        (_("Module mode"), 'LIVE_MODULE_MODE', Gtk.ComboBoxText,
         _("Choose how system modules are loaded:\n"
           "• 'simple' – load modules as-is.\n"
           "• 'merged' – consolidates dpkg databases, passwd, shadow, and groups; updates caches.\n\n"
           "Usually not required unless modules are built independently.\n"
           "See: man 7 live-config (search 'module-mode')")),
        (_("live-config command line"), 'LIVE_CONFIG_CMDLINE', Gtk.Entry,
         _("Additional boot parameters for live-config (separated by spaces).\n\n"
           "• Passed at startup to control various session aspects.\n"
           "• Example: 'boot=live live-config.debug'\n\n"
           "See: man 7 live-config (search 'cmdline')")),
        (_("Debug mode"), 'LIVE_CONFIG_DEBUG', Gtk.CheckButton,
         _("Activate to enable detailed debug output during boot.\n\n"
           "• Useful for troubleshooting configuration issues.\n\n"
           "See: man 7 live-config (search 'debug')")),
        (_("Export logs to flash drive"), 'EXPORT_LOGS', Gtk.CheckButton,
          _("If enabled, MiniOS and live-config logs are copied to the writable MiniOS drive during every boot.\n\n"
            "• Each boot creates a timestamped directory under /minios/log.\n"
            "• Useful for diagnostics and troubleshooting.\n\n"
           "See: https://github.com/minios-linux/minios-live/wiki")),
    ],
}

NEXT_BOOT_KEYS = {
    'LIVE_LINK_USER_DIRS', 'LIVE_BIND_USER_DIRS', 'LIVE_USER_DIRS_PATH',
    'LIVE_HOSTNAME', 'LIVE_LOCALES', 'LIVE_TIMEZONE', 'DEFAULT_TARGET',
    'ENABLE_SERVICES', 'DISABLE_SERVICES', 'LIVE_KEYBOARD_MODEL',
    'LIVE_KEYBOARD_LAYOUTS', 'LIVE_KEYBOARD_OPTIONS', 'LIVE_KEYBOARD_VARIANTS',
    'LIVE_MODULE_MODE', 'LIVE_CONFIG_CMDLINE', 'LIVE_CONFIG_DEBUG', 'EXPORT_LOGS',
}
NEW_SESSION_KEYS = {
    'LIVE_USERNAME', 'LIVE_USER_FULLNAME', 'LIVE_USER_DEFAULT_GROUPS',
    'USER_PASSWORD', 'ROOT_PASSWORD', 'LIVE_CONFIG_NOROOT',
    'LIVE_SUDO_MODE', 'LIVE_POLKIT_MODE',
    'LIVE_SSH_PERMIT_ROOT_LOGIN', 'LIVE_SSH_PASSWORD_AUTHENTICATION',
    'LIVE_XRDP_MODE', 'LIVE_X11_MODE', 'LIVE_ISSUE_PASSWORD_HINTS',
    'LIVE_LOCKSCREEN_MODE',
}


def applicability_for_key(key):
    if key in NEXT_BOOT_KEYS:
        return 'next-boot'
    return 'new-session'

# ──────────────────────────────────────────────────────────────────────────────
# Main Configurator Window
# ──────────────────────────────────────────────────────────────────────────────
class ConfiguratorWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application, config_path: str, inherit_cmdline: bool = False):
        super().__init__(application=application, title=_(APP_TITLE))
        self._destroyed = False
        self.connect('destroy', self._on_destroy)
        screen = Gdk.Screen.get_default()
        monitor = screen.get_primary_monitor() if screen else 0
        workarea = screen.get_monitor_workarea(monitor) if screen else None
        width = min(900, max(700, int(workarea.width * 0.76))) if workarea else 820
        height = min(600, max(480, int(workarea.height * 0.76))) if workarea else 580
        self.set_default_size(width, height)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_name(ICON_WINDOW)

        # Internal state
        self.config_file_path = config_path
        self.config_values = {}
        self.field_widgets = {}
        self.field_labels = {}
        self.field_validity = {}
        self.previous_password_hashes = {}
        self.field_tab_index = {}
        self._busy = False

        # Load config and track required password fields
        try:
            source_values = load_config(self.config_file_path)
        except Exception as e:
            show_error_dialog(self, str(e))
            return

        # If inherit_cmdline flag is set, merge cmdline parameters
        cmdline_params = parse_cmdline_params() if inherit_cmdline else {}
        self.state = ConfigState(source_values, cmdline_params, PASSWORD_FIELD_MAP.keys())
        self.config_values = dict(self.state.current)

        self.previous_password_hashes = get_previous_password_hashes(self.config_values)
        self.required_passwords = get_required_passwords(self.config_values)

        # Load system data
        self.available_locales = read_available_locales()
        self.available_timezones = get_available_timezones()
        self.available_services = read_available_services()
        self.xrdp_installed = is_xrdp_installed()
        self.current_perchmode = read_perchmode()
        self.initrd_crypto_available = initrd_crypto_supported()

        apply_minios_css(CSS_FILE_PATH)

        # Build the UI
        self._build_header_bar()
        self._build_main_layout()

        # Run initial validation
        self._validate_all_fields()

    # ──────────────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────────────
    def _build_header_bar(self):
        self.set_titlebar(new_header_bar(_(APP_TITLE)))

    def _build_main_layout(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(container)

        self._add_warning_label(container)
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        container.pack_start(body, True, True, 0)
        self.category_list = Gtk.ListBox()
        self.category_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.category_list.set_size_request(180, -1)
        self.category_list.get_style_context().add_class('minios-sidebar')
        self.category_list.connect('row-selected', self._on_category_selected)
        body.pack_start(self.category_list, False, False, 0)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        body.pack_start(self.stack, True, True, 0)
        self.detect_button_size_group = Gtk.SizeGroup(
            Gtk.SizeGroupMode.HORIZONTAL)
        self.detect_buttons = []
        self._populate_tabs()
        self._add_footer(container)

    def _add_warning_label(self, parent: Gtk.Box):
        text = _('If you are unsure about a field, do not change it. '
                 'Incorrect settings may prevent the system from booting.')
        if self.current_perchmode == 'luks':
            if self.initrd_crypto_available:
                text += '\n\n' + _(
                    'LUKS persistence was requested at boot. Crypto support is provided by the initrd; '
                    'this configurator does not open containers or request passwords.'
                )
            else:
                text += '\n\n' + _(
                    'LUKS persistence was requested at boot, but this initrd does not advertise crypto support. '
                    'It cannot be activated until a crypto-capable initrd provides '
                    '/run/initramfs/etc/minios-initramfs-crypt.'
                )
        banner = StatusBanner(text, intent='warning', icon=ICON_WARNING)
        banner.label.set_max_width_chars(80)
        for method in ('set_margin_top', 'set_margin_bottom', 'set_margin_start', 'set_margin_end'):
            getattr(banner, method)(6)
        parent.pack_start(banner, False, False, 0)

    def _populate_tabs(self):
        for tab_index, (tab_label, fields) in enumerate(TAB_DEFINITIONS.items()):
            grid = Gtk.Grid(column_spacing=8, row_spacing=8)
            grid.set_column_homogeneous(False)
            for m in ('set_margin_top', 'set_margin_bottom', 'set_margin_start', 'set_margin_end'):
                getattr(grid, m)(8)

            field_keys = {field[1] for field in fields}
            first_row = 0
            if 'LIVE_HOSTNAME' in field_keys:
                self._add_detect_section(grid, 0, 'system')
                first_row = 2
            elif 'LIVE_KEYBOARD_MODEL' in field_keys:
                self._add_detect_section(grid, 0, 'keyboard')
                first_row = 2

            for row_index, (label_text, key, widget_cls, tooltip) in enumerate(fields):
                self._add_field_row(grid, first_row + row_index * 2, tab_index, label_text, key, widget_cls, tooltip)

            scrolled = Gtk.ScrolledWindow()
            scrolled.set_hexpand(True)
            scrolled.set_vexpand(True)
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            card = Gtk.Frame()
            card.get_style_context().add_class('content-card')
            card.add(grid)
            scrolled.add(card)
            name = 'category-{}'.format(tab_index)
            self.stack.add_named(scrolled, name)
            row = Gtk.ListBoxRow()
            row.category_name = name
            label = Gtk.Label(label=tab_label, xalign=0)
            row.add(label)
            self.category_list.add(row)
        self.category_list.select_row(self.category_list.get_row_at_index(0))

    def _on_category_selected(self, _listbox, row):
        if row is not None:
            self.stack.set_visible_child_name(row.category_name)

    def _add_detect_section(self, grid, row, scope):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        if scope == 'system':
            text = _('Detect current hostname, locale, timezone, and boot target.')
            label = _('Detect current system settings')
        else:
            text = _('Detect the keyboard settings used by the current session.')
            label = _('Detect current keyboard')
        note = Gtk.Label(label=text, xalign=0)
        note.set_line_wrap(True)
        note.get_style_context().add_class('availability-note')
        box.pack_start(note, True, True, 0)
        button = Gtk.Button(label=label)
        button.set_valign(Gtk.Align.CENTER)
        self.detect_button_size_group.add_widget(button)
        self.detect_buttons.append(button)
        button.connect('clicked', self._on_detect_clicked, scope)
        box.pack_end(button, False, False, 0)
        grid.attach(box, 0, row, 2, 1)

    def _add_field_row(self, grid, row, tab_index, label_text, key, widget_cls, tooltip):
        label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        label_text_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=1)
        label = Gtk.Label(label=label_text, xalign=0)
        label.set_tooltip_text(tooltip)
        self.field_labels[key] = label_text
        if key in self.required_passwords and self.required_passwords[key]:
            label.set_text(label.get_text() + " *")
        label_text_box.pack_start(label, False, False, 0)
        help_icon = new_icon('dialog-information-symbolic', Gtk.IconSize.MENU)
        help_icon.get_style_context().add_class('field-help-icon')
        help_hover = Gtk.EventBox()
        help_hover.set_visible_window(False)
        help_hover.set_valign(Gtk.Align.CENTER)
        help_hover.set_tooltip_text(tooltip)
        help_hover.add(help_icon)
        applicability = applicability_for_key(key)
        if key == '_SECURITY_PRESET':
            applicability_text = _('Preset only; individual settings are saved')
        else:
            applicability_text = {
                'next-boot': _('Applies after reboot'),
                'new-session': _('Only when creating a new session'),
            }[applicability]
        badge = Gtk.Label(label=applicability_text, xalign=0)
        badge.set_halign(Gtk.Align.START)
        badge.get_style_context().add_class('applicability-note')
        badge.get_style_context().add_class(
            'applicability-' + applicability)
        label_text_box.pack_start(badge, False, False, 0)
        label_box.pack_start(label_text_box, True, True, 0)
        label_box.pack_end(help_hover, False, False, 0)
        grid.attach(label_box, 0, row, 1, 1)
        error = Gtk.Label(xalign=0)
        error.get_style_context().add_class('inline-error')
        error.set_no_show_all(True)
        self.field_error_labels = getattr(self, 'field_error_labels', {})
        self.field_error_labels[key] = error
        grid.attach(error, 1, row + 1, 1, 1)
        self.field_tab_index[key] = tab_index

        if widget_cls is Gtk.Entry and key in PASSWORD_FIELD_MAP:
            self._add_password_entry(grid, row, key, tooltip)
        elif widget_cls is Gtk.Entry:
            self._add_text_entry(grid, row, key, tooltip)
        elif widget_cls is Gtk.CheckButton:
            self._add_check_button(grid, row, key, tooltip)
        else:
            self._add_combo_box(grid, row, key, tooltip)

    def _add_password_entry(self, grid, row, key, tooltip):
        entry = Gtk.Entry()
        entry.set_size_request(-1, -1)
        entry.get_style_context().add_class('setting-control')
        entry.set_visibility(False)
        entry.set_hexpand(True)
        entry.set_valign(Gtk.Align.CENTER)
        entry.set_tooltip_text(tooltip)
        # Classic pattern: the show/hide toggle is an icon INSIDE the entry, so
        # the row keeps the exact height of every other field.
        entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, resolve_icon(ICON_EYE_OPEN))
        entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        entry.set_icon_tooltip_text(
            Gtk.EntryIconPosition.SECONDARY, _('Show password'))
        entry.connect('icon-press', self._on_password_icon_press)
        self._register_widget(entry, key)
        self.field_widgets[key] = entry
        grid.attach(entry, 1, row, 1, 1)

    def _on_password_icon_press(self, entry, icon_pos, _event):
        if icon_pos != Gtk.EntryIconPosition.SECONDARY:
            return
        visible = not entry.get_visibility()
        entry.set_visibility(visible)
        entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY,
            resolve_icon(ICON_EYE_CLOSED if visible else ICON_EYE_OPEN))
        entry.set_icon_tooltip_text(
            Gtk.EntryIconPosition.SECONDARY,
            _('Hide password') if visible else _('Show password'))

    def _add_text_entry(self, grid, row, key, tooltip):
        entry = Gtk.Entry()
        entry.set_size_request(-1, -1)
        entry.get_style_context().add_class('setting-control')
        entry.set_hexpand(True)
        entry.set_valign(Gtk.Align.CENTER)
        entry.set_text(self.config_values.get(key, ''))
        placeholders = {
            'LIVE_HOSTNAME': _('Automatic'),
            'LIVE_LOCALES': _('Use system default'),
            'LIVE_TIMEZONE': _('Use system default'),
            'LIVE_KEYBOARD_MODEL': _('Automatic'),
            'LIVE_KEYBOARD_LAYOUTS': _('Automatic'),
            'LIVE_KEYBOARD_OPTIONS': _('None'),
            'LIVE_KEYBOARD_VARIANTS': _('None'),
            'ENABLE_SERVICES': _('None'),
            'DISABLE_SERVICES': _('None'),
            'LIVE_CONFIG_CMDLINE': _('None'),
        }
        if key in placeholders:
            entry.set_placeholder_text(placeholders[key])
        entry.set_tooltip_text(tooltip)
        if key in ('LIVE_LOCALES', 'LIVE_TIMEZONE', 'ENABLE_SERVICES', 'DISABLE_SERVICES'):
            self._attach_inline_completion(entry, key)
        self._register_widget(entry, key)
        self.field_widgets[key] = entry
        grid.attach(entry, 1, row, 1, 1)

    def _add_check_button(self, grid, row, key, tooltip):
        check = Gtk.ComboBoxText()
        check.set_size_request(-1, -1)
        check.set_hexpand(True)
        check.set_valign(Gtk.Align.CENTER)
        check.get_style_context().add_class('setting-control')
        default_enabled = key in (
            'LIVE_SSH_PERMIT_ROOT_LOGIN',
            'LIVE_SSH_PASSWORD_AUTHENTICATION',
            'LIVE_ISSUE_PASSWORD_HINTS',
        )
        check.append('true', _('Enabled'))
        check.append('false', _('Disabled'))
        current = self.config_values.get(key, '').lower()
        effective = current if current in ('true', 'false') else ('true' if default_enabled else 'false')
        check.set_active_id(effective)
        check._default_setting_id = 'true' if default_enabled else 'false'
        check.set_tooltip_text(tooltip)
        check._boolean_setting = True
        self.field_validity[key] = True
        check.connect('changed', lambda w: self._on_check_changed(w, key))
        self.field_widgets[key] = check
        grid.attach(check, 1, row, 1, 1)

    def _add_combo_box(self, grid, row, key, tooltip):
        combo = Gtk.ComboBoxText()
        combo._setting_ids = True
        combo.set_size_request(-1, -1)
        combo.get_style_context().add_class('setting-control')
        combo.set_hexpand(True)
        combo.set_valign(Gtk.Align.CENTER)
        options_map = {
            'LIVE_MODULE_MODE': ['simple', 'merged'],
            'DEFAULT_TARGET': ['graphical.target', 'multi-user.target', 'rescue.target'],
            '_SECURITY_PRESET': list(SECURITY_PROFILE_IDS),
            'LIVE_SUDO_MODE': ['passwordless', 'password', 'disabled'],
            'LIVE_POLKIT_MODE': ['passwordless', 'password', 'disabled'],
            'LIVE_XRDP_MODE': ['relaxed', 'hardened', 'disabled'],
            'LIVE_X11_MODE': ['relaxed', 'hardened'],
            'LIVE_LOCKSCREEN_MODE': ['relaxed', 'hardened'],
        }
        options = options_map.get(key, ['graphical.target', 'multi-user.target', 'rescue.target'])
        defaults = {
            'DEFAULT_TARGET': 'graphical.target',
            'LIVE_MODULE_MODE': 'simple',
            'LIVE_SUDO_MODE': 'passwordless',
            'LIVE_POLKIT_MODE': 'passwordless',
            'LIVE_XRDP_MODE': 'relaxed',
            'LIVE_X11_MODE': 'relaxed',
            'LIVE_LOCKSCREEN_MODE': 'relaxed',
        }
        if key == '_SECURITY_PRESET':
            combo.append('', _('Custom'))
        for opt in options:
            combo.append(opt, opt)
        current = normalize_default_target(self.config_values.get(key, '')) if key == 'DEFAULT_TARGET' else self.config_values.get(key, '')
        if key == '_SECURITY_PRESET':
            current = self._matching_security_preset()
        if current in options:
            combo.set_active_id(current)
        elif key in defaults:
            combo.set_active_id(defaults[key])
            combo._default_setting_id = defaults[key]
        else:
            combo.set_active(-1)
        combo.set_tooltip_text(tooltip)
        if key == '_SECURITY_PRESET':
            combo.connect('changed', self._on_security_profile_changed)
            self.field_validity[key] = True
        else:
            self._register_widget(combo, key, is_combo=True)
        self.field_widgets[key] = combo
        if key == 'LIVE_XRDP_MODE' and not self.xrdp_installed:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.set_hexpand(True)
            box.pack_start(combo, False, False, 0)
            note = Gtk.Label(
                label=_('XRDP is not installed. This setting will be saved and used if XRDP is installed later.'),
                xalign=0,
            )
            note.set_line_wrap(True)
            note.get_style_context().add_class('availability-note')
            box.pack_start(note, False, False, 0)
            grid.attach(box, 1, row, 1, 1)
        else:
            grid.attach(combo, 1, row, 1, 1)

    def _attach_inline_completion(self, entry, key):
        items = {
            'LIVE_LOCALES': self.available_locales,
            'LIVE_TIMEZONE': self.available_timezones,
            'ENABLE_SERVICES': self.available_services,
            'DISABLE_SERVICES': self.available_services,
        }[key]
        aliases = None
        if key in ('ENABLE_SERVICES', 'DISABLE_SERVICES'):
            aliases = lambda value: (
                value, value[:-8] if value.endswith('.service') else value)
        TokenCompletionPopover(
            entry, items=items, delimiters=',', min_chars=1,
            max_results=12, aliases=aliases)

    def _add_footer(self, parent):
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.get_style_context().add_class('minios-footer')
        self.dirty_label = Gtk.Label(xalign=0)
        footer.pack_start(self.dirty_label, True, True, 0)
        self.reset_button = Gtk.Button(label=_('Discard changes…'))
        self.reset_button.connect('clicked', self._on_reset_clicked)
        footer.pack_start(self.reset_button, False, False, 0)
        self.review_button = Gtk.Button(label=_('Review changes'))
        self.review_button.connect('clicked', self._on_review_clicked)
        footer.pack_start(self.review_button, False, False, 0)
        self.save_button = Gtk.Button(label=_('Save changes'))
        self.save_button.get_style_context().add_class('suggested-action')
        self.save_button.connect('clicked', self._on_save_clicked)
        footer.pack_end(self.save_button, False, False, 0)
        parent.pack_end(footer, False, False, 0)
        self._update_actions()

    def _on_security_profile_changed(self, combo):
        if getattr(self, '_applying_security_preset', False):
            return
        profile = combo.get_active_id() or ''
        if not profile:
            return
        try:
            profile = validate_security_profile(profile)
        except ValueError:
            return
        cfg = live_config_for_profile(profile)
        self._applying_security_preset = True
        for key, value in cfg.items():
            if key == 'LIVE_CONFIG_CMDLINE':
                continue
            widget = self.field_widgets.get(key)
            if widget is None:
                continue
            self.state.set(key, value)
            if getattr(widget, '_boolean_setting', False):
                widget.set_active_id(value)
            elif isinstance(widget, Gtk.ComboBoxText):
                widget.set_active_id(value)
                if widget.get_active_text() != value:
                    # ComboBoxText without ids: select by visible text.
                    model = widget.get_model()
                    for idx, row in enumerate(model):
                        if row[0] == value:
                            widget.set_active(idx)
                            break
            elif isinstance(widget, Gtk.Entry):
                widget.set_text(value)
        cmdline = self.field_widgets.get('LIVE_CONFIG_CMDLINE')
        if cmdline is not None:
            tokens = [token for token in cmdline.get_text().split() if token != 'noautologin']
            if profile in ('balanced', 'strict'):
                tokens.append('noautologin')
            cmdline_value = ' '.join(tokens)
            self.state.set('LIVE_CONFIG_CMDLINE', cmdline_value)
            cmdline.set_text(cmdline_value)
        self._applying_security_preset = False
        self._validate_all_fields()

    def _matching_security_preset(self):
        """Return the preset matching concrete saved values, if any."""
        for profile in SECURITY_PROFILE_IDS:
            expected = live_config_for_profile(profile)
            concrete_match = all(
                self.state.get(key) == value
                for key, value in expected.items()
                if key not in ('LIVE_CONFIG_CMDLINE', 'LIVE_SECURITY_PROFILE')
            )
            has_noautologin = 'noautologin' in self.state.get('LIVE_CONFIG_CMDLINE').split()
            wants_noautologin = profile in ('balanced', 'strict')
            if concrete_match and has_noautologin == wants_noautologin:
                return profile
        return ''

    # ──────────────────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────────────────
    def _register_widget(self, widget, key, is_combo=False):
        widget.connect('changed', lambda w: self._on_field_changed(w, key, is_combo))
        self.field_validity[key] = False

    def _on_field_changed(self, widget, key, is_combo):
        if is_combo and getattr(widget, '_setting_ids', False):
            value = widget.get_active_id() or ''
        else:
            value = widget.get_active_text() if is_combo else widget.get_text()
        programmatic = getattr(self, '_applying_security_preset', False)
        validating = getattr(self, '_validating_only', False)
        if not programmatic and not validating:
            self.state.set(key, value or '')
        if key != '_SECURITY_PRESET' and not programmatic and not validating:
            preset = self.field_widgets.get('_SECURITY_PRESET')
            if preset is not None:
                preset.set_active_id(self._matching_security_preset())
        valid = validate_field(key, value, self.available_locales, 
                              self.available_timezones, self.available_services,
                              self.required_passwords)

        ctx = widget.get_style_context()
        if valid:
            ctx.remove_class('error')
        else:
            ctx.add_class('error')

        self.field_validity[key] = valid
        self._highlight_error_tab(self.field_tab_index[key])
        error = self.field_error_labels.get(key)
        if error:
            error.set_text(_('This value is not valid.'))
            error.set_visible(not valid)
        self._update_actions()

    def _on_check_changed(self, widget, key):
        if getattr(self, '_applying_security_preset', False):
            return
        self.state.set(key, widget.get_active_id() or '')
        self._validate_all_fields()

    def _update_actions(self):
        if not hasattr(self, 'dirty_label'):
            return
        busy = getattr(self, '_busy', False)
        count = self.state.dirty_count
        if count == 0:
            self.dirty_label.set_text(_('No unsaved changes'))
        elif count == 1:
            self.dirty_label.set_text(_('1 unsaved change'))
        else:
            self.dirty_label.set_text(_('{count} unsaved changes').format(count=count))
        valid = all(self.field_validity.values())
        dirty = set(self.state.dirty_keys)
        for key, widget in self.field_widgets.items():
            if key == '_SECURITY_PRESET':
                self.field_validity[key] = True
                continue
            ctx = widget.get_style_context()
            if key in dirty:
                ctx.add_class('changed')
            else:
                ctx.remove_class('changed')
        for button in (self.reset_button, self.review_button):
            button.set_sensitive(count > 0 and not busy)
        self.save_button.set_sensitive(count > 0 and valid and not busy)

    def _highlight_error_tab(self, tab_index):
        row = self.category_list.get_row_at_index(tab_index)
        keys = [k for k, idx in self.field_tab_index.items() if idx == tab_index]
        has_error = any(not self.field_validity.get(k, True) for k in keys)
        ctx = row.get_style_context()
        if has_error:
            ctx.add_class('error-tab')
        else:
            ctx.remove_class('error-tab')

    def _validate_all_fields(self):
        self._validating_only = True
        for key, widget in self.field_widgets.items():
            if key == '_SECURITY_PRESET':
                continue
            widget.get_style_context().remove_class('error')
            self.field_error_labels[key].set_visible(False)
            if getattr(widget, '_boolean_setting', False):
                self.field_validity[key] = True
            else:
                is_combo = isinstance(widget, Gtk.ComboBoxText)
                self._on_field_changed(widget, key, is_combo)
        cross_errors = validate_config(self._collect_updated_values())
        for key, message in cross_errors.items():
            self.field_validity[key] = False
            widget = self.field_widgets[key]
            widget.get_style_context().add_class('error')
            self.field_error_labels[key].set_text(_(message))
            self.field_error_labels[key].set_visible(True)
            self._highlight_error_tab(self.field_tab_index[key])
        self._validating_only = False
        self._update_actions()

    # ──────────────────────────────────────────────────────────────────────────
    # Saving
    # ──────────────────────────────────────────────────────────────────────────
    def _on_save_clicked(self, button):
        self._start_save()

    def _collect_updated_values(self):
        updated = {}
        for key, widget in self.field_widgets.items():
            if key == '_SECURITY_PRESET':
                continue
            if isinstance(widget, Gtk.Entry):
                txt = widget.get_text()
                if key in ('ENABLE_SERVICES', 'DISABLE_SERVICES'):
                    updated[key] = process_services_field(txt)
                else:
                    updated[key] = txt
            elif getattr(widget, '_boolean_setting', False):
                updated[key] = widget.get_active_id() or ''
            else:
                value = widget.get_active_id()
                if value is None:
                    value = widget.get_active_text() or ''
                updated[key] = normalize_default_target(value) if key == 'DEFAULT_TARGET' else value
        return updated

    def _collect_changes_for_save(self):
        """Return only explicit edits, never effective values shown for defaults."""
        updated = self.state.changes()
        for key in ('ENABLE_SERVICES', 'DISABLE_SERVICES'):
            if key in updated:
                updated[key] = process_services_field(updated[key])
        return updated

    def _save_current_config(self):
        updated = self._collect_changes_for_save()
        save_config(self.config_file_path, self.config_values, updated)
        return updated

    def _set_busy(self, busy):
        self._busy = busy
        for widget in getattr(self, 'field_widgets', {}).values():
            widget.set_sensitive(not busy)
        for button in getattr(self, 'detect_buttons', ()):
            button.set_sensitive(not busy)
        for button in (self.reset_button, self.review_button, self.save_button):
            button.set_sensitive(not busy)

    def _on_detect_clicked(self, button, scope):
        if getattr(self, '_busy', False):
            return
        self._set_busy(True)
        self.dirty_label.set_text(_('Detecting current system settings...'))
        threading.Thread(target=self._detect_worker, args=(scope, button), daemon=True).start()

    def _detect_worker(self, scope, button):
        try:
            detected = detect_current_settings()
            if scope == 'system':
                allowed = {'LIVE_HOSTNAME', 'LIVE_LOCALES', 'LIVE_TIMEZONE', 'DEFAULT_TARGET'}
            else:
                allowed = {
                    'LIVE_KEYBOARD_MODEL', 'LIVE_KEYBOARD_LAYOUTS',
                    'LIVE_KEYBOARD_OPTIONS', 'LIVE_KEYBOARD_VARIANTS',
                }
            detected = {key: value for key, value in detected.items() if key in allowed}
            error = None
        except Exception as exc:
            detected = {}
            error = str(exc)
        GLib.idle_add(self._detect_finished, detected, error, button)

    def _detect_finished(self, detected, error, button):
        if self._destroyed:
            return False
        self._set_busy(False)
        button.set_sensitive(True)
        if error:
            show_error_dialog(self, _('Automatic detection failed: {}').format(error))
            self._update_actions()
            return False
        changed = [
            key for key, value in detected.items()
            if key in self.field_widgets and self.state.get(key) != value
        ]
        for key, value in detected.items():
            if key in self.field_widgets:
                self.state.set(key, value)
        self._set_widgets_from_state()
        if not detected:
            show_error_dialog(self, _('No system settings could be detected.'))
        else:
            if changed:
                if len(changed) == 1:
                    text = _('1 setting updated. Changed fields are highlighted.')
                else:
                    text = _('{count} settings updated. Changed fields are highlighted.').format(
                        count=len(changed)
                    )
            else:
                text = _('Detected settings already match the values shown.')
            show_info_dialog(self, text)
        return False

    def _start_save(self):
        if getattr(self, '_busy', False):
            return
        if not all(self.field_validity.values()):
            show_error_dialog(self, _('Fix invalid fields before saving changes.'))
            return
        updated = self._collect_changes_for_save()
        self._set_busy(True)
        threading.Thread(target=self._save_worker, args=(updated,), daemon=True).start()

    def _save_worker(self, updated):
        saved = False
        error = None
        persisted = None
        try:
            save_config(self.config_file_path, self.config_values, updated)
            persisted = load_config(self.config_file_path)
            saved = True
        except Exception as exc:
            error = str(exc)
        GLib.idle_add(self._save_finished, saved, updated, persisted, error)

    def _save_finished(self, saved, updated, persisted, error):
        if self._destroyed:
            return False
        if saved:
            self.config_values = persisted
            self.state.mark_saved(persisted)
            for key in PASSWORD_FIELD_MAP:
                if updated.get(key):
                    self.required_passwords[key] = False
            self._sync_password_widgets()
        self._set_busy(False)
        self._update_actions()
        if error:
            show_error_dialog(self, _('Settings could not be saved: {}').format(error))
            return False
        show_info_dialog(
            self, _('Settings saved. They will be used on the next boot.'))
        return False

    def _on_destroy(self, _widget):
        self._destroyed = True

    def _sync_password_widgets(self):
        for key in PASSWORD_FIELD_MAP:
            self.field_widgets[key].set_text('')

    def _on_reset_clicked(self, _button):
        if not ask_confirmation(
                self, _('Discard all unsaved changes?'),
                _('The form will return to the currently saved settings.'),
                destructive=True, confirm_label=_('Discard')):
            return
        self.state.reset()
        self._set_widgets_from_state()

    def _set_widgets_from_state(self):
        self._applying_security_preset = True
        for key, widget in self.field_widgets.items():
            if key == '_SECURITY_PRESET':
                continue
            value = self.state.get(key)
            if isinstance(widget, Gtk.Entry):
                widget.set_text(value)
            elif getattr(widget, '_boolean_setting', False):
                widget.set_active_id(
                    value if value in ('true', 'false')
                    else getattr(widget, '_default_setting_id', 'false')
                )
            else:
                effective = value or getattr(widget, '_default_setting_id', '')
                if not widget.set_active_id(effective):
                    widget.set_active(-1)
        preset = self.field_widgets.get('_SECURITY_PRESET')
        if preset is not None:
            preset.set_active_id(self._matching_security_preset())
        self._validate_all_fields()
        self._applying_security_preset = False
        self._update_actions()

    def _on_review_clicked(self, _button):
        dialog = Gtk.Dialog(title=_('Review changes'), transient_for=self, modal=True)
        dialog.add_button(_('Close'), Gtk.ResponseType.CLOSE)
        dialog.set_default_size(680, 440)
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        count = self.state.dirty_count
        heading = Gtk.Label(xalign=0)
        if count == 1:
            heading_text = _('1 setting will change')
        else:
            heading_text = _('{count} settings will change').format(count=count)
        heading.set_markup('<big><b>{}</b></big>'.format(GLib.markup_escape_text(heading_text)))
        box.pack_start(heading, False, False, 0)
        explanation = Gtk.Label(
            label=_('Review the current and new values before saving. Empty values use the MiniOS default.'),
            xalign=0,
        )
        explanation.set_line_wrap(True)
        explanation.get_style_context().add_class('dim-label')
        box.pack_start(explanation, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        changes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        changes_box.set_margin_end(6)
        for item in self.state.diff():
            card = Gtk.Frame()
            card.get_style_context().add_class('review-change-card')
            row = Gtk.Grid(column_spacing=12, row_spacing=3)
            row.set_margin_top(8)
            row.set_margin_bottom(8)
            row.set_margin_start(10)
            row.set_margin_end(10)
            title = Gtk.Label(xalign=0)
            title.set_markup('<b>{}</b>'.format(GLib.markup_escape_text(
                self.field_labels.get(item['key'], item['key'])
            )))
            key_label = Gtk.Label(label=item['key'], xalign=1)
            key_label.get_style_context().add_class('review-key')
            before = item['before'] or _('Not set (use default)')
            after = item['after'] or _('Not set (use default)')
            before_label = Gtk.Label(label=before, xalign=0)
            before_label.set_selectable(True)
            before_label.set_line_wrap(True)
            before_label.get_style_context().add_class('review-before')
            arrow = new_icon('go-next-symbolic', Gtk.IconSize.MENU)
            after_label = Gtk.Label(label=after, xalign=0)
            after_label.set_selectable(True)
            after_label.set_line_wrap(True)
            after_label.get_style_context().add_class('review-after')
            row.attach(title, 0, 0, 2, 1)
            row.attach(key_label, 2, 0, 2, 1)
            row.attach(before_label, 0, 1, 1, 1)
            row.attach(arrow, 1, 1, 1, 1)
            row.attach(after_label, 2, 1, 2, 1)
            card.add(row)
            changes_box.pack_start(card, False, False, 0)
        scrolled.add(changes_box)
        box.pack_start(scrolled, True, True, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

# ──────────────────────────────────────────────────────────────────────────────
# Application class and entry point
# ──────────────────────────────────────────────────────────────────────────────
class MiniOSConfiguratorApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id=APPLICATION_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )
        self.main_window = None
        self.pending_config = None
        self.inherit_cmdline = False

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()

        # Parse command line arguments using argparse
        parser = argparse.ArgumentParser(
            prog=APP_NAME,
            description=_('A graphical tool for configuring MiniOS settings')
        )
        parser.add_argument(
            'config_file',
            nargs='?',
            default=DEFAULT_CONFIG_FILE,
            help=_('Path to config file (default: /etc/live/config.conf)')
        )
        parser.add_argument(
            '-i', '--inherit-cmdline',
            action='store_true',
            help=_('Inherit configuration parameters from kernel command line (/proc/cmdline)')
        )

        try:
            parsed_args = parser.parse_args(args[1:])
            self.pending_config = parsed_args.config_file
            self.inherit_cmdline = parsed_args.inherit_cmdline
        except SystemExit:
            # argparse calls sys.exit on --help or errors
            return 0

        self.activate()
        return 0

    def do_activate(self):
        if self.main_window:
            self.main_window.present()
        else:
            cfg = self.pending_config or DEFAULT_CONFIG_FILE
            self.main_window = ConfiguratorWindow(self, cfg, self.inherit_cmdline)
            self.main_window.show_all()
            self.main_window.present()

def main():
    try:
        app = MiniOSConfiguratorApp()
        return app.run(sys.argv)
    except KeyboardInterrupt:
        return 130
    
if __name__ == '__main__':
    sys.exit(main())
