#!/usr/bin/env python
from __future__ import annotations
import esp32  # noqa


def cat(path):
    with open(path) as f:
        print(f"File {path}\n{'=' * len(path)}")
        for line in f:
            print(line, end="")
        print()


def store_wifi_config(ssid: str, pwd: str):
    ns = esp32.NVS('wifi')
    ns.set_blob('ssid', ssid.encode())
    ns.set_blob('pwd', pwd.encode())
    ns.commit()


def bytearray_find(buf, b):
    for i, c in enumerate(buf):
        if c == b:
            return i
    return -1


def load_wifi_config():
    ns = esp32.NVS('wifi')

    buf = bytearray(512)
    ns.get_blob('ssid', buf)
    i = max(bytearray_find(buf, 0), 0)
    ssid = buf[:i].decode()

    buf = bytearray(512)
    ns.get_blob('pwd', buf)
    i = max(bytearray_find(buf, 0), 0)
    pwd = buf[:i].decode()

    return ssid, pwd
