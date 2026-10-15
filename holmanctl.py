#!/usr/bin/env python3

import sys
from argparse import ArgumentParser, ArgumentTypeError

import holman


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

    def timer_written(self):
        self.print("timer written")

    def timer_write_failed(self, error):
        self.print("timer write failed: " + str(error))

    def print(self, string):
        print("Holman tap timer " + self.tap_timer.mac_address + " " + string)


class TapTimerTestListener(TapTimerPrintListener):
    """
    Drives ``holmanctl``: optionally starts or stops the tap once connected,
    then disconnects and stops the event loop.

    ``exit_code`` is 0 on success and 1 if connecting or writing failed.
    ``finished`` is set once there is nothing left to wait for.

    :param run_minutes: start the tap for this many minutes once connected
    :param stop_tap: stop the tap once connected
    """

    def __init__(
        self, tap_timer, auto_reconnect=False, run_minutes=None, stop_tap=False
    ):
        super().__init__(tap_timer)
        self.auto_reconnect = auto_reconnect
        self.run_minutes = run_minutes
        self.stop_tap = stop_tap
        self.exit_code = 0
        self.finished = False

    def connect_succeeded(self):
        super().connect_succeeded()
        if self.run_minutes is not None:
            self.tap_timer.start(runtime=self.run_minutes)
        elif self.stop_tap:
            self.tap_timer.stop()

    def connect_failed(self, error):
        super().connect_failed(error)
        self.exit_code = 1
        self._finish()

    def timer_written(self):
        super().timer_written()
        # Disconnect rather than just exiting: BlueZ would otherwise keep
        # the connection open after this process is gone.
        self.tap_timer.disconnect()

    def timer_write_failed(self, error):
        super().timer_write_failed(error)
        self.exit_code = 1
        self.tap_timer.disconnect()

    def disconnect_succeeded(self):
        super().disconnect_succeeded()

        if self.auto_reconnect:
            # Reconnect as soon as Holman was disconnected
            print("Disconnected, reconnecting...")
            self.tap_timer.connect()
        else:
            self._finish()

    def _finish(self):
        # gatt can report a failure synchronously from inside connect(),
        # before the event loop runs; stop() is a no-op then, so main()
        # also checks ``finished`` before calling run().
        self.finished = True
        self.tap_timer.manager.stop()


class TapTimerManagerPrintListener(holman.TapTimerManagerListener):
    def tap_timer_discovered(self, tap_timer):
        print("Discovered Holman tap timer", tap_timer.mac_address)


def minutes(value):
    """argparse type for a tap runtime: a whole number of minutes, 1-255."""
    try:
        runtime = int(value)
    except ValueError:
        raise ArgumentTypeError(f"invalid number of minutes: {value!r}") from None
    if not 1 <= runtime <= 255:
        raise ArgumentTypeError(f"must be between 1 and 255 minutes, got {runtime}")
    return runtime


def main():
    arg_parser = ArgumentParser(description="Holman Tap Timer Demo")
    arg_parser.add_argument(
        "--adapter",
        default="hci0",
        help="Name of Bluetooth adapter, defaults to 'hci0'",
    )
    arg_commands_group = arg_parser.add_mutually_exclusive_group(required=True)
    arg_commands_group.add_argument(
        "--discover", action="store_true", help="Lists all nearby Holman tap timers"
    )
    arg_commands_group.add_argument(
        "--known", action="store_true", help="Lists all known Holman tap timers"
    )
    arg_commands_group.add_argument(
        "--connect",
        metavar="address",
        type=str,
        help="Connect to a Holman tap timer with a given MAC address",
    )
    arg_commands_group.add_argument(
        "--auto",
        metavar="address",
        type=str,
        help="Connect and automatically reconnect to a Holman tap timer "
        "with a given MAC address",
    )
    arg_commands_group.add_argument(
        "--disconnect",
        metavar="address",
        type=str,
        help="Disconnect a Holman tap timer with a given MAC address",
    )
    arg_action_group = arg_parser.add_mutually_exclusive_group()
    arg_action_group.add_argument(
        "--run",
        metavar="minutes",
        type=minutes,
        help="With --connect: run the tap for 1-255 minutes, then exit",
    )
    arg_action_group.add_argument(
        "--stop",
        action="store_true",
        help="With --connect: stop the tap, then exit",
    )
    args = arg_parser.parse_args()

    one_shot = args.run is not None or args.stop
    if one_shot and not args.connect:
        arg_parser.error("--run and --stop require --connect")

    tap_timer_manager = holman.TapTimerManager(adapter_name=args.adapter)
    listener = None

    if args.discover:
        tap_timer_manager.listener = TapTimerManagerPrintListener()
        tap_timer_manager.start_discovery()
    if args.known:
        for tap_timer in tap_timer_manager.tap_timers():
            print(f"[{tap_timer.mac_address}] {tap_timer.alias()}")
        return 0
    elif args.connect:
        tap_timer = holman.TapTimer(mac_address=args.connect, manager=tap_timer_manager)
        listener = TapTimerTestListener(
            tap_timer=tap_timer, run_minutes=args.run, stop_tap=args.stop
        )
        tap_timer.listener = listener
        tap_timer.connect()
    elif args.auto:
        tap_timer = holman.TapTimer(mac_address=args.auto, manager=tap_timer_manager)
        listener = TapTimerTestListener(tap_timer=tap_timer, auto_reconnect=True)
        tap_timer.listener = listener
        tap_timer.connect()
    elif args.disconnect:
        tap_timer = holman.TapTimer(
            mac_address=args.disconnect, manager=tap_timer_manager
        )
        tap_timer.disconnect()
        return 0

    if listener and listener.finished:
        return listener.exit_code
    if not one_shot:
        print("Terminate with Ctrl+C")
    try:
        tap_timer_manager.run()
    except KeyboardInterrupt:
        pass
    return listener.exit_code if listener else 0


if __name__ == "__main__":
    sys.exit(main())
