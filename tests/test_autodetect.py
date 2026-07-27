from unittest.mock import mock_open, patch

from system_utils import detect_current_settings


def test_detect_current_settings_uses_session_values():
    keyboard = 'XKBMODEL="pc105"\nXKBLAYOUT="us,ru"\nXKBOPTIONS="grp:alt_shift_toggle"\n'

    def open_file(path, *args, **kwargs):
        if path == '/etc/timezone':
            return mock_open(read_data='Europe/Berlin\n')()
        if path == '/etc/default/keyboard':
            return mock_open(read_data=keyboard)()
        raise OSError(path)

    with patch('builtins.open', side_effect=open_file), \
         patch('system_utils.socket.gethostname', return_value='minios-test'), \
         patch.dict('system_utils.os.environ', {'LANG': 'de_DE.UTF-8'}, clear=False), \
         patch('system_utils.subprocess.check_output', return_value='graphical.target\n'):
        result = detect_current_settings()

    assert result['LIVE_HOSTNAME'] == 'minios-test'
    assert result['LIVE_LOCALES'] == 'de_DE.UTF-8'
    assert result['LIVE_TIMEZONE'] == 'Europe/Berlin'
    assert result['LIVE_KEYBOARD_LAYOUTS'] == 'us,ru'
    assert result['DEFAULT_TARGET'] == 'graphical.target'
