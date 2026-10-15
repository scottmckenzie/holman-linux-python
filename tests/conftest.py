"""
Test setup: replace the ``gatt`` library with an in-memory fake.

The real ``gatt`` needs ``python3-dbus`` and a running ``bluetoothd`` (and
calls ``sys.exit`` on import without dbus), so tests never import it.
"""

import sys
import types

import pytest


class FakeDeviceManager:
    def __init__(self, adapter_name):
        self.adapter_name = adapter_name
        self.listener = None
        self.aliases = {}
        self.known_devices = []
        self.discovery_uuids = None
        self.stopped = False

    def devices(self):
        return self.known_devices

    def start_discovery(self, service_uuids=None):
        self.discovery_uuids = service_uuids

    def device_discovered(self, device):
        pass

    def stop(self):
        self.stopped = True


class FakeDevice:
    def __init__(self, mac_address, manager, managed=True):
        self.mac_address = mac_address
        self.manager = manager
        self.services = []
        self.connect_calls = 0
        self.disconnect_calls = 0

    def alias(self):
        return self.manager.aliases.get(self.mac_address, self.mac_address)

    def connect(self):
        self.connect_calls += 1

    def connect_failed(self, error):
        pass

    def disconnect(self):
        self.disconnect_calls += 1

    def disconnect_succeeded(self):
        pass

    def services_resolved(self):
        pass


class FakeService:
    def __init__(self, uuid, characteristics=()):
        self.uuid = uuid
        self.characteristics = list(characteristics)


class FakeCharacteristic:
    def __init__(self, uuid, value=b"\x00"):
        self.uuid = uuid
        self.value = value
        self.written = []

    def read_value(self):
        return self.value

    def write_value(self, value):
        self.written.append(value)


fake_gatt = types.ModuleType("gatt")
fake_gatt.DeviceManager = FakeDeviceManager  # type: ignore[attr-defined]
fake_gatt.Device = FakeDevice  # type: ignore[attr-defined]
sys.modules["gatt"] = fake_gatt

import holman  # noqa: E402


class RecordingListener(holman.TapTimerListener):
    def __init__(self):
        self.events = []

    def started_connecting(self):
        self.events.append("started_connecting")

    def connect_succeeded(self):
        self.events.append("connect_succeeded")

    def connect_failed(self, error):
        self.events.append(("connect_failed", str(error)))

    def started_disconnecting(self):
        self.events.append("started_disconnecting")

    def disconnect_succeeded(self):
        self.events.append("disconnect_succeeded")


@pytest.fixture
def manager():
    return holman.TapTimerManager(adapter_name="hci0")


@pytest.fixture
def tap_timer(manager):
    return holman.TapTimer(mac_address="AA:BB:CC:DD:EE:FF", manager=manager)


@pytest.fixture
def listener(tap_timer):
    tap_timer.listener = RecordingListener()
    return tap_timer.listener


@pytest.fixture
def make_service():
    """Factory for a non-Holman GATT service."""
    return FakeService


@pytest.fixture
def make_holman_service():
    """Factory for a Holman GATT service with optional characteristics."""

    def make(
        service_uuid=holman.TapTimer.HOLMAN_CO3015_SERVICE_UUID,
        state=b"\x00",
        manual=True,
        state_char=True,
    ):
        chars = []
        if manual:
            chars.append(FakeCharacteristic(holman.TapTimer.MANUAL_CHARACTERISTIC_UUID))
        if state_char:
            chars.append(
                FakeCharacteristic(holman.TapTimer.STATE_CHARACTERISTIC_UUID, state)
            )
        return FakeService(service_uuid, chars)

    return make
