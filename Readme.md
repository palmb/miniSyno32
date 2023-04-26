# MiniSynoBoard

The board connects to a local WIFI and ask a website if the SYNO is open. 
Iff the SYNO is open, the LED will be on and if the SYNO is closed the LED will be off.

Because the board needs a working internet connection, the board stores the WIFI 
credentials in its internal non-volatile memory. To change these credentials, 
for example if you use a new or other WIFI or your password has changed follow these 
steps:

1. Every time the board powers up, it creates its ***own* temporary Wifi for 90 
   seconds**. It is named `miniSyno`.
2. Connect to it with the following password: `make syno great again`
3. Open your favorite browser and enter `192.168.4.1`. 
   Ensure that you only enter the numbers and dots as they are, without any `http` or 
   `www` upfront.
4. You should see now a minimal website. Once you see this website you have 10 minutes 
   to enter the new WIFI credentials for **your** WIFI.
5. If you were too slow to connect simply power it up again - did you try turning it off and on again ;)

> **Hint:** While the `miniSyno` WIFI is active the blue LED of the board flashes
> twice a second.


# Development

1. install `requirements.txt` with pip 
2. Flash the micro python firmware by following the instructions here: https://docs.micropython.org/en/latest/esp32/tutorial/intro.html
3. find the port the board is connected to. e.g. with `sudo dmesg | grep tty`
4. adjust the port the board is connected to in `.ampy`.
5. use `upload.sh` to copy all python files in the directory to the board. 
   Alternatively use `ampy` to do so. e.g. `ampy --p /dev/ttyUSBn put main.py /main.py`
6. Run via REPL or by simply pressing reset/boot button on the device.


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

