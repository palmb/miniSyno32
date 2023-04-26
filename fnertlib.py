#!/usr/bin/env python
import esp32  # noqa


def cat(path):
    with open(path) as f:
        print(f"File {path}\n{'=' * len(path)}")
        for line in f:
            print(line, end="")
        print()


def bytearray_find(buf, b):
    for i, c in enumerate(buf):
        if c == b:
            return i
    return -1


def store_str_in_NVS(ns: str, key: str, value):
    ns = esp32.NVS(ns)
    ns.set_blob(key, value.encode())
    ns.commit()


def load_str_from_NVS(ns, key, max_size=128):
    ns = esp32.NVS(ns)
    buf = bytearray(max_size)
    ns.get_blob(key, buf)
    i = max(bytearray_find(buf, 0), 0)
    value = buf[:i].decode()
    return value


def store_wifi_config(ssid: str, pwd: str):
    ns = esp32.NVS("wifi")
    ns.set_blob("ssid", ssid.encode())
    ns.set_blob("pwd", pwd.encode())
    ns.commit()


def load_wifi_config():
    ssid = load_str_from_NVS('wifi', 'ssid', 512)
    pwd = load_str_from_NVS('wifi', 'pwd', 512)
    return ssid, pwd
