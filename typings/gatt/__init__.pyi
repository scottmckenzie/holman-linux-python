# gatt picks its backend with a runtime platform.system() check, which type
# checkers can't narrow. This SDK is Linux-only, so resolve to the BlueZ backend.
from gatt.gatt_linux import Characteristic as Characteristic
from gatt.gatt_linux import Device as Device
from gatt.gatt_linux import DeviceManager as DeviceManager
from gatt.gatt_linux import Service as Service
