import machine
import network
import logging
from machine import Pin, Timer
import esp32  # noqa

import fnertlib
import urequests as requests  # noqa
import time

URL = None

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")  # root
wlan = network.WLAN(network.STA_IF)
STATUS_PNO = 2
WAKE_PNO = 14
status_led = Pin(STATUS_PNO, Pin.OUT)
wake_pin = Pin(WAKE_PNO, Pin.IN, Pin.PULL_DOWN, hold=True)


def status_led_hold(on=True):
    Pin(STATUS_PNO, Pin.OUT, hold=on)


def status_led_commit():
    status_led_hold(True)


def wake_on_rise():
    esp32.wake_on_ext0(pin=wake_pin, level=esp32.WAKEUP_ANY_HIGH)


def wake_on_fall():
    esp32.wake_on_ext0(pin=wake_pin, level=esp32.WAKEUP_ALL_LOW)


ms_second = 1000
ms_minute = ms_second * 60
ms_hour = 60 * ms_minute

RESET_CAUSES = {
    machine.PWRON_RESET: "POWERON_RESET",
    machine.HARD_RESET: "HARD_RESET",
    machine.WDT_RESET: "WDT_RESET",
    machine.DEEPSLEEP_RESET: "DEEPSLEEP_RESET",
    machine.SOFT_RESET: "SOFT_RESET",
}


def wlan_connect(ssid, pwd):
    # DO NOT USE LOGGING HERE
    wlan.active(False)  # reset wlan
    wlan.active(True)
    print("connecting to network..")
    wlan.connect(ssid, pwd)
    for i in range(30):
        if wlan.isconnected():
            print("connected :D")
            print(f"network config: {wlan.ifconfig()}")
            return
        print(f"waiting.. ({i})")
        time.sleep(1)
    print("failed :(")


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


def toggle_status_led():
    status_led.value(status_led.value() ^ 1)


def bink_status_led(
    blinks: int, period: int = 1000, dutycycle: float = 0.5, maxtime: int = None
):
    """
    Blink the status LED.
    `n` is ignored if `maxtime` is given.
    """
    high = int(period * dutycycle)
    low = int(period * (1 - dutycycle))
    if maxtime is not None:
        blinks = maxtime // period
    for _ in range(blinks):
        status_led.on()
        time.sleep_ms(high)
        status_led.off()
        time.sleep_ms(low)


def simple_run():
    is_on = wake_pin.value() == 1

    try:
        ssid, pwd = fnertlib.load_wifi_config()
        wlan_connect(ssid, pwd)

        if wlan.isconnected():
            # blink twice to signal that wifi is connected
            bink_status_led(2)
        else:
            raise OSError(9999, "could not connect to wifi")

        status_led_hold(True)

        if is_on:
            logger.info(f"{wake_pin=} is HIGH")
            change_syno_state(action="open")
            status_led.on()
        else:
            logger.info(f"{wake_pin=} is LOW")
            change_syno_state(action="close")
            status_led.off()

        status_led_commit()

    except Exception as e:
        logger.error(repr(e))
        if isinstance(e, OSError) and e.errno == 9999:
            # 5 min blink, 10 min deepsleep, retry
            bink_status_led(1000, maxtime=5 * ms_minute)
        # exits here
        deepsleep(10 * ms_minute)

    if is_on:
        wake_on_fall()
        logger.info(f"waiting for {wake_pin} to become LOW")
    else:
        wake_on_rise()
        logger.info(f"waiting for {wake_pin} to become HIGH")

    # exits here
    deepsleep(1 * ms_hour)


try:
    URL = fnertlib.load_str_from_NVS("syno", "url")
except OSError as e:
    print(f"{repr(e)}. Most likely no initial credentials was provided..")


def test():
    is_on = wake_pin.value() == 1

    if is_on:
        wake_on_fall()
        logger.info(f"waiting for {wake_pin} to become LOW")
    else:
        wake_on_rise()
        logger.info(f"waiting for {wake_pin} to become HIGH")

    deepsleep(1 * ms_hour)


def deepsleep(ms: int):
    print("Going to deepsleep", end="")
    if ms > 5000:
        ms -= 5000
        for i in range(5):
            time.sleep(1)
            print(".", end="")
    print()
    machine.deepsleep(ms)


if __name__ == "__main__":
    cause = machine.reset_cause()
    cause_str = RESET_CAUSES.get(cause, "UNKNOWN")
    logger.info(f"last reset was because of {cause_str}({cause})")
    logger.info("start.. ")
    # let's calm down a bit
    status_led_hold(False)
    status_led.off()
    machine.freq(80000000)
    time.sleep(1)

    logger.info("try import store_credentials.py")
    try:
        import store_credentials
    except ImportError:
        logger.info("No new credentials")

    logger.info("lets gooooo... :)")
    simple_run()
