import machine
import errno
import network
import sys
import logging
from machine import lightsleep, Pin, Timer

import fnertlib
from mini_server import serve_website
import urequests as requests  # noqa
import time

URL = None

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('main')  # root
error = logger.error
debug = logger.debug
info = logger.info

ap = network.WLAN(network.AP_IF)
wlan = network.WLAN(network.STA_IF)
tim0 = Timer(0)
LED = Pin(2, Pin.OUT)


def wlan_connect(ssid, pwd):
    ap.active(False)
    wlan.active(False)  # reset wlan
    wlan.active(True)
    info("connecting to network..")
    wlan.connect(ssid, pwd)
    for i in range(60):
        if wlan.isconnected():
            info("connected :D")
            info(f"network config: {wlan.ifconfig()}")
            return
        info(f"waiting.. ({i})")
        time.sleep(1)
    info("failed :(")


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
    info(f"created wifi access point:\n\tSSID: {essid}\n\tPWD: {password}")
    info(f"connect to: 192.168.4.1")


def toggle_led():
    LED.value(LED.value() ^ 1)


def is_syno_open():
    # todo: use select.poll
    #   https://docs.micropython.org/en/v1.19.1/library/select.html#select.poll
    debug(f"request: GET {URL}")
    r = requests.get(URL)
    if r.status_code != 200:
        raise OSError(9999, f"status code: {r.status_code}")
    isopen = r.content.decode()
    if isopen in ["True", "False"]:
        return eval(isopen)
    raise ValueError(f"got unknown return value from URL: {isopen}")


DEFAULT_WEBSITE_TO = 5*60  # 1h


def ap_and_website(timeout):
    tim0.init(mode=Timer.PERIODIC, period=500, callback=lambda t: toggle_led())
    ap_connect()
    ssid, pwd = serve_website(timeout)
    tim0.deinit()
    LED.off()
    return ssid, pwd


def loop():
    ssid, pwd = ap_and_website(30)  # serve website for 5 sec
    if ssid:
        fnertlib.store_wifi_config(ssid, pwd)

    state = 'WIFI'
    isopen = False
    err_count = 0
    request_count = 0
    our_server_timeout = DEFAULT_WEBSITE_TO

    # transitions of statemachine
    # WEB<->WEB         AP<->AP
    #     ^------>WIFI<----^
    # start -------^
    while True:
        time.sleep_ms(100)
        info(f"{state=}, {isopen=}, {err_count=}, {request_count=}, {our_server_timeout=}")

        if state == 'WIFI':
            ssid, pwd = fnertlib.load_wifi_config()
            wlan_connect(ssid, pwd)
            if wlan.isconnected():
                state = 'WEB'
            else:
                state = 'AP'

        elif state == 'WEB':
            err = None
            wasopen = isopen
            try:
                isopen = is_syno_open()
            except Exception as e:
                err = e

            if err:
                error(repr(err))
                if isinstance(err, OSError) and err.errno in [errno.EHOSTUNREACH, 9999]:
                    time.sleep(300)  # wait 5 min and retry
                err_count += 1
                if not wlan.isconnected():
                    state = 'WIFI'
                if err_count > 10:
                    isopen = False
                    LED.off()
                continue
            err_count = 0

            LED.on() if isopen else LED.off()

            request_count += 1
            if isopen != wasopen:
                request_count = 0

            if request_count < 60:
                time.sleep(1)
            else:
                time.sleep(60)

        elif state == 'AP':
            ap_and_website(our_server_timeout)
            if ssid:
                fnertlib.store_wifi_config(ssid, pwd)
                our_server_timeout = DEFAULT_WEBSITE_TO
            else:
                our_server_timeout += 5 * 60  # add 5 min
            # either try new wifi config or the old again
            state = 'WIFI'


def simple_run():
    try:
        ssid, pwd = ap_and_website(30)  # serve website for 30 sec
        if ssid:
            fnertlib.store_wifi_config(ssid, pwd)
        ssid, pwd = fnertlib.load_wifi_config()
        wlan_connect(ssid, pwd)

        if not wlan.isconnected():
            raise ConnectionError("could not connect to wifi")

        # for 30min check every second ..
        for _ in range(30 * 60):
            isopen = is_syno_open()
            LED.on() if isopen else LED.off()
            time.sleep(1)

        # now we get lazy and just check every minute
        while True:
            isopen = is_syno_open()
            LED.on() if isopen else LED.off()
            time.sleep(60)

    except Exception:
        # wait 5min and then perform a reset
        # and we start again
        machine.deepsleep(5 * 60 * 1000)


def test():
    try:
        LED.on()
        time.sleep(1)
        raise ValueError('lala')
    except Exception:
        machine.deepsleep(1000)


def trap(msg: str = ""):
    _msg = 'trapped'
    if msg:
        _msg += ": " + msg
    while True:
        print(_msg)
        time.sleep(5)


def strore_credentials_initial(ssid, pwd, url):
    fnertlib.store_wifi_config(ssid, pwd)
    fnertlib.store_str_in_NVS("syno", "url", url)
    # fnertlib.store_str_in_NVS('system', 'loglevel ', "done")
    fnertlib.store_str_in_NVS('system', 'init', "done")


try:
    URL = fnertlib.load_str_from_NVS("syno", "url")
except OSError as e:
    trap(f"{repr(e)}. Most likely no initial credentials was provided..")

if __name__ == "__main__":

    print("enter setup")
    # let's calm down a bit
    machine.freq(80000000)
    time.sleep(1)
    test()
    # print("enter loop")
    # loop()
    trap('END OF PROGRAM')
