import machine
import errno
import network
import sys
import logging
from machine import lightsleep, Pin, Timer
from mini_server import serve_website
import urequests as requests    # noqa
import time
import _credetials

SSID = _credetials.SSID
WIFI_PWD = _credetials.WIFI_PWD
URL = _credetials.URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(None)  # root
error = logger.error
debug = logger.debug
info = logger.info

ap = network.WLAN(network.AP_IF)
wlan = network.WLAN(network.STA_IF)
tim0 = Timer(0)
LED = Pin(2, Pin.OUT)


def wlan_connect(ssid, pwd) -> bool:
    ap.active(False)
    wlan.active(True)
    if not wlan.isconnected():
        info("connecting to network..")
        wlan.connect(ssid, pwd)
        for i in range(60):
            info(f"waiting.. ({i})")
            if wlan.isconnected():
                info("connected :D")
                break
            time.sleep(1)
        else:
            info("failed :(")
            return False
    info(f"network config: {wlan.ifconfig()}")
    return True


def ap_connect(
    essid="miniSyno",
    channel=8,
    authmode=network.AUTH_WPA_WPA2_PSK,
    password="make syno great again",
):
    wlan.active(False)
    ap.active(True)
    ap.config(essid=essid, password=password, channel=channel, authmode=authmode)
    info(f"created wifi access point:\n\tSSID: {essid}\n\tPWD: {password}")


def toggle_led():
    LED.value(LED.value() ^ 1)


def is_syno_open():
    # todo: use select.poll
    #   https://docs.micropython.org/en/v1.19.1/library/select.html#select.poll
    try:
        debug(f"request: GET {URL}")
        r = requests.get(URL)
        if r.status_code != 200:
            raise ConnectionError(f"status code: {r.status_code}")
        isopen = r.content.decode()
        if isopen in ["True", "False"]:
            return eval(isopen)
        raise ValueError(f"got unknown value {isopen}")
    except Exception as e:
        error(f"{type(e)}: {e}")


def loop():
    global SSID, WIFI_PWD
    isopen = False
    wlan_connect(SSID, WIFI_PWD)

    while True:

        while wlan.isconnected():
            wasopen, isopen = isopen, is_syno_open()
            if isopen != wasopen:
                info(f"syno is open: {isopen}")
                LED.on() if isopen else LED.off()
            time.sleep_ms(1000)

        # seems we have no wifi
        # todo timeout
        ap_connect()
        ssid, pwd = serve_website()
        # todo put in permanent storage
        SSID, WIFI_PWD = ssid, pwd
        wlan_connect(SSID, WIFI_PWD)


def test():
    ap_connect()
    serve_website()

DEBUG = True

if __name__ == "__main__":
    print("enter setup")
    # let's calm down a bit
    machine.freq(80000000)
    time.sleep(1)
    if DEBUG:
        print("enter test")
        test()
    else:
        print("enter loop")
        loop()
