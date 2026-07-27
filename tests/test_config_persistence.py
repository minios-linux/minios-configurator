import os
import stat

import pytest

import config_utils
from config_utils import load_config, save_config


def test_atomic_save_preserves_document_mode_and_quotes(tmp_path):
    path = tmp_path / 'config.conf'
    path.write_text("# heading\nUNKNOWN='keep'\nLIVE_HOSTNAME='old'\n# tail\n")
    os.chmod(str(path), 0o640)
    save_config(str(path), load_config(str(path)), {'LIVE_HOSTNAME': "mini'os"})
    text = path.read_text()
    assert text == "# heading\nUNKNOWN='keep'\nLIVE_HOSTNAME='mini'\\''os'\n# tail\n"
    assert load_config(str(path))['LIVE_HOSTNAME'] == "mini'os"
    assert stat.S_IMODE(os.stat(str(path)).st_mode) == 0o640


def test_new_keys_append_without_reordering_existing_lines(tmp_path):
    path = tmp_path / 'config.conf'
    path.write_text('FIRST=one\n# retained\nSECOND=two\n')
    save_config(str(path), load_config(str(path)), {'THIRD': 'three'})
    assert path.read_text() == "FIRST=one\n# retained\nSECOND=two\nTHIRD='three'\n"


def test_save_only_persists_dirty_values(tmp_path, monkeypatch):
    from config_state import ConfigState
    import main_configurator
    from main_configurator import ConfiguratorWindow

    path = tmp_path / 'config.conf'
    path.write_text("LIVE_HOSTNAME='disk'\nLIVE_SUDO_MODE='passwordless'\n")
    state = ConfigState(load_config(str(path)))
    state.set('LIVE_HOSTNAME', 'edited')
    window = ConfiguratorWindow.__new__(ConfiguratorWindow)
    window.state = state
    window.field_validity = {'LIVE_HOSTNAME': True}

    class Button:
        def set_sensitive(self, _value):
            pass

    window.reset_button = Button()
    window.review_button = Button()
    window.save_button = Button()
    captured = {}

    class WorkerThread:
        def __init__(self, target, args, daemon):
            captured['target'] = target
            captured['updated'] = args[0]
            captured['daemon'] = daemon

        def start(self):
            pass

    monkeypatch.setattr(main_configurator.threading, 'Thread', WorkerThread)
    window._start_save()
    assert captured['target'] == window._save_worker
    assert captured['updated'] == {'LIVE_HOSTNAME': 'edited'}
    assert captured['daemon'] is True
    save_config(str(path), state.source, captured['updated'])

    assert load_config(str(path)) == {
        'LIVE_HOSTNAME': 'edited',
        'LIVE_SUDO_MODE': 'passwordless',
    }


def test_symlink_config_is_rejected(tmp_path):
    target = tmp_path / 'target.conf'
    path = tmp_path / 'config.conf'
    target.write_text("LIVE_HOSTNAME='old'\n")
    path.symlink_to(target)

    with pytest.raises(Exception, match='Failed to (load|update) config'):
        load_config(str(path))
    with pytest.raises(Exception, match='Failed to update config'):
        save_config(str(path), {}, {'LIVE_HOSTNAME': 'new'})
    assert target.read_text() == "LIVE_HOSTNAME='old'\n"


def test_atomic_save_preserves_user_extended_attributes(tmp_path):
    path = tmp_path / 'config.conf'
    path.write_text("LIVE_HOSTNAME='old'\n")
    try:
        os.setxattr(path, 'user.minios-test', b'present')
    except OSError as exc:
        pytest.skip('filesystem does not support user extended attributes: {}'.format(exc))

    save_config(str(path), load_config(str(path)), {'LIVE_HOSTNAME': 'new'})
    assert os.getxattr(path, 'user.minios-test') == b'present'


def test_failed_atomic_replace_leaves_original_untouched(tmp_path, monkeypatch):
    path = tmp_path / 'config.conf'
    original = "LIVE_HOSTNAME='old'\n"
    path.write_text(original)

    def fail_replace(_source, _destination):
        raise OSError('simulated replacement failure')

    monkeypatch.setattr(config_utils.os, 'replace', fail_replace)
    with pytest.raises(Exception):
        save_config(str(path), load_config(str(path)), {'LIVE_HOSTNAME': 'new'})
    assert path.read_text() == original
    assert list(tmp_path.iterdir()) == [path]
