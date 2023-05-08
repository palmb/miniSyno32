import machine
import logging
from machine import Pin
import esp32  # noqa

from fnertlib import (
    WakePin,
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

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")  # root
# config
STATUS_PNO = 2
WAKE_PNO = 14

# globals
wake_pin = WakePin(WAKE_PNO, Pin.PULL_DOWN)
status_led = LedPin(STATUS_PNO, value=0, keep_state_on_sleep=True)


ms_second = 1000
ms_minute = ms_second * 60
ms_hour = 60 * ms_minute


def change_syno_state(action):
    if action not in ["open", "close"]:
        raise ValueError(f"unknown action {action}")
    url = f"{URL}?action={action}"
    logger.debug(f"request: POST to {url}")
    r = requests.post(url)
    if r.status_code != 200:
        raise OSError(9999, f"status code: {r.status_code}")
    r.close()
    return


def simple_run():
    is_high = wake_pin.value() == 1

    try:
        ssid, pwd = load_wifi_config()
        wlan_connect(ssid, pwd)

        if wlan.isconnected():
            # blink twice to signal that wifi is connected
            status_led.blink(2)
        else:
            raise OSError(9999, "could not connect to wifi")

        if is_high:
            logger.info(f"{wake_pin=} is HIGH")
            change_syno_state(action="open")
            status_led.on()
        else:
            logger.info(f"{wake_pin=} is LOW")
            change_syno_state(action="close")
            status_led.off()

        # temp fast
        while wlan.isconnected():
            was_high = is_high
            is_high = wake_pin.value() == 1
            if was_high != is_high:
                if is_high:
                    logger.info(f"{wake_pin=} is HIGH")
                    change_syno_state(action="open")
                    status_led.on()
                else:
                    logger.info(f"{wake_pin=} is LOW")
                    change_syno_state(action="close")
                    status_led.off()
            time.sleep(1)

    except Exception as e:
        logger.error(repr(e))
        if isinstance(e, OSError) and e.errno == 9999:
            # 5 min blink, 10 min deepsleep, retry
            status_led.blink(1000, maxtime=5 * ms_minute)
        # exits here
        deepsleep(10 * ms_minute)

    if is_high:
        wake_pin.wake_on(level="low")
    else:
        wake_pin.wake_on(level="high")

    # exits here
    if is_high + wake_pin.value() == 1:
        t = 1
    else:
        t = 1 * ms_hour
    deepsleep(t)


try:
    URL = load_str_from_NVS("syno", "url")
except OSError as e:
    print(f"{repr(e)}. Most likely no initial credentials was provided..")


def test():
    is_on = wake_pin.value() == 1

    if is_on:
        wake_pin.wake_on(level='low')
        logger.info(f"waiting for {wake_pin} to become LOW")
    else:
        wake_pin.wake_on(level='high')
        logger.info(f"waiting for {wake_pin} to become HIGH")

    deepsleep(1 * ms_hour)


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
