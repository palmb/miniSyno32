
# Getting started

1. install `requirements.txt` with pip 
2. Flash the micro python firmware by following the instructions here: https://docs.micropython.org/en/latest/esp32/tutorial/intro.html
3. use `ampy` to copy `main.py` and `_credentials.py` on the device
   e.g. `ampy --p /dev/ttyUSBn put main.py /main.py`
4. Run via REPL or by simply pressing reset/boot button on the device.


# Errors

### ImportError("Cannot import 'urequests'[...]")

1. connect to device via REPL
2. Ensure you have a working internet connection on the device, you might want to use the defined
   `wlan_connect(ssid, pwd)` function.
    ```pycon
    >>> wlan_connect(...)
    >>> import upip
    >>> upip.install('urequests')
    ```

