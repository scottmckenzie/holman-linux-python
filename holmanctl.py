#!/usr/bin/env python3

import sys
from argparse import ArgumentParser
import holman

tap_timer_manager = None


class TapTimerPrintListener(holman.TapTimerListener):
    """
    An implementation of ``TapTimerListener`` that prints each event.
    """
    def __init__(self, tap_timer):
        self.tap_timer = tap_timer

    def started_connecting(self):
        self.print("connecting...")

    def connect_succeeded(self):
        self.print("connected")

    def connect_failed(self, error):
        self.print("connect failed: " + str(error))

    def started_disconnecting(self):
        self.print("disconnecting...")

    def disconnect_succeeded(self):
        self.print("disconnected")

    def print(self, string):
        print("Holman tap timer " + self.tap_timer.mac_address + " " + string)


class TapTimerTestListener(TapTimerPrintListener):
    def __init__(self, tap_timer, auto_reconnect=False):
        super().__init__(tap_timer)
        self.auto_reconnect = auto_reconnect

    def connect_failed(self, error):
        super().connect_failed(error)
        tap_timer_manager.stop()
        sys.exit(0)

    def disconnect_succeeded(self):
        super().disconnect_succeeded()

        if self.auto_reconnect:
            # Reconnect as soon as Holman was disconnected
            print("Disconnected, reconnecting...")
            self.tap_timer.connect()
        else:
            tap_timer_manager.stop()
            sys.exit(0)


class TapTimerManagerPrintListener(holman.TapTimerManagerListener):
    def tap_timer_discovered(self, tap_timer):
        print("Discovered Holman tap timer", tap_timer.mac_address)


def main():
    arg_parser = ArgumentParser(description="Holman Tap Timer Demo")
    arg_parser.add_argument(
        '--adapter',
        default='hci0',
        help="Name of Bluetooth adapter, defaults to 'hci0'")
    arg_commands_group = arg_parser.add_mutually_exclusive_group(required=True)
    arg_commands_group.add_argument(
        '--discover',
        action='store_true',
        help="Lists all nearby Holman tap timers")
    arg_commands_group.add_argument(
        '--known',
        action='store_true',
        help="Lists all known Holman tap timers")
    arg_commands_group.add_argument(
        '--connect',
        metavar='address',
        type=str,
        help="Connect to a Holman tap timer with a given MAC address")
    arg_commands_group.add_argument(
        '--auto',
        metavar='address',
        type=str,
        help="Connect and automatically reconnect to a Holman tap timer with a given MAC address")
    arg_commands_group.add_argument(
        '--disconnect',
        metavar='address',
        type=str,
        help="Disconnect a Holman tap timer with a given MAC address")
    args = arg_parser.parse_args()

    global tap_timer_manager
    tap_timer_manager = holman.TapTimerManager(adapter_name=args.adapter)

    if args.discover:
        tap_timer_manager.listener = TapTimerManagerPrintListener()
        tap_timer_manager.start_discovery()
    if args.known:
        for tap_timer in tap_timer_manager.tap_timers():
            print("[%s] %s" % (tap_timer.mac_address, tap_timer.alias()))
        return
    elif args.connect:
        tap_timer = holman.TapTimer(mac_address=args.connect, manager=tap_timer_manager)
        tap_timer.listener = TapTimerTestListener(tap_timer=tap_timer)
        tap_timer.connect()
    elif args.auto:
        tap_timer = holman.TapTimer(mac_address=args.auto, manager=tap_timer_manager)
        tap_timer.listener = TapTimerTestListener(tap_timer=tap_timer, auto_reconnect=True)
        tap_timer.connect()
    elif args.disconnect:
        tap_timer = holman.TapTimer(mac_address=args.disconnect, manager=tap_timer_manager)
        tap_timer.disconnect()
        return

    print("Terminate with Ctrl+C")
    try:
        tap_timer_manager.run()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
