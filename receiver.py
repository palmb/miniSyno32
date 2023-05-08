import logging
import machine  # noqa

from fnertlib import (
    LedPin,
    deepsleep,
    store_wifi_config,
    store_str_in_NVS,
    load_str_from_NVS,
    load_wifi_config,
    wlan_connect,
    ap_connect,
    wlan,
)
from mini_server import serve_website
import urequests as requests  # noqa
import time

URL = None

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")  # root

tim1 = machine.Timer(1)
STATUS_PNO = 2
status_led = LedPin(STATUS_PNO, value=0, keep_state_on_sleep=True)
syno_led = status_led

second = 1000
minute = second * 60


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
        self.tim.init(mode=machine.Timer.ONE_SHOT, period=self.timeout, callback=self._reset)

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
        for i in range(30 * 60):
            print(f"second {i} since start")
            isopen = is_syno_open()
            syno_led.on() if isopen else syno_led.off()
            time.sleep(1)
            wdt.feed()

        logger.info("now we get lazy and just check every minute")
        wdt = WatchdogTim1(5 * minute)

        i = 30
        while True:
            isopen = is_syno_open()
            status_led.on() if isopen else status_led.off()
            i += 1
            print(f"minute {i} since start")
            time.sleep(60)
            wdt.feed()

    except Exception as e:
        tim1.deinit()  # stop wdt
        logger.error(repr(e))
        if isinstance(e, OSError) and e.errno == 9999:
            status_led.blink(1000, maxtime=5 * minute)
            machine.reset()
        deepsleep(5 * minute)


try:
    URL = load_str_from_NVS("syno", "url")
except OSError as e:
    print(f"{repr(e)}. Most likely no initial credentials was provided..")


def wifi_setup():
    # state: no -> (enter) -> no
    state = load_str_from_NVS("system", "wifisetup")
    print(f"WIFI-SETUP: {state=}")
    if state == "no":
        store_str_in_NVS("system", "wifisetup", "enter")
        # wait 3 secs and blink ... if the user press
        # reset within the 3 secs, we eventually enter
        # the next if-branch, otherwise we start normally
        status_led.blink(1000, 100, maxtime=2 * second)
        store_str_in_NVS("system", "wifisetup", "no")
        time.sleep_ms(50)
        status_led.off()
    elif state == "enter":
        store_str_in_NVS("system", "wifisetup", "no")
        ssid, pwd = ap_and_website(None)
        if ssid:
            store_wifi_config(ssid, pwd)


if __name__ == '__main__':
    logger.info("start.. ")
    logger.info("try import store_credentials.py")
    try:
        import store_credentials
    except ImportError:
        logger.info("No credentials file")

    if machine.reset_cause() == machine.PWRON_RESET:
        wifi_setup()

    # let's calm down a bit
    status_led.off()
    tim1.deinit()
    machine.freq(80000000)
    time.sleep(1)

    logger.info("lets gooooo... :)")
    simple_run()
