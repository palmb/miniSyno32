import machine
import network
import logging
from machine import Pin, Timer

import fnertlib
import urequests as requests  # noqa
import time

URL = None

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")  # root
wlan = network.WLAN(network.STA_IF)
status_led = Pin(2, Pin.OUT)
pin = Pin(5, Pin.IN)

second = 1000
minute = second * 60

RESET_CAUSES = {
    machine.PWRON_RESET: "POWERON_RESET",
    machine.HARD_RESET: "HARD_RESET",
    machine.WDT_RESET: "WDT_RESET",
    machine.DEEPSLEEP_RESET: "DEEPSLEEP_RESET",
    machine.SOFT_RESET: "SOFT_RESET",
}


def wlan_connect(ssid, pwd):
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


def change_syno_state(action):
    if action not in ['open', 'close']:
        raise ValueError(f'unknown action {action}')
    url = f"{URL}?action={action}"
    logger.debug(f"request: POST to {url}")
    r = requests.post(url)
    if r.status_code != 200:
        raise OSError(9999, f"status code: {r.status_code}")
    r.close()
    return


def toggle_status_led():
    status_led.value(status_led.value() ^ 1)


def bink_status_led(n, period=1000, dutycycle=0.5, maxtime=None):
    high = int(period * dutycycle)
    low = int(period * (1 - dutycycle))
    if maxtime is not None:
        n = maxtime // period
    for _ in range(n):
        status_led.on()
        time.sleep_ms(high)
        status_led.off()
        time.sleep_ms(low)


def simple_run():
    try:
        ssid, pwd = fnertlib.load_wifi_config()
        wlan_connect(ssid, pwd)

        if wlan.isconnected():
            # blink twice to signal that wifi is connected
            bink_status_led(2)
        else:
            raise OSError(9999, "could not connect to wifi")

        if pin.value():
            print("pin is high")
            change_syno_state(action='open')
        else:
            print("pin is low")
            change_syno_state(action='close')

    except Exception as e:
        logger.error(repr(e))
        if isinstance(e, OSError) and e.errno == 9999:
            bink_status_led(1000, maxtime=5*minute)
            machine.reset()
        logger.info("goning to deepsleep for 5 min and then restart the program")
        time.sleep(1)
        # todo: IRQ on pin high/low change
        machine.deepsleep(5 * minute)


def strore_credentials_initial(ssid, pwd, url):
    fnertlib.store_wifi_config(ssid, pwd)
    fnertlib.store_str_in_NVS("syno", "url", url)


try:
    URL = fnertlib.load_str_from_NVS("syno", "url")
except OSError as e:
    print(f"{repr(e)}. Most likely no initial credentials was provided..")


if __name__ == "__main__":
    cause = machine.reset_cause()
    cause_str = RESET_CAUSES.get(cause, "UNKNOWN")
    logger.info(f"last reset was because of {cause_str}({cause})")
    logger.info("start.. ")
    # let's calm down a bit
    status_led.off()
    machine.freq(80000000)
    time.sleep(1)
    logger.info("lets gooooo... :)")
    simple_run()
