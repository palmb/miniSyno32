import machine
import logging
from machine import Pin
import esp32  # noqa

from fnertlib import (
    DeepSleepWakePin,
    LedPin,
    deepsleep,
    load_str_from_NVS,
    load_wifi_config,
    wlan_connect,
    wlan,
)
import urequests as requests  # noqa
import time


URL = None
MS_SECOND = 1000
MS_MINUTE = MS_SECOND * 60
MS_HOUR = 60 * MS_MINUTE


# config
STATUS_PNO = 2
WAKE_PNO = 14

# globals
asleep = True
status_led = LedPin(STATUS_PNO, value=0, keep_state_on_sleep=True)
ir_pin = Pin(WAKE_PNO, Pin.IN, Pin.PULL_DOWN, hold=True)


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")  # root


def wake_ISR(pin):
    global asleep
    asleep = False


ir_pin.irq(handler=wake_ISR, trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING)


def change_syno_state(action):
    if action not in ["open", "close"]:
        raise ValueError(f"unknown action {action}")
    url = f"{URL}?action={action}"
    logger.debug(f"request: POST to {url}")
    r = requests.post(url)
    if r.status_code != 200:
        raise ConnectionError(f"POST failed, status code: {r.status_code}")
    r.close()


def simple_run():
    try:
        ssid, pwd = load_wifi_config()
        wlan_connect(ssid, pwd)

        if wlan.isconnected():
            # blink twice to signal that wifi is connected
            status_led.blink(2)

        _simple_run()
    except Exception as err:
        # 5 min blink, 1 min deepsleep, retry
        logger.error(repr(err))
        status_led.blink(1000, maxtime=5 * MS_MINUTE)
    deepsleep(1 * MS_MINUTE)


def _simple_run():
    global asleep

    while True:

        if asleep:
            time.sleep_ms(1)
            continue

        logger.info('WAKE UP')

        if not wlan.isconnected():
            raise ConnectionError("wifi not connected (anymore?)")

        if ir_pin.value() == 1:
            logger.info(f"{ir_pin=} is HIGH")
            change_syno_state(action="open")
            status_led.on()
        else:
            logger.info(f"{ir_pin=} is LOW")
            change_syno_state(action="close")
            status_led.off()

        asleep = True
        logger.info('SLEEP NOW...')


try:
    URL = load_str_from_NVS("syno", "url")
except OSError as e:
    print(f"{repr(e)}. Most likely no initial credentials was provided..")


if __name__ == '__main__':
    logger.info("start.. ")
    # let's calm down a bit
    status_led.off()
    machine.freq(80000000)
    time.sleep(1)

    logger.info("try import store_credentials.py")
    try:
        import store_credentials
    except ImportError:
        logger.info("No new credentials")

    logger.info("lets gooooo... :)")
    # esp32.gpio_deep_sleep_hold(True)
    simple_run()
