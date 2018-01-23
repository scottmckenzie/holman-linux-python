"""
Module for managing Holman Bluetooth tap timers.
"""
import gatt


class TapTimerManager(gatt.DeviceManager):
    """
    Entry point for managing and discovering Holman ``TapTimer``s.
    """

    def __init__(self, adapter_name='hci0'):
        """
        Instantiates a ``TapTimerManager``

        :param adapter_name: name of Bluetooth adapter used by this
                             tap timer manager
        """
        super().__init__(adapter_name)
        self.listener = None
        self.discovered_tap_timers = {}

    def tap_timers(self):
        """
        Returns all known Holman tap timers.
        """
        return self.devices()

    def start_discovery(self, service_uuids=None):
        """
        Starts a Bluetooth discovery for Holman tap timers.

        Assign a `TapTimerManagerListener` to the `listener` attribute
        to collect discovered Holmans.
        """
        super().start_discovery(service_uuids=TapTimer.SERVICE_UUIDS)

    def make_device(self, mac_address):
        device = gatt.Device(
            mac_address=mac_address, manager=self, managed=False)
        if device.alias() != 'Tap Timer':
            return None
        return TapTimer(mac_address=mac_address, manager=self)

    def device_discovered(self, device):
        super().device_discovered(device)
        if device.mac_address in self.discovered_tap_timers:
            return
        self.discovered_tap_timers[device.mac_address] = device
        if self.listener is not None:
            self.listener.tap_timer_discovered(device)


class TapTimerManagerListener(object):
    """
    Base class for receiving discovery events from ``TapTimerManager``.

    Assign an instance of your subclass to the ``listener`` attribute
    of your ``TapTimerManager`` to receive discovery events.
    """

    def tap_timer_discovered(self, tap_timer):
        """
        This method gets called once for each Holman tap timer
        discovered nearby.

        :param tap_timer: the Holman tap timer that was discovered
        """
        pass


class TapTimer(gatt.Device):
    """
    This class represents a Holman tap timer.

    Obtain instances of this class by using the discovery mechanism of
    ``TapTimerManager`` or by manually creating an instance.

    Assign an instance of ``TapTimerListener`` to the ``listener``
    attribute to receive all Holman related events such as connection,
    disconnection and user input.

    :param adapter_name: name of Bluetooth adapter that can connect to
    this tap timer
    :param mac_address: MAC address of this Holman tap timer
    :param listener: instance of ``TapTimerListener`` that will be
    notified with all events
    """

    HOLMAN_SERVICE_UUID = '0a75f000-f9ad-467a-e564-3c19163ad543'
    STATE_CHARACTERISTIC_UUID = '0000f004-0000-1000-8000-00805f9b34fb'
    MANUAL_CHARACTERISTIC_UUID = '0000f006-0000-1000-8000-00805f9b34fb'

    SERVICE_UUIDS = [
        HOLMAN_SERVICE_UUID]

    def __init__(self, mac_address, manager):
        """
        Create an instance with given Bluetooth adapter name and MAC
        address.

        :param mac_address: MAC address of Holman tap timer with
        format: ``AA:BB:CC:DD:EE:FF``
        :param manager: reference to the `TapTimerManager` that manages
        this tap timer
        """
        super().__init__(mac_address=mac_address, manager=manager)

        self.listener = None
        self._battery_level = None
        self._manual_characteristic = None
        self._state_characteristic = None
        self._state = bytes([0])

    def connect(self):
        """
        Tries to connect to this Holman tap timer and blocks until it
        has connected or failed to connect.

        Notifies ``listener`` as soon has the connection has succeeded
        or failed.
        """
        if self.listener:
            self.listener.started_connecting()
        super().connect()

    def connect_failed(self, error):
        super().connect_failed(error)
        if self.listener:
            self.listener.connect_failed(error)

    def disconnect(self):
        """
        Disconnects this Holman tap timer if connected.

        Notifies ``listener`` as soon as Holman was disconnected.
        """
        if self.listener:
            self.listener.started_disconnecting()
        self._refresh_state()
        super().disconnect()

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        if self.listener:
            self.listener.disconnect_succeeded()

    def services_resolved(self):
        super().services_resolved()

        holman_service = next((
            service for service in self.services
            if service.uuid == self.HOLMAN_SERVICE_UUID), None)
        if holman_service is None:
            if self.listener:
                # TODO: Use proper exception subclass
                self.listener.connect_failed(
                    Exception("Holman GATT service missing"))
            return

        self._manual_characteristic = next((
            char for char in holman_service.characteristics
            if char.uuid == self.MANUAL_CHARACTERISTIC_UUID), None)
        if self._manual_characteristic is None:
            # TODO: Use proper exception subclass
            self.listener.connect_failed(
                Exception(
                    "Holman GATT characteristic %s missing",
                    self.MANUAL_CHARACTERISTIC_UUID))
            return

        self._state_characteristic = next((
            char for char in holman_service.characteristics
            if char.uuid == self.STATE_CHARACTERISTIC_UUID), None)
        if self._state_characteristic is None:
            # TODO: Use proper exception subclass
            self.listener.connect_failed(
                Exception(
                    "Holman GATT characteristic %s missing",
                    self.STATE_CHARACTERISTIC_UUID))
            return
        self._refresh_state()

        # TODO: Only fire connected event when we read the firmware
        # version or battery value as in other SDKs
        if self.listener:
            self.listener.connect_succeeded()

    def battery_level(self):
        # TODO: determine which byte in state is used for battery level
        return self._battery_level

    def _refresh_state(self):
        if self._state_characteristic:
            self._state = self._state_characteristic.read_value()

    @property
    def is_on(self):
        """Return true if tap is running."""
        self._refresh_state()
        return self._state[-1] == 1

    @property
    def name(self):
        """The name of the tap timer."""
        return str(self.alias())

    def start(self, runtime=1):
        """
        Turn on the tap for ```runtime``` minutes.

        :param runtime: the number of minutes to run the tap
        """
        runtime = 255 if runtime > 255 else runtime
        if self._manual_characteristic:
            value = bytes([0x01, 0x00, 0x00, runtime])
            self._manual_characteristic.write_value(value)

    def stop(self):
        """Turn off the tap."""
        if self._manual_characteristic:
            value = bytes([0x00, 0x00, 0x00, 0x00])
            self._manual_characteristic.write_value(value)

    def characteristic_write_value_succeeded(self, characteristic):
        self._refresh_state()

    def characteristic_write_value_failed(self, characteristic, error):
        self._refresh_state()


class TapTimerListener:
    """
    Base class of listeners for a ``TapTimer`` with empty handler
    implementations.
    """
    def started_connecting(self):
        pass

    def connect_succeeded(self):
        pass

    def connect_failed(self, error):
        pass

    def started_disconnecting(self):
        pass

    def disconnect_succeeded(self):
        pass
