from config_state import ConfigState


def test_source_inherited_dirty_reset_and_saved():
    state = ConfigState({'LIVE_HOSTNAME': 'disk'}, {'LIVE_HOSTNAME': 'boot'})
    assert state.source['LIVE_HOSTNAME'] == 'disk'
    assert state.inherited['LIVE_HOSTNAME'] == 'boot'
    assert state.get('LIVE_HOSTNAME') == 'boot'
    state.set('LIVE_HOSTNAME', 'edited')
    assert state.dirty_count == 1
    state.reset()
    assert state.get('LIVE_HOSTNAME') == 'boot'
    assert state.dirty_count == 0


def test_password_diff_is_redacted():
    state = ConfigState({}, password_fields=('USER_PASSWORD',))
    state.set('USER_PASSWORD', 'never-show-this')
    diff = state.diff()
    assert diff[0]['after'] == 'Password will be changed'
    assert 'never-show-this' not in repr(diff)


def test_ui_default_is_not_dirty():
    state = ConfigState({})
    state.set_default('LIVE_SUDO_MODE', 'password')
    assert state.get('LIVE_SUDO_MODE') == 'password'
    assert state.dirty_count == 0
