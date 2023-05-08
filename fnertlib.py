#!/usr/bin/env python
import esp32  # noqa
from machine import Pin
import machine
import time
import network


RESET_CAUSES = {
    machine.PWRON_RESET: "POWERON_RESET",
    machine.HARD_RESET: "HARD_RESET",
    machine.WDT_RESET: "WDT_RESET",
    machine.DEEPSLEEP_RESET: "DEEPSLEEP_RESET",
    machine.SOFT_RESET: "SOFT_RESET",
}

# now extra dependencies pls
wlan = network.WLAN(network.STA_IF)
ap = network.WLAN(network.AP_IF)
GLOBAL_GPIO_HOLD = False


class WakePin:
    def __init__(self, pid, pull):
        self.pid = pid
        self.pin = Pin(pid, Pin.IN, pull, hold=True)

    def wake_on(self, level):
        """level is 0 or 1"""
        if level in ["low", 0, False, "L", "l"]:
            level = esp32.WAKEUP_ALL_LOW
        else:
            level = esp32.WAKEUP_ANY_HIGH
        esp32.wake_on_ext0(pin=self.pin, level=level)
        print(f"waiting for {self.pin} to become {'high' if level else 'low'}")

    def value(self, value=None):
        if value is not None:
            self.pin.value(value)
        return self.pin.value()


class LedPin:
    def __init__(self, pid, value=None, keep_state_on_sleep=False):
        self.pid = pid
        self.pin = Pin(pid, mode=Pin.OUT, value=value)
        self.hold = None
        self.keep_state_on_sleep(keep_state_on_sleep)
        self.commit()

    def value(self, value=None):
        if value is not None:
            self.pin.value(value)
            self.commit()
        return self.pin.value()

    def commit(self):
        # setting or re-setting False or True
        # will apply all changes immediately
        Pin(self.pid, hold=self.hold)

    def keep_state_on_sleep(self, value: bool):
        self.hold = value
        self.commit()

    def on(self):
        self.pin.on()
        self.commit()

    def off(self):
        self.pin.off()
        self.commit()

    def toggle(self):
        self.pin.value(self.pin.value() ^ 1)
        self.commit()

    def blink(
        self,
        blinks: int,
        period: int = 1000,
        dutycycle: float = 0.5,
        maxtime: int = None,
    ):
        """
        Blink the status LED.
        `blinks` is ignored if `maxtime` is given.
        """
        Pin(self.pid, hold=False)
        laststate = self.pin.value()
        high = int(period * dutycycle)
        low = int(period * (1 - dutycycle))
        if maxtime is None and laststate == 1:
            # we have a defined number of blinks, but we
            # start with the LED on, so we blink one more
            blinks += 1
        if maxtime is not None:
            blinks = maxtime // period
        for _ in range(blinks):
            self.on()
            time.sleep_ms(high)
            self.off()
            time.sleep_ms(low)
        self.pin.value(laststate)
        self.commit()


def deepsleep(ms: int):
    print("Going to deepsleep", end="")
    if ms > 5000:
        ms -= 5000
        for i in range(5):
            time.sleep(1)
            print(".", end="")
    print()
    machine.deepsleep(ms)


def cat(path):
    with open(path) as f:
        print(f"File {path}\n{'=' * len(path)}")
        for line in f:
            print(line, end="")
        print()


def bytearray_find(buf, b):
    for i, c in enumerate(buf):
        if c == b:
            return i
    return -1


def store_str_in_NVS(ns: str, key: str, value):
    ns = esp32.NVS(ns)
    ns.set_blob(key, value.encode())
    ns.commit()


def load_str_from_NVS(ns, key, max_size=128):
    ns = esp32.NVS(ns)
    buf = bytearray(max_size)
    ns.get_blob(key, buf)
    i = max(bytearray_find(buf, 0), 0)
    value = buf[:i].decode()
    return value


def store_wifi_config(ssid: str, pwd: str):
    ns = esp32.NVS("wifi")
    ns.set_blob("ssid", ssid.encode())
    ns.set_blob("pwd", pwd.encode())
    ns.commit()


def load_wifi_config():
    ssid = load_str_from_NVS("wifi", "ssid", 512)
    pwd = load_str_from_NVS("wifi", "pwd", 512)
    return ssid, pwd


def wlan_connect(ssid=None, pwd=None):
    """autoload wifi config from storage if ssid=None"""
    if ssid is None:
        ssid, pwd = load_wifi_config()
    wlan.active(False)  # reset wlan
    wlan.active(True)
    print("WLAN: connecting to network..")
    wlan.connect(ssid, pwd)
    for i in range(30):
        if wlan.isconnected():
            print("WLAN: connected :D")
            print(f"WLAN: network config: {wlan.ifconfig()}")
            return
        print(f"WLAN: waiting.. ({i})")
        time.sleep(1)
    print("WLAN: failed :(")


def ap_connect(
        essid="miniSyno",
        channel=8,
        authmode=network.AUTH_WPA_WPA2_PSK,
        password="make syno great again",
):
    wlan.active(False)
    ap.active(False)  # reset ap
    ap.active(True)
    ap.config(essid=essid, password=password, channel=channel, authmode=authmode)
    print(f"AP: created wifi access point:\n\tSSID: {essid}\n\tPWD: {password}")
    print(f"AP: connect to: 192.168.4.1")


