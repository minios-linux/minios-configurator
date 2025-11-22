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

# Add lib directory to Python path
sys.path.insert(0, '/usr/lib/minios-configurator')

# Import our library modules
from config_utils import load_config, save_config, process_services_field
from system_utils import (read_available_locales, read_available_services,
                          get_available_timezones, parse_cmdline_params)
from validation_utils import validate_field
from ui_utils import (apply_css_if_exists, show_error_dialog, create_completion,
                      on_toggle_password_visibility, ICON_WINDOW, ICON_WARNING,
                      ICON_SAVE, ICON_EYE_OPEN)
from password_utils import PASSWORD_FIELD_MAP, get_required_passwords, get_previous_password_hashes

gi.require_version('Gtk', '3.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Gdk, Gio

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
           "• Helps retain user data across reboots.\n\n"
           "• FAT, NTFS only.\n\n"
           "See: man 7 live-config (search 'link-user-dirs')")),
        (_("Bind user directories to storage"), 'LIVE_BIND_USER_DIRS', Gtk.CheckButton,
         _("If enabled, user home directories will be bind-mounted to persistent storage.\n\n"
           "• Helps retain user data across reboots.\n\n"
           "• FAT, NTFS only.\n\n"
           "See: man 7 live-config (search 'bind-user-dirs')")),
        (_("User directories path on storage"), 'LIVE_USER_DIRS_PATH', Gtk.Entry,
         _("Set the base path on persistent storage for user directories.\n\n"
           "• Example: '/minios/userdirs'.\n\n"
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
        (_("Default systemd target"), 'DEFAULT_TARGET', Gtk.ComboBoxText,
         _("Set the default boot target for systemd:\n"
           "• 'graphical' – start with a desktop.\n"
           "• 'multi-user' – console mode.\n"
           "• 'rescue' – minimal rescue mode.\n\n"
           "See: man systemd.special (search for 'target')")),
        (_("Enable services"), 'ENABLE_SERVICES', Gtk.Entry,
         _("List systemd services to enable at boot, separated by commas.\n\n"
           "• Example: 'ssh, NetworkManager'.\n"
           "• Use service names with or without '.service'.\n\n"
           "See: man systemctl (search 'enable')")),
        (_("Disable services"), 'DISABLE_SERVICES', Gtk.Entry,
         _("List systemd services to disable at boot, separated by commas.\n\n"
           "• Example: 'bluetooth, ModemManager'.\n"
           "• Use service names with or without '.service'.\n\n"
           "See: man systemctl (search 'disable')")),
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
         _("If enabled, system logs will be copied to a connected flash drive at shutdown.\n\n"
           "• Useful for diagnostics and troubleshooting.\n\n"
           "See: https://github.com/minios-linux/minios-live/wiki")),
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# Main Configurator Window
# ──────────────────────────────────────────────────────────────────────────────
class ConfiguratorWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application, config_path: str, inherit_cmdline: bool = False):
        super().__init__(application=application, title=_(APP_TITLE))
        self.set_default_size(600, 450)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_name(ICON_WINDOW)

        # Internal state
        self.config_file_path = config_path
        self.config_values = {}
        self.field_widgets = {}
        self.field_validity = {}
        self.previous_password_hashes = {}
        self.field_tab_index = {}

        # Load config and track required password fields
        try:
            self.config_values = load_config(self.config_file_path)
        except Exception as e:
            show_error_dialog(self, str(e))
            return

        # If inherit_cmdline flag is set, merge cmdline parameters
        if inherit_cmdline:
            cmdline_params = parse_cmdline_params()
            # Cmdline parameters override config file values
            self.config_values.update(cmdline_params)

        self.previous_password_hashes = get_previous_password_hashes(self.config_values)
        self.required_passwords = get_required_passwords(self.config_values)

        # Load system data
        self.available_locales = read_available_locales()
        self.available_timezones = get_available_timezones()
        self.available_services = read_available_services()

        # Apply CSS if available
        apply_css_if_exists(CSS_FILE_PATH)

        # Build the UI
        self._build_header_bar()
        self._build_main_layout()

        # Run initial validation
        self._validate_all_fields()

    # ──────────────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────────────
    def _build_header_bar(self):
        header = Gtk.HeaderBar(show_close_button=True)
        header.props.title = _(APP_TITLE)
        self.set_titlebar(header)

    def _build_main_layout(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for m in ('set_margin_top', 'set_margin_bottom', 'set_margin_start', 'set_margin_end'):
            getattr(container, m)(10)
        self.add(container)

        self._add_warning_label(container)
        self.notebook = Gtk.Notebook()
        container.pack_start(self.notebook, True, True, 0)
        self._populate_tabs()
        self._add_save_button(container)

    def _add_warning_label(self, parent: Gtk.Box):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.START)
        icon = Gtk.Image.new_from_icon_name(ICON_WARNING, Gtk.IconSize.DIALOG)
        label = Gtk.Label()
        label.set_text(
            _('If you are unsure about a field, do not change it. '
              'Incorrect settings may prevent the system from booting.')
        )
        label.set_line_wrap(True)
        label.set_max_width_chars(80)
        label.set_xalign(0)
        box.pack_start(icon, False, False, 0)
        box.pack_start(label, True, True, 0)
        parent.pack_start(box, False, False, 0)

    def _populate_tabs(self):
        for tab_index, (tab_label, fields) in enumerate(TAB_DEFINITIONS.items()):
            grid = Gtk.Grid(column_spacing=10, row_spacing=10)
            grid.set_column_homogeneous(False)
            for m in ('set_margin_top', 'set_margin_bottom', 'set_margin_start', 'set_margin_end'):
                getattr(grid, m)(10)

            for row_index, (label_text, key, widget_cls, tooltip) in enumerate(fields):
                self._add_field_row(grid, row_index, tab_index, label_text, key, widget_cls, tooltip)

            scrolled = Gtk.ScrolledWindow()
            scrolled.set_hexpand(True)
            scrolled.set_vexpand(True)
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled.add(grid)
            self.notebook.append_page(scrolled, Gtk.Label(label=tab_label))

    def _add_field_row(self, grid, row, tab_index, label_text, key, widget_cls, tooltip):
        label = Gtk.Label(label=label_text, xalign=0)
        label.set_tooltip_text(tooltip)
        if key in self.required_passwords and self.required_passwords[key]:
            label.set_text(label.get_text() + " *")
        grid.attach(label, 0, row, 1, 1)
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
        entry.set_visibility(False)
        entry.set_hexpand(True)
        entry.set_tooltip_text(tooltip)
        toggle = Gtk.ToggleButton()
        icon = Gtk.Image.new_from_icon_name(ICON_EYE_OPEN, Gtk.IconSize.BUTTON)
        toggle.set_image(icon)
        toggle.set_always_show_image(True)
        toggle.connect('toggled', on_toggle_password_visibility, entry)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_hexpand(True)
        box.pack_start(entry, True, True, 0)
        box.pack_start(toggle, False, False, 0)
        self._register_widget(entry, key)
        self.field_widgets[key] = entry
        grid.attach(box, 1, row, 1, 1)

    def _add_text_entry(self, grid, row, key, tooltip):
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        entry.set_text(self.config_values.get(key, ''))
        entry.set_tooltip_text(tooltip)
        if key in ('LIVE_LOCALES', 'LIVE_TIMEZONE', 'ENABLE_SERVICES', 'DISABLE_SERVICES'):
            self._attach_inline_completion(entry, key)
        self._register_widget(entry, key)
        self.field_widgets[key] = entry
        grid.attach(entry, 1, row, 1, 1)

    def _add_check_button(self, grid, row, key, tooltip):
        check = Gtk.CheckButton()
        check.set_hexpand(True)
        check.set_active(self.config_values.get(key, '').lower() == 'true')
        check.set_tooltip_text(tooltip)
        self.field_validity[key] = True
        self.field_widgets[key] = check
        grid.attach(check, 1, row, 1, 1)

    def _add_combo_box(self, grid, row, key, tooltip):
        combo = Gtk.ComboBoxText()
        combo.set_hexpand(True)
        options = ['simple', 'merged'] if key == 'LIVE_MODULE_MODE' else ['graphical', 'multi-user', 'rescue']
        for opt in options:
            combo.append_text(opt)
        current = self.config_values.get(key, '')
        combo.set_active(options.index(current) if current in options else -1)
        combo.set_tooltip_text(tooltip)
        self._register_widget(combo, key, is_combo=True)
        self.field_widgets[key] = combo
        grid.attach(combo, 1, row, 1, 1)

    def _attach_inline_completion(self, entry, key):
        items = {
            'LIVE_LOCALES': self.available_locales,
            'LIVE_TIMEZONE': self.available_timezones,
            'ENABLE_SERVICES': self.available_services,
            'DISABLE_SERVICES': self.available_services,
        }[key]
        completion = create_completion(items, entry)
        entry.set_completion(completion)

    def _add_save_button(self, parent):
        self.save_button = Gtk.Button(label=_('Save'))
        self.save_button.get_style_context().add_class('suggested-action')
        icon = Gtk.Image.new_from_icon_name(ICON_SAVE, Gtk.IconSize.BUTTON)
        self.save_button.set_image(icon)
        self.save_button.set_always_show_image(True)
        self.save_button.connect('clicked', self._on_save_clicked)
        parent.pack_end(self.save_button, False, False, 0)

    # ──────────────────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────────────────
    def _register_widget(self, widget, key, is_combo=False):
        widget.connect('changed', lambda w: self._on_field_changed(w, key, is_combo))
        self.field_validity[key] = False

    def _on_field_changed(self, widget, key, is_combo):
        value = widget.get_active_text() if is_combo else widget.get_text()
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
        self.save_button.set_sensitive(all(self.field_validity.values()))

    def _highlight_error_tab(self, tab_index):
        page = self.notebook.get_nth_page(tab_index)
        label = self.notebook.get_tab_label(page)
        keys = [k for k, idx in self.field_tab_index.items() if idx == tab_index]
        has_error = any(not self.field_validity.get(k, True) for k in keys)
        ctx = label.get_style_context()
        if has_error:
            ctx.add_class('error-tab')
        else:
            ctx.remove_class('error-tab')

    def _validate_all_fields(self):
        for key, widget in self.field_widgets.items():
            if isinstance(widget, Gtk.CheckButton):
                self.field_validity[key] = True
            else:
                is_combo = isinstance(widget, Gtk.ComboBoxText)
                self._on_field_changed(widget, key, is_combo)

    # ──────────────────────────────────────────────────────────────────────────
    # Saving
    # ──────────────────────────────────────────────────────────────────────────
    def _on_save_clicked(self, button):
        updated = {}
        for key, widget in self.field_widgets.items():
            if isinstance(widget, Gtk.Entry):
                txt = widget.get_text()
                if key in ('ENABLE_SERVICES', 'DISABLE_SERVICES'):
                    updated[key] = process_services_field(txt)
                else:
                    updated[key] = txt
            elif isinstance(widget, Gtk.CheckButton):
                updated[key] = 'true' if widget.get_active() else 'false'
            else:
                updated[key] = widget.get_active_text() or ''

        try:
            save_config(self.config_file_path, self.config_values, updated)
        except Exception as e:
            show_error_dialog(self, str(e))

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
