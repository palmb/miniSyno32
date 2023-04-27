import machine
import network
import logging
from machine import Pin, Timer

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
tim1 = Timer(1)
status_led = Pin(2, Pin.OUT)
syno_led = status_led

RESET_CAUSES = {
    machine.PWRON_RESET: "POWERON_RESET",
    machine.HARD_RESET: "HARD_RESET",
    machine.WDT_RESET: "WDT_RESET",
    machine.DEEPSLEEP_RESET: "DEEPSLEEP_RESET",
    machine.SOFT_RESET: "SOFT_RESET",
}


class MyWDT:
    def __init__(self, timeout):
        logger.debug('WDT init')
        self.timeout = timeout
        self.tim = tim1
        self.feed()  # start

    def _reset(self, timer):
        logger.critical("Watchdog timer triggered")
        self.tim.deinit()
        time.sleep(1)
        machine.reset()

    def feed(self):
        logger.debug('WDT feed')
        self.tim.deinit()
        self.tim.init(mode=Timer.ONE_SHOT, period=self.timeout, callback=self._reset)

    def stop(self):
        logger.debug('WDT stope')
        self.tim.deinit()


def wlan_connect(ssid, pwd):
    ap.active(False)
    wlan.active(False)  # reset wlan
    wlan.active(True)
    logger.info("connecting to network..")
    wlan.connect(ssid, pwd)
    for i in range(30):
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
    r.close()
    if isopen in ["True", "False"]:
        return eval(isopen)
    raise ValueError(f"got unknown return value from URL: {isopen}")


def toggle_status_led():
    status_led.value(status_led.value() ^ 1)


def ap_and_website(timeout):
    status_led.on()
    ap_connect()
    ssid, pwd = serve_website(timeout)
    tim0.deinit()
    status_led.off()
    return ssid, pwd


def simple_run():
    try:
        ssid, pwd = fnertlib.load_wifi_config()
        wlan_connect(ssid, pwd)

        if wlan.isconnected():
            # blink twice to signal that wifi is connected
            for _ in range(2):
                status_led.on()
                time.sleep_ms(500)
                status_led.off()
                time.sleep_ms(500)
        else:
            raise OSError(9999, "could not connect to wifi")

        wdt = MyWDT(1000 * 60 * 2)  # 2min

        # for 30min check every second ..
        for _ in range(30 * 60):
            isopen = is_syno_open()
            syno_led.on() if isopen else syno_led.off()
            time.sleep(1)
            wdt.feed()

        logger.info("now we get lazy and just check every minute")
        wdt = MyWDT(1000 * 60 * 5)  # 5min

        while True:
            isopen = is_syno_open()
            status_led.on() if isopen else status_led.off()
            time.sleep(60)
            wdt.feed()

    except Exception as e:
        tim1.deinit()
        logger.error(repr(e))
        logger.info("goning to deepsleep for 5 min and then restart the program")
        time.sleep(1)
        machine.deepsleep(5 * 60 * 1000)


def strore_credentials_initial(ssid, pwd, url):
    fnertlib.store_wifi_config(ssid, pwd)
    fnertlib.store_str_in_NVS("syno", "url", url)
    fnertlib.store_str_in_NVS('system', 'wifisetup', 'nope')


try:
    URL = fnertlib.load_str_from_NVS("syno", "url")
except OSError as e:
    print(f"{repr(e)}. Most likely no initial credentials was provided..")


def wifi_setup():
    # state: nope -> maybe -> enter
    status = fnertlib.load_str_from_NVS("system", "wifisetup")
    logger.info(f"wifi setup status: {status}")
    if status == 'nope':
        fnertlib.store_str_in_NVS('system', 'wifisetup', 'maybe')
    if status == 'maybe':
        fnertlib.store_str_in_NVS('system', 'wifisetup', 'enter')
    if status == 'enter':
        logger.info(f"enter wifi setup")
        fnertlib.store_str_in_NVS('system', 'wifisetup', 'nope')
        ssid, pwd = ap_and_website(None)
        if ssid:
            fnertlib.store_wifi_config(ssid, pwd)
    else:
        tim0.init(mode=Timer.PERIODIC, period=100, callback=lambda t: toggle_status_led())
        time.sleep(3)
        fnertlib.store_str_in_NVS('system', 'wifisetup', 'nope')
        tim0.deinit()
        time.sleep_ms(50)
        status_led.off()


if __name__ == "__main__":
    cause = machine.reset_cause()
    cause_str = RESET_CAUSES.get(cause, "UNKNOWN")
    logger.info(f"last reset was because of {cause_str}({cause})")
    logger.info("start.. ")
    # let's calm down a bit
    status_led.off()
    tim0.deinit()
    tim1.deinit()
    machine.freq(80000000)
    time.sleep(1)
    logger.info("lets gooooo... :)")
    wifi_setup()
    simple_run()
