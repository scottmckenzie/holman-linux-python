import pytest

import holman

MANUAL = holman.TapTimer.MANUAL_CHARACTERISTIC_UUID
UNLOCK = holman.TapTimer.UNLOCK_CHARACTERISTIC_UUID


def resolve(tap_timer, *services):
    tap_timer.services = list(services)
    tap_timer.services_resolved()


def manual_char(tap_timer):
    return next(c for c in tap_timer.services[0].characteristics if c.uuid == MANUAL)


def unlock_char(tap_timer):
    return next(c for c in tap_timer.services[0].characteristics if c.uuid == UNLOCK)


@pytest.mark.parametrize("uuid", holman.TapTimer.SERVICE_UUIDS)
def test_services_resolved_connects_for_each_model(
    make_holman_service, tap_timer, listener, uuid
):
    resolve(tap_timer, make_holman_service(service_uuid=uuid))
    assert listener.events == ["connect_succeeded"]


def test_services_resolved_without_holman_service_fails(
    make_service, tap_timer, listener
):
    resolve(tap_timer, make_service("00001800-0000-1000-8000-00805f9b34fb"))
    assert listener.events == [("connect_failed", "Holman GATT service missing")]


@pytest.mark.parametrize(
    ("kwargs", "missing"),
    [
        ({"manual": False}, holman.TapTimer.MANUAL_CHARACTERISTIC_UUID),
        ({"state_char": False}, holman.TapTimer.STATE_CHARACTERISTIC_UUID),
    ],
)
def test_services_resolved_missing_characteristic_fails(
    make_holman_service, tap_timer, listener, kwargs, missing
):
    resolve(tap_timer, make_holman_service(**kwargs))
    assert listener.events == [
        ("connect_failed", f"Holman GATT characteristic {missing} missing")
    ]


def test_services_resolved_missing_characteristic_without_listener(
    make_holman_service, tap_timer
):
    resolve(tap_timer, make_holman_service(manual=False))  # must not raise


@pytest.mark.parametrize(
    ("state", "is_on"), [(b"\x00\x01", True), (b"\x01\x00", False)]
)
def test_is_on_reads_last_state_byte(make_holman_service, tap_timer, state, is_on):
    resolve(tap_timer, make_holman_service(state=state))
    assert tap_timer.is_on is is_on


@pytest.mark.parametrize(
    ("runtime", "minutes"), [(1, 1), (30, 30), (255, 255), (600, 255)]
)
def test_start_writes_runtime_capped_at_255(
    make_holman_service, tap_timer, runtime, minutes
):
    resolve(tap_timer, make_holman_service())
    tap_timer.start(runtime=runtime)
    assert manual_char(tap_timer).written == [bytes([0x01, 0x00, 0x00, minutes])]


def test_stop_writes_off(make_holman_service, tap_timer):
    resolve(tap_timer, make_holman_service())
    tap_timer.stop()
    assert manual_char(tap_timer).written == [bytes(4)]


def test_start_and_stop_before_connect_are_noops(tap_timer):
    tap_timer.start()
    tap_timer.stop()


def test_connect_and_disconnect_notify_listener(tap_timer, listener):
    tap_timer.connect()
    tap_timer.disconnect()
    tap_timer.disconnect_succeeded()
    assert listener.events == [
        "started_connecting",
        "started_disconnecting",
        "disconnect_succeeded",
    ]
    assert tap_timer.connect_calls == 1
    assert tap_timer.disconnect_calls == 1


def test_connect_failed_notifies_listener(tap_timer, listener):
    tap_timer.connect_failed(Exception("boom"))
    assert listener.events == [("connect_failed", "boom")]


def test_battery_level_not_decoded(tap_timer):
    assert tap_timer.battery_level() is None


def test_write_succeeded_on_manual_characteristic_notifies(
    make_holman_service, tap_timer, listener
):
    resolve(tap_timer, make_holman_service())
    listener.events.clear()
    tap_timer.characteristic_write_value_succeeded(manual_char(tap_timer))
    assert listener.events == ["timer_written"]


def test_write_failed_on_manual_characteristic_notifies(
    make_holman_service, tap_timer, listener
):
    resolve(tap_timer, make_holman_service())
    listener.events.clear()
    tap_timer.characteristic_write_value_failed(manual_char(tap_timer), "rejected")
    assert listener.events == [("timer_write_failed", "rejected")]


def test_write_on_other_characteristic_does_not_notify(
    make_holman_service, tap_timer, listener
):
    resolve(tap_timer, make_holman_service())
    listener.events.clear()
    state = next(c for c in tap_timer.services[0].characteristics if c.uuid != MANUAL)
    tap_timer.characteristic_write_value_succeeded(state)
    tap_timer.characteristic_write_value_failed(state, "rejected")
    assert listener.events == []


def test_base_listener_accepts_write_events(make_holman_service, tap_timer):
    # Listeners written before these events existed must keep working.
    tap_timer.listener = holman.TapTimerListener()
    resolve(tap_timer, make_holman_service())
    tap_timer.characteristic_write_value_succeeded(manual_char(tap_timer))
    tap_timer.characteristic_write_value_failed(manual_char(tap_timer), "rejected")


@pytest.mark.parametrize("zone", [1, 2])
@pytest.mark.parametrize("runtime", [1, 255])
def test_start_selects_bx2_outlet(make_holman_service, tap_timer, zone, runtime):
    resolve(tap_timer, make_holman_service())
    tap_timer.start(runtime=runtime, zone=zone)
    assert manual_char(tap_timer).written == [bytes([1, zone - 1, 0, runtime])]


@pytest.mark.parametrize("zone", [0, 3, -1, True, False, 1.0, 2.0, "2", None])
def test_invalid_zone_never_writes(make_holman_service, tap_timer, zone):
    resolve(tap_timer, make_holman_service())
    with pytest.raises(ValueError, match="zone must be 1 or 2"):
        tap_timer.start(zone=zone)
    assert manual_char(tap_timer).written == []


def test_unlock_written_before_connecting(make_holman_service, tap_timer, listener):
    resolve(tap_timer, make_holman_service(unlock=True))
    assert unlock_char(tap_timer).written == [bytes([0xAE, 0x8E])]
    assert listener.events == []


def test_unlock_success_finishes_connecting(make_holman_service, tap_timer, listener):
    resolve(tap_timer, make_holman_service(state=b"\x00\x01", unlock=True))
    tap_timer.characteristic_write_value_succeeded(unlock_char(tap_timer))
    assert listener.events == ["connect_succeeded"]
    assert tap_timer.is_on is True


def test_unlock_failure_fails_connecting(make_holman_service, tap_timer, listener):
    resolve(tap_timer, make_holman_service(unlock=True))
    tap_timer.characteristic_write_value_failed(unlock_char(tap_timer), "rejected")
    assert listener.events == [
        ("connect_failed", "Holman unlock write failed: rejected")
    ]


def test_unlock_without_listener(make_holman_service, tap_timer):
    resolve(tap_timer, make_holman_service(unlock=True))
    tap_timer.characteristic_write_value_succeeded(unlock_char(tap_timer))
    tap_timer.characteristic_write_value_failed(unlock_char(tap_timer), "rejected")


def test_no_unlock_characteristic_skips_unlock(make_holman_service, tap_timer):
    resolve(tap_timer, make_holman_service())
    assert tap_timer._unlock_characteristic is None
