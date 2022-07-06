# -*- coding: utf-8 -*-

"""
Dependency::

    pip3 install pyobjc-framework-Cocoa
    pip3 install pyobjc-framework-Quartz

Usage::

    python3 xx.py
"""


import logging
import os
from functools import partial

from AppKit import NSKeyUp, NSEvent, NSBundle
import Quartz
from AppKit import NSSystemDefined

logger = logging.getLogger(__name__)


def keyboard_tap_callback(key_queue, proxy, type_, event, refcon):
    NSBundle.mainBundle().infoDictionary()['NSAppTransportSecurity'] =\
        dict(NSAllowsArbitraryLoads=True)
    if type_ < 0 or type_ > 0x7fffffff:
        logger.error('Unkown mac event')
        run_event_loop()
        logger.error('restart mac key board event loop')
        return event
    try:
        key_event = NSEvent.eventWithCGEvent_(event)
    except:  # noqa
        logger.info("mac event cast error")
        return event
    if key_event.subtype() == 8:
        key_code = (key_event.data1() & 0xFFFF0000) >> 16
        key_state = (key_event.data1() & 0xFF00) >> 8
        if key_code in (16, 19, 20):
            # 16 for play-pause, 19 for next, 20 for previous
            if key_state == NSKeyUp:
                if key_code == 19:
                    logger.info('mac hotkey: play next')
                    key_queue.put('next')
                elif key_code == 20:
                    logger.info('mac hotkey: play last')
                    key_queue.put('previous')
                elif key_code == 16:
                    logger.info('mac hotkey: play or pause')
                    key_queue.put('play_pause')
            return None
    return event


def run_event_loop(key_queue):
    logger.info("try to load mac hotkey event loop")

    # Set up a tap, with type of tap, location, options and event mask
    tap = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap,  # Session level is enough for our needs
        Quartz.kCGHeadInsertEventTap,  # Insert wherever, we do not filter
        Quartz.kCGEventTapOptionDefault,
        # NSSystemDefined for media keys
        Quartz.CGEventMaskBit(NSSystemDefined),
        partial(keyboard_tap_callback, key_queue),
        None
    )

    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(
        None, tap, 0)
    Quartz.CFRunLoopAddSource(
        Quartz.CFRunLoopGetCurrent(),
        run_loop_source,
        Quartz.kCFRunLoopDefaultMode
    )
    # Enable the tap
    Quartz.CGEventTapEnable(tap, True)
    # and run! This won't return until we exit or are terminated.
    Quartz.CFRunLoopRun()
    logger.error('Mac hotkey event loop exit')


if __name__ == '__main__':
    run_event_loop()