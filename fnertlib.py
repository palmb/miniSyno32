#!/usr/bin/env python
from __future__ import annotations


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
        print(f"File {path}\n{'=' * len(path)}")
        for line in f:
            print(line, end="")
        print()

