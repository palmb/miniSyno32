import machine
import errno
import network
import sys
import logging
from machine import lightsleep, Pin, Timer
import urequests as requests
import time
import webrepl
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


# Ensure that this function is available, even on errors, because
# it makes live a lot easier ;)
def wlan_connect(ssid, pwd):
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
            return
    info(f"network config: {wlan.ifconfig()}")


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


def setup():
    # let's calm down a bit
    machine.freq(80000000)
    time.sleep(1)
    wlan_connect(SSID, WIFI_PWD)


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


def start_webrepl_timed(sec: int):
    tim0.init(mode=Timer.ONE_SHOT, period=sec * 1000, callback=lambda t: webrepl.stop())
    try:
        webrepl.start_foreground()
    except OSError as e:
        if e.errno == errno.EBADF:
            pass
        else:
            raise


def loop():
    isopen = False

    while wlan.isconnected():
        wasopen = isopen
        isopen = is_syno_open()
        if isopen != wasopen:
            info(f"syno is open: {isopen}")
            LED.on() if isopen else LED.off()
        time.sleep_ms(1000)

    ap_connect()
    start_webrepl_timed(20)


data = dict(action="close")

import socket

html = """<!DOCTYPE html>
<html>
    <head> <title>MiniSyno Wifi Settings</title> </head>
    <form action="/wifi" method="GET">
      <label for="ssid">SSID:</label>
      <input type="text" id="ssid" name="ssid"><br><br>
      <label for="pwd">Passwort:</label>
      <input type="text" id="pwd" name="pwd"><br><br>
      <input type="submit" value="Submit">
    </form>
    </body>
</html>
"""

http_OK = "HTTP/1.0 200 OK\nContent-type: text/html\n\n"
request = None


def url_decode(url):
    result = ""
    i = 0
    while i < len(url):
        if url[i] == "%":
            result += chr(int(url[i + 1 : i + 3], 16))
            i += 3
        else:
            if url[i] == "+":
                c = " "
            else:
                c = url[i]
            result += c
            i += 1
    return result


def cat(path):
    with open(path) as f:
        for l in f:
            print(l, end="")


def serve_website():
    # https://randomnerdtutorials.com/esp32-esp8266-micropython-web-server/
    global request
    import gc
    gc.collect()  # ensure old sockets to be closed
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.close()
    s.bind(("0.0.0.0", 80))
    s.listen(1)
    ssid, pwd = "", ""
    while ssid is "":
        conn, addr = s.accept()
        info(f"New connection from {addr}")
        request = str(conn.recv(1024))
        debug(f"{request=}")
        i0 = request.find("?ssid=") + 6
        i1 = request[i0:].find("&pwd=") + i0
        i2 = request[i1:].find(" ") + i1
        ssid = url_decode(request[i0:i1])
        pwd = url_decode(request[i1 + 5 : i2])
        info(f"new wifi config: {ssid=}, {pwd=}")
        conn.send(http_OK)
        conn.sendall(html)
        conn.close()


def test():
    webrepl.stop()
    ap_connect()
    serve_website()


if __name__ == "__main__":
    test()
    # print("enter setup")
    # setup()
    # print("enter loop")
    # loop()
