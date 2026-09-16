from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from main_configurator import ConfiguratorWindow, PasswordEntry


ROOT = Path(__file__).resolve().parents[1]


def test_launcher_elevates_only_non_root_callers():
    launcher = (ROOT / "bin/minios-configurator").read_text(encoding="utf-8")
    desktop = (ROOT / "share/applications/minios-configurator.desktop").read_text(
        encoding="utf-8")

    assert 'if [ "$(id -u)" -ne 0 ]; then' in launcher
    assert 'exec pkexec "$SCRIPT_PATH" "$@"' in launcher
    assert "Exec=/usr/bin/minios-configurator\n" in desktop
    assert "Exec=pkexec" not in desktop


def test_password_entry_construction_is_isolated_from_field_registration():
    password = Mock()
    entry = Mock()
    grid = Mock()
    window = SimpleNamespace(
        _create_password_entry=Mock(return_value=(password, entry)),
        _register_widget=Mock(),
        field_widgets={},
    )

    ConfiguratorWindow._add_password_entry(
        window, grid, 4, 'USER_PASSWORD', 'Password help')

    window._create_password_entry.assert_called_once_with('Password help')
    window._register_widget.assert_called_once_with(entry, 'USER_PASSWORD')
    assert window.field_widgets['USER_PASSWORD'] is entry
    grid.attach.assert_called_once_with(password, 1, 4, 1, 1)


def test_password_entry_uses_shared_toggle_widget_and_retains_entry_contract():
    password = Mock()
    password.entry = Mock()

    with patch('main_configurator.PasswordEntry', return_value=password) as factory:
        widget, entry = ConfiguratorWindow._create_password_entry(
            SimpleNamespace(), 'Password help')

    factory.assert_called_once_with(
        reveal_mode='toggle', show_label='Show password',
        hide_label='Hide password')
    assert widget is password
    assert entry is password.entry
    entry.set_tooltip_text.assert_called_once_with('Password help')
    password.reveal_button.connect.assert_not_called()
    password.reveal_button.set_tooltip_text.assert_not_called()
