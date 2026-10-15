import pytest

import holman
import holmanctl

MAC = "AA:BB:CC:DD:EE:FF"


def run_holmanctl(monkeypatch, *args):
    monkeypatch.setattr("sys.argv", ["holmanctl", *args])
    return holmanctl.main()


def manual_writes(tap_timer):
    return next(
        c.written
        for c in tap_timer.services[0].characteristics
        if c.uuid == holman.TapTimer.MANUAL_CHARACTERISTIC_UUID
    )


def test_connect_failed_finishes_with_error(tap_timer, manager):
    listener = holmanctl.TapTimerTestListener(tap_timer)
    manager.run()
    listener.connect_failed(Exception("boom"))
    assert listener.finished
    assert listener.exit_code == 1
    assert manager.stopped


def test_disconnect_with_auto_reconnect_reconnects(tap_timer, manager):
    listener = holmanctl.TapTimerTestListener(tap_timer, auto_reconnect=True)
    listener.disconnect_succeeded()
    assert tap_timer.connect_calls == 1
    assert not listener.finished


def test_known_lists_tap_timers(monkeypatch, capsys):
    class KnownManager(holman.TapTimerManager):
        def __init__(self, adapter_name):
            super().__init__(adapter_name)
            self.aliases[MAC] = "Tap Timer"
            self.known_devices = [holman.TapTimer(mac_address=MAC, manager=self)]

    monkeypatch.setattr(holman, "TapTimerManager", KnownManager)
    assert run_holmanctl(monkeypatch, "--known") == 0
    assert capsys.readouterr().out == f"[{MAC}] Tap Timer\n"


def test_requires_a_command(monkeypatch):
    with pytest.raises(SystemExit):
        run_holmanctl(monkeypatch)


def test_run_starts_tap_then_disconnects(monkeypatch, capsys, simulated_tap_timer):
    assert run_holmanctl(monkeypatch, "--connect", MAC, "--run", "10") == 0
    (tap_timer,) = simulated_tap_timer.tap_timers
    assert manual_writes(tap_timer) == [bytes([0x01, 0x00, 0x00, 10])]
    assert tap_timer.disconnect_calls == 1
    out = capsys.readouterr().out
    assert "timer written" in out
    assert "Terminate with Ctrl+C" not in out


def test_stop_stops_tap_then_disconnects(monkeypatch, simulated_tap_timer):
    assert run_holmanctl(monkeypatch, "--connect", MAC, "--stop") == 0
    (tap_timer,) = simulated_tap_timer.tap_timers
    assert manual_writes(tap_timer) == [bytes(4)]
    assert tap_timer.disconnect_calls == 1


def test_connect_without_action_writes_nothing(monkeypatch, simulated_tap_timer):
    assert run_holmanctl(monkeypatch, "--connect", MAC) == 0
    (tap_timer,) = simulated_tap_timer.tap_timers
    assert manual_writes(tap_timer) == []
    assert tap_timer.disconnect_calls == 0


def test_run_write_failure_exits_nonzero(monkeypatch, capsys, simulated_tap_timer):
    simulated_tap_timer.write_error = Exception("write rejected")
    assert run_holmanctl(monkeypatch, "--connect", MAC, "--run", "10") == 1
    (tap_timer,) = simulated_tap_timer.tap_timers
    assert tap_timer.disconnect_calls == 1
    assert "timer write failed: write rejected" in capsys.readouterr().out


def test_connect_failure_exits_nonzero_without_running_loop(
    monkeypatch, manager, simulated_tap_timer
):
    # gatt reports some failures synchronously inside connect(), before the
    # loop starts; main() must not then block forever in run().
    monkeypatch.setattr(holman, "TapTimerManager", lambda adapter_name: manager)
    simulated_tap_timer.connect_error = Exception("Device does not exist")
    assert run_holmanctl(monkeypatch, "--connect", MAC, "--run", "10") == 1
    assert not manager.ran


@pytest.mark.parametrize("value", ["0", "256", "-5", "ten", "1.5"])
def test_run_rejects_invalid_minutes(monkeypatch, capsys, value):
    with pytest.raises(SystemExit) as excinfo:
        run_holmanctl(monkeypatch, "--connect", MAC, "--run", value)
    assert excinfo.value.code == 2
    assert "--run" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["1", "255"])
def test_run_accepts_minute_bounds(value):
    assert holmanctl.minutes(value) == int(value)


@pytest.mark.parametrize(
    "args",
    [
        ["--auto", MAC, "--run", "10"],
        ["--auto", MAC, "--stop"],
        ["--discover", "--stop"],
        ["--connect", MAC, "--run", "10", "--stop"],
    ],
)
def test_run_and_stop_only_with_connect(monkeypatch, manager, args):
    monkeypatch.setattr(holman, "TapTimerManager", lambda adapter_name: manager)
    with pytest.raises(SystemExit) as excinfo:
        run_holmanctl(monkeypatch, *args)
    assert excinfo.value.code == 2
    assert not manager.ran


def test_public_api():
    assert set(holman.__all__) == {
        "TapTimer",
        "TapTimerListener",
        "TapTimerManager",
        "TapTimerManagerListener",
    }
