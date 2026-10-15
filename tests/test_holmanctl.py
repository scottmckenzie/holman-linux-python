import pytest

import holman
import holmanctl


def test_connect_failed_stops_manager_and_exits(tap_timer, manager):
    listener = holmanctl.TapTimerTestListener(tap_timer)
    with pytest.raises(SystemExit):
        listener.connect_failed(Exception("boom"))
    assert manager.stopped


def test_disconnect_with_auto_reconnect_reconnects(tap_timer, manager):
    listener = holmanctl.TapTimerTestListener(tap_timer, auto_reconnect=True)
    listener.disconnect_succeeded()
    assert tap_timer.connect_calls == 1
    assert not manager.stopped


def test_known_lists_tap_timers(monkeypatch, capsys):
    class KnownManager(holman.TapTimerManager):
        def __init__(self, adapter_name):
            super().__init__(adapter_name)
            self.aliases["AA:BB:CC:DD:EE:FF"] = "Tap Timer"
            self.known_devices = [
                holman.TapTimer(mac_address="AA:BB:CC:DD:EE:FF", manager=self)
            ]

    monkeypatch.setattr(holman, "TapTimerManager", KnownManager)
    monkeypatch.setattr("sys.argv", ["holmanctl", "--known"])
    holmanctl.main()
    assert capsys.readouterr().out == "[AA:BB:CC:DD:EE:FF] Tap Timer\n"


def test_requires_a_command(monkeypatch):
    monkeypatch.setattr("sys.argv", ["holmanctl"])
    with pytest.raises(SystemExit):
        holmanctl.main()


def test_public_api():
    assert set(holman.__all__) == {
        "TapTimer",
        "TapTimerListener",
        "TapTimerManager",
        "TapTimerManagerListener",
    }
