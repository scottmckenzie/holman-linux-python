# Holman Python SDK
[Holman CO3015](https://www.holmanindustries.com.au/products/bluetooth-tap-timer-co3015/)
and [BTX1](https://www.holmanindustries.com.au/products/btx1-tap-mounted-smart-valve/) are Bluetooth tap timers made by [Holman](https://www.holmanindustries.com.au/).

The Holman Python SDK for Linux allows you to integrate your Holman(s) into any type of Linux application or script that can execute Python code.

## Prerequisites
The Holman SDK requires [Python 3.4+](https://www.python.org) and a recent installation of [BlueZ](http://www.bluez.org/). It is tested to work fine with BlueZ 5.44, slightly older versions should however work, too.

## Installation
These instructions assume a Debian-based Linux.

On Linux the [BlueZ](http://www.bluez.org/) library is necessary to access your built-in Bluetooth controller or Bluetooth USB dongle. Some Linux distributions provide a more up-to-date BlueZ package, some other distributions only install older versions that don't implement all Bluetooth features needed for this SDK. In those cases you want to either update BlueZ or build it from sources.

### Updating/installing BlueZ via apt-get

1. `bluetoothd --version` Obtains the version of the pre-installed BlueZ. `bluetoothd` daemon must run at startup to expose the Bluetooth API via D-Bus.
2. `sudo apt-get install --no-install-recommends bluetooth` Installs BlueZ
3. If the installed version is too old, proceed with next step: [Installing BlueZ from sources](#installing-bluez-from-sources)

### Installing BlueZ from sources

The `bluetoothd` daemon provides BlueZ's D-Bus interfaces that is accessed by the Holman SDK to communicate with Holman Bluetooth tap timers. The following commands download BlueZ 5.44 sources, built them and replace any pre-installed `bluetoothd` daemon. It's not suggested to remove any pre-installed BlueZ package as its deinstallation might remove necessary Bluetooth drivers as well.

1. `sudo systemctl stop bluetooth`
2. `sudo apt-get update`
3. `sudo apt-get install libusb-dev libdbus-1-dev libglib2.0-dev libudev-dev libical-dev libreadline-dev libdbus-glib-1-dev unzip`
4. `cd`
5. `mkdir bluez`
6. `cd bluez`
7. `wget http://www.kernel.org/pub/linux/bluetooth/bluez-5.44.tar.xz`
8. `tar xf bluez-5.44.tar.xz`
9. `cd bluez-5.44`
10. `./configure --prefix=/usr --sysconfdir=/etc --localstatedir=/var --enable-library`
11. `make`
12. `sudo make install`
13. `sudo ln -svf /usr/libexec/bluetooth/bluetoothd /usr/sbin/`
14. `sudo install -v -dm755 /etc/bluetooth`
15. `sudo install -v -m644 src/main.conf /etc/bluetooth/main.conf`
16. `sudo systemctl daemon-reload`
17. `sudo systemctl start bluetooth`
18. `bluetoothd --version` # should now print 5.44

Please note that some distributions might use a different directory for system deamons, apply step 13 only as needed.

### Enabling your Bluetooth adapter

1. `echo "power on" | sudo bluetoothctl` Enables your built-in Bluetooth adapter or external Bluetooth USB dongle

### Using BlueZ commandline tools
BlueZ also provides an interactive commandline tool to interact with Bluetooth devices. You know that your BlueZ installation is working fine if it discovers any Bluetooth devices nearby.

`sudo bluetoothctl` Starts an interactive mode to talk to BlueZ
  * `power on` Enables the Bluetooth adapter
  * `scan on` Start Bluetooth device scanning and lists all found devices with MAC addresses
  * `connect AA:BB:CC:DD:EE:FF` Connects to a Holman tap timer with specified MAC address
  * `exit` Quits the interactive mode

### Installing Holman Python SDK

To install Holman module and the Python3 D-Bus dependency globally, run:

```
sudo pip3 install holman
sudo apt-get install python3-dbus
```

#### Running the Holman control script

To test if your setup is working, run the following command. Note that it must be run as root because on Linux, Bluetooth discovery is a restricted operation.

```
sudo holmanctl --discover
sudo holmanctl --connect AA:BB:CC:DD:EE:FF # Replace the MAC address with your Holman's MAC address
sudo holmanctl --help # To list all available commands
```

## SDK Usage

### Discovering nearby Holman tap timers

The SDK entry point is the `TapTimerManager` class. Check the following example to dicover any Holman tap timer nearby.

Please note that communication with your Bluetooth adapter happens over BlueZ's D-Bus API, hence an event loop needs to be run in order to receive all Bluetooth related events. You can start and stop the event loop via `run()` and `stop()` calls to your `TapTimerManager` instance.


```python
import holman

class TapTimerManagerPrintListener(holman.TapTimerManagerListener):
    def tap_timer_discovered(self, tap_timer):
        print("Discovered Holman tap_timer", tap_timer.mac_address)

manager = holman.TapTimerManager(adapter_name='hci0')
manager.listener = TapTimerManagerPrintListener()
manager.start_discovery()
manager.run()
```

### Connecting to a Holman tap timer and receiving user input events

Once `TapTimerManager` has discovered a Holman tap timer you can use the `TapTimer` object(s) that you retrieved from `TapTimerManager.tap_timers()` to connect to it. Alternatively you can create a new instance of `TapTimer` using the name of your Bluetooth adapter (typically `hci0`) and Holman's MAC address.

Make sure to assign a `TapTimerListener` object to the `listener` attribute of your TapTimer instance. It will notify you about all Holman tap timer related events such connection, disconnection and user input events.

The following example connects to a Holman tap timer manually:

```python
import holman

manager = holman.TapTimerManager(adapter_name='hci0')

tap_timer = holman.TapTimer(mac_address='AA:BB:CC:DD:EE:FF', manager=manager)
tap_timer.listener = holman.TapTimerListener() # Use an instance of your own holman.TapTimerListener subclass
tap_timer.connect()

manager.run()
```

As with Holman tap timer discovery, remember to start the Bluetooth event loop with `TapTimerManager.run()`.

### Start the tap running

Once a Holman tap timer is connected you can start the tap with `TapTimer.start(runtime=1)`.  Pass this a runtime (in minutes) for how long to run the tap.

## Support

Please open an issue.

## Contributing

Contributions are welcome via pull requests. Please open an issue first in case you want to discus your possible improvements to this SDK.

## License

The Holman Python SDK is available under the MIT License.
