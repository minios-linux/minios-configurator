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

    class Task:
        def __init__(self, worker, finished_callback, owner):
            captured['worker'] = worker
            captured['finished_callback'] = finished_callback
            captured['owner'] = owner
            captured['locked'] = not field.sensitive and not detect.sensitive

        def start(self):
            captured['started'] = True
            return self

    monkeypatch.setattr(main_configurator, 'BackgroundTask', Task)
    window._start_save()

    assert captured['locked']
    assert captured['owner'] is window
    assert captured['started']


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

    class Task:
        def __init__(self, worker, finished_callback, owner):
            captured.append({
                'worker': worker,
                'finished_callback': finished_callback,
                'owner': owner,
                'locked': not field.sensitive and not detect_keyboard.sensitive,
            })

        def start(self):
            return self

    monkeypatch.setattr(main_configurator, 'BackgroundTask', Task)
    window._on_detect_clicked(detect_system, 'system')
    window._on_detect_clicked(detect_keyboard, 'keyboard')

    assert len(captured) == 1
    assert captured[0]['owner'] is window
    assert captured[0]['locked']

    monkeypatch.setattr(
        main_configurator, 'detect_current_settings',
        lambda: {'LIVE_HOSTNAME': 'detected', 'LIVE_KEYBOARD_MODEL': 'pc105'})
    assert captured[0]['worker'](None) == {'LIVE_HOSTNAME': 'detected'}
