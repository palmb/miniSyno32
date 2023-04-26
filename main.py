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
logger = logging.getLogger("main")  # root

ap = network.WLAN(network.AP_IF)
wlan = network.WLAN(network.STA_IF)
tim0 = Timer(0)
led = Pin(2, Pin.OUT)

RESET_CAUSES = {
    machine.PWRON_RESET: "POWERON_RESET",
    machine.HARD_RESET: "HARD_RESET",
    machine.WDT_RESET: "WDT_RESET",
    machine.DEEPSLEEP_RESET: "DEEPSLEEP_RESET",
    machine.SOFT_RESET: "SOFT_RESET",
}


class MyWDT:
    instance = None

    def __init__(self, timeout):
        if MyWDT.instance is not None:
            MyWDT.instance.stop()
        MyWDT.instance = self

        self.timeout = timeout
        self.tim = Timer(1)
        self.feed()  # start

    def _reset(self):
        logger.critical("Watchdog timer triggered")
        time.sleep(1)
        machine.reset()

    def feed(self):
        self.tim.init(mode=Timer.ONE_SHOT, period=self.timeout, callback=self._reset)

    def stop(self):
        self.tim.deinit()


def wlan_connect(ssid, pwd):
    ap.active(False)
    wlan.active(False)  # reset wlan
    wlan.active(True)
    logger.info("connecting to network..")
    wlan.connect(ssid, pwd)
    for i in range(60):
        if wlan.isconnected():
            logger.info("connected :D")
            logger.info(f"network config: {wlan.ifconfig()}")
            return
        logger.info(f"waiting.. ({i})")
        time.sleep(1)
    logger.info("failed :(")


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
    logger.info(f"created wifi access point:\n\tSSID: {essid}\n\tPWD: {password}")
    logger.info(f"connect to: 192.168.4.1")


def is_syno_open():
    # todo: use select.poll
    #   https://docs.micropython.org/en/v1.19.1/library/select.html#select.poll
    logger.debug(f"request: GET {URL}")
    r = requests.get(URL)
    if r.status_code != 200:
        raise OSError(9999, f"status code: {r.status_code}")
    isopen = r.content.decode()
    if isopen in ["True", "False"]:
        return eval(isopen)
    raise ValueError(f"got unknown return value from URL: {isopen}")


def toggle_led():
    led.value(led.value() ^ 1)


def ap_and_website(timeout):
    tim0.init(mode=Timer.PERIODIC, period=500, callback=lambda t: toggle_led())
    ap_connect()
    ssid, pwd = serve_website(timeout)
    tim0.deinit()
    led.off()
    return ssid, pwd


def simple_run():
    cause = machine.reset_cause()
    if cause == machine.PWRON_RESET:
        wait_for_connect = 90  # sec
    else:
        wait_for_connect = 30

    try:
        wdt = MyWDT(1000*60*15)  # 10min

        ssid, pwd = ap_and_website(wait_for_connect)
        wdt.feed()
        if ssid:
            fnertlib.store_wifi_config(ssid, pwd)
        ssid, pwd = fnertlib.load_wifi_config()
        wlan_connect(ssid, pwd)

        if not wlan.isconnected():
            raise ConnectionError("could not connect to wifi")

        wdt = MyWDT(1000*60*2)  # 2min

        # for 30min check every second ..
        for _ in range(30 * 60):
            isopen = is_syno_open()
            led.on() if isopen else led.off()
            time.sleep(1)
            wdt.feed()

        wdt = MyWDT(1000*60*5)  # 5min

        # now we get lazy and just check every minute
        while True:
            isopen = is_syno_open()
            led.on() if isopen else led.off()
            time.sleep(60)
            wdt.feed()

    except Exception as e:
        logger.error(repr(e))
        logger.info("goning to deepsleep for 5 min and then restart the program")
        time.sleep(1)
        machine.deepsleep(5 * 60 * 1000)


def strore_credentials_initial(ssid, pwd, url):
    fnertlib.store_wifi_config(ssid, pwd)
    fnertlib.store_str_in_NVS("syno", "url", url)
    fnertlib.store_str_in_NVS("system", "init", "done")


try:
    URL = fnertlib.load_str_from_NVS("syno", "url")
except OSError as e:
    print(f"{repr(e)}. Most likely no initial credentials was provided..")

if __name__ == "__main__":
    cause = machine.reset_cause()
    print(f"last reset was because of {RESET_CAUSES[cause]}({cause})")
    print("enter setup")
    # let's calm down a bit
    machine.freq(80000000)
    time.sleep(1)
    print("lets gooooo... :)")
    simple_run()
