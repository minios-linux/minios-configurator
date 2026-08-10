from config_state import ConfigState
from main_configurator import ConfiguratorWindow


class Control:
    def __init__(self):
        self.sensitive = True
        self.text = ''

    def set_sensitive(self, sensitive):
        self.sensitive = sensitive

    def set_text(self, text):
        self.text = text


def test_busy_state_locks_fields_and_all_detection_actions():
    window = ConfiguratorWindow.__new__(ConfiguratorWindow)
    field = Control()
    detect_system = Control()
    detect_keyboard = Control()
    window.field_widgets = {'LIVE_HOSTNAME': field}
    window.detect_buttons = [detect_system, detect_keyboard]
    window.reset_button = Control()
    window.review_button = Control()
    window.save_button = Control()

    window._set_busy(True)

    assert not field.sensitive
    assert not detect_system.sensitive
    assert not detect_keyboard.sensitive
    assert not window.reset_button.sensitive
    assert not window.review_button.sensitive
    assert not window.save_button.sensitive


def test_save_locks_mutating_controls_before_worker_starts(monkeypatch):
    import main_configurator

    window = ConfiguratorWindow.__new__(ConfiguratorWindow)
    window._busy = False
    window.state = ConfigState({'LIVE_HOSTNAME': 'old'})
    window.state.set('LIVE_HOSTNAME', 'saved-value')
    window.field_validity = {'LIVE_HOSTNAME': True}
    field = Control()
    detect = Control()
    window.field_widgets = {'LIVE_HOSTNAME': field}
    window.detect_buttons = [detect]
    window.reset_button = Control()
    window.review_button = Control()
    window.save_button = Control()
    captured = {}

    class WorkerThread:
        def __init__(self, target, args, daemon):
            captured['target'] = target
            captured['updated'] = args[0]
            captured['locked'] = not field.sensitive and not detect.sensitive
            captured['daemon'] = daemon

        def start(self):
            pass

    monkeypatch.setattr(main_configurator.threading, 'Thread', WorkerThread)
    window._start_save()

    assert captured['target'] == window._save_worker
    assert captured['updated'] == {'LIVE_HOSTNAME': 'saved-value'}
    assert captured['locked']
    assert captured['daemon'] is True


def test_detection_locks_controls_and_ignores_reentry(monkeypatch):
    import main_configurator

    window = ConfiguratorWindow.__new__(ConfiguratorWindow)
    window._busy = False
    field = Control()
    detect_system = Control()
    detect_keyboard = Control()
    window.field_widgets = {'LIVE_HOSTNAME': field}
    window.detect_buttons = [detect_system, detect_keyboard]
    window.reset_button = Control()
    window.review_button = Control()
    window.save_button = Control()
    window.dirty_label = Control()
    captured = []

    class WorkerThread:
        def __init__(self, target, args, daemon):
            captured.append({
                'target': target,
                'args': args,
                'locked': not field.sensitive and not detect_keyboard.sensitive,
                'daemon': daemon,
            })

        def start(self):
            pass

    monkeypatch.setattr(main_configurator.threading, 'Thread', WorkerThread)
    window._on_detect_clicked(detect_system, 'system')
    window._on_detect_clicked(detect_keyboard, 'keyboard')

    assert len(captured) == 1
    assert captured[0]['target'] == window._detect_worker
    assert captured[0]['args'] == ('system', detect_system)
    assert captured[0]['locked']
    assert captured[0]['daemon'] is True
