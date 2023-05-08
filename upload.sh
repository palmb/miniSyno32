#!/usr/bin/env bash

if [ "$1" = "sender" ]; then
  set -x
  ampy put boot.py /boot.py
  ampy put fnertlib.py /fnertlib.py
  ampy put sender.py /main.py

elif [ "$1" = "receiver" ]; then
  set -x
  ampy put boot.py /boot.py
  ampy put fnertlib.py /fnertlib.py
  ampy put receiver.py /main.py

else
  echo "USAGE: upload.sh {sender|receiver}"
  exit 1
fi

