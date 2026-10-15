import holman

MAC = "AA:BB:CC:DD:EE:FF"


class RecordingManagerListener(holman.TapTimerManagerListener):
    def __init__(self):
        self.discovered = []

    def tap_timer_discovered(self, tap_timer):
        self.discovered.append(tap_timer)


def test_start_discovery_filters_on_holman_services(manager):
    manager.start_discovery()
    assert manager.discovery_uuids == holman.TapTimer.SERVICE_UUIDS


def test_make_device_accepts_tap_timer_alias(manager):
    manager.aliases[MAC] = "Tap Timer"
    device = manager.make_device(MAC)
    assert isinstance(device, holman.TapTimer)
    assert device.mac_address == MAC


def test_make_device_rejects_other_alias(manager):
    manager.aliases[MAC] = "Some Speaker"
    assert manager.make_device(MAC) is None


def test_device_discovered_notifies_once_per_device(manager):
    manager.listener = RecordingManagerListener()
    tap_timer = holman.TapTimer(mac_address=MAC, manager=manager)
    manager.device_discovered(tap_timer)
    manager.device_discovered(tap_timer)
    assert manager.listener.discovered == [tap_timer]
    assert manager.discovered_tap_timers == {MAC: tap_timer}


def test_device_discovered_without_listener(manager):
    manager.device_discovered(holman.TapTimer(mac_address=MAC, manager=manager))
