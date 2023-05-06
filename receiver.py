import machine
import network
import logging
from machine import Pin, Timer

from fnertlib import (
    WakePin,
    LedPin,
    deepsleep,
    store_wifi_config,
    store_str_in_NVS,
    load_str_from_NVS,
    load_str_from_NVS,
    load_wifi_config,
    wlan_connect,
    ap_connect,
    ap,
    wlan,
)
from mini_server import serve_website
import urequests as requests  # noqa
import time

URL = None

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")  # root

tim1 = Timer(1)
STATUS_PNO = 2
status_led = LedPin(STATUS_PNO, value=0, keep_state_on_sleep=True)
syno_led = status_led

second = 1000
minute = second * 60

RESET_CAUSES = {
    machine.PWRON_RESET: "POWERON_RESET",
    machine.HARD_RESET: "HARD_RESET",
    machine.WDT_RESET: "WDT_RESET",
    machine.DEEPSLEEP_RESET: "DEEPSLEEP_RESET",
    machine.SOFT_RESET: "SOFT_RESET",
}


class WatchdogTim1:
    def __init__(self, timeout):
        logger.debug("WDT init")
        self.timeout = timeout
        self.tim = tim1
        self.feed()  # start

    def _reset(self, timer):
        logger.critical("Watchdog timer triggered")
        self.tim.deinit()
        time.sleep(1)
        machine.reset()

    def feed(self):
        logger.debug("WDT feed")
        self.tim.deinit()
        self.tim.init(mode=Timer.ONE_SHOT, period=self.timeout, callback=self._reset)

    def stop(self):
        logger.debug("WDT stope")
        self.tim.deinit()


def is_syno_open():
    # todo: use select.poll
    #   https://docs.micropython.org/en/v1.19.1/library/select.html#select.poll
    logger.debug(f"request: GET {URL}")
    r = requests.get(URL)
    if r.status_code != 200:
        raise OSError(9999, f"status code: {r.status_code}")
    isopen = r.content.decode()
    r.close()
    if isopen in ["True", "False"]:
        return eval(isopen)
    raise ValueError(f"got unknown return value from URL: {isopen}")


def ap_and_website(timeout):
    status_led.on()
    ap_connect()
    ssid, pwd = serve_website(timeout)
    status_led.off()
    return ssid, pwd


def simple_run():
    try:
        ssid, pwd = load_wifi_config()
        wlan_connect(ssid, pwd)

        if wlan.isconnected():
            # blink twice to signal that wifi is connected
            status_led.blink(2)
        else:
            raise OSError(9999, "could not connect to wifi")

        wdt = WatchdogTim1(2 * minute)

        # for 30min check every second ..
        for _ in range(30 * 60):
            isopen = is_syno_open()
            syno_led.on() if isopen else syno_led.off()
            time.sleep(1)
            wdt.feed()

        logger.info("now we get lazy and just check every minute")
        wdt = WatchdogTim1(5 * minute)

        while True:
            isopen = is_syno_open()
            status_led.on() if isopen else status_led.off()
            time.sleep(60)
            wdt.feed()

    except Exception as e:
        tim1.deinit()
        logger.error(repr(e))
        if isinstance(e, OSError) and e.errno == 9999:
            status_led.blink(1000, maxtime=5 * minute)
            machine.reset()
        logger.info("goning to deepsleep for 5 min and then restart the program")
        time.sleep(1)
        machine.deepsleep(5 * 60 * 1000)


try:
    URL = load_str_from_NVS("syno", "url")
except OSError as e:
    print(f"{repr(e)}. Most likely no initial credentials was provided..")


def wifi_setup():
    # state: nope -> maybe -> enter
    status = load_str_from_NVS("system", "wifisetup")
    print(f"WIFI-SETUP: {status=}")
    if status == "nope":
        store_str_in_NVS("system", "wifisetup", "maybe")
    if status == "maybe":
        store_str_in_NVS("system", "wifisetup", "enter")
    if status == "enter":
        logger.info(f"enter wifi setup")
        store_str_in_NVS("system", "wifisetup", "nope")
        ssid, pwd = ap_and_website(None)
        if ssid:
            store_wifi_config(ssid, pwd)
    else:
        status_led.blink(1000, 100, maxtime=3 * second)
        store_str_in_NVS("system", "wifisetup", "nope")
        time.sleep_ms(50)
        status_led.off()


def run():
    logger.info("start.. ")
    # let's calm down a bit
    status_led.off()
    tim1.deinit()
    machine.freq(80000000)
    time.sleep(1)

    logger.info("try import store_credentials.py")
    try:
        import store_credentials
    except ImportError:
        logger.info("No new credentials")

    logger.info("lets gooooo... :)")
    wifi_setup()
    simple_run()
