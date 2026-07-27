#!/usr/bin/env python3

from unittest.mock import mock_open, patch


def test_unknown_posture_keys_round_trip(tmp_path):
    from config_utils import load_config, save_config

    path = tmp_path / 'config.conf'
    path.write_text("LIVE_USERNAME='live'\nLIVE_SUDO_MODE='password'\n", encoding='utf-8')
    values = load_config(str(path))
    save_config(str(path), values, {'LIVE_HOSTNAME': 'box'})
    result = path.read_text(encoding='utf-8')
    assert "LIVE_SUDO_MODE='password'" in result
    assert "LIVE_HOSTNAME='box'" in result


def test_security_field_validation():
    from validation_utils import validate_field

    assert validate_field('LIVE_XRDP_MODE', 'disabled', set(), set(), set(), {})
    assert not validate_field('LIVE_XRDP_MODE', 'open', set(), set(), set(), {})
    assert validate_field('LIVE_SSH_PASSWORD_AUTHENTICATION', 'false', set(), set(), set(), {})
    assert not validate_field('LIVE_SSH_PASSWORD_AUTHENTICATION', 'no', set(), set(), set(), {})


def test_cmdline_maps_security_keys():
    from system_utils import parse_cmdline_params

    data = 'boot=live sudo-mode=password ssh-password-authentication=false issue-password-hints=false'
    with patch('builtins.open', mock_open(read_data=data)):
        parsed = parse_cmdline_params()
    assert 'LIVE_SECURITY_PROFILE' not in parsed
    assert parsed['LIVE_SUDO_MODE'] == 'password'
    assert parsed['LIVE_SSH_PASSWORD_AUTHENTICATION'] == 'false'
    assert parsed['LIVE_ISSUE_PASSWORD_HINTS'] == 'false'


def test_matching_preset_ignores_legacy_profile_marker():
    pytest = __import__('pytest')
    pytest.importorskip('gi')
    from main_configurator import ConfiguratorWindow
    from minios_security.security_profiles import live_config_for_profile

    expected = live_config_for_profile('balanced')
    values = dict(expected)
    values['LIVE_SECURITY_PROFILE'] = 'strict'
    values['LIVE_CONFIG_CMDLINE'] = 'noautologin'

    class State:
        def get(self, key):
            return values.get(key, '')

    window = ConfiguratorWindow.__new__(ConfiguratorWindow)
    window.state = State()
    assert window._matching_security_preset() == 'balanced'
