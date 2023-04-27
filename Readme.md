# MiniSynoBoard

The board connects to a local WIFI and ask a website if the SYNO is open. 
Iff the SYNO is open, the LED will be on and if the SYNO is closed the LED will be off.

Because the board needs a working internet connection, the board stores the WIFI 
credentials in its internal non-volatile memory. To change these credentials, 
for example if you use a new or other WIFI or your password has changed follow these 
steps:

1. Power up the board and wait for the blue status LED to blink fast (5 times per second)
2. Reset the board during the blinking phase (switch off and on again)
3. Do the same again: in the blinking phase reset the board again.
4. Now the LED should be on permanently, and you successfully entered the WIFI setup. 
5. The board now provide an **own** WIFI, named `miniSyno`.
6. Connect to this WIFI with the password: `make syno great again`
7. Open your favorite browser and enter `192.168.4.1`. Ensure that you only enter the 
   numbers and dots as they are, without any `http` or `www` upfront.
8. You should now see a minimal website, where you can enter the new WIFI credentials 
   for **your** WIFI.
9. As soon you hit the `Submit` button, the board will tear down the miniSyno-WIFI and
   try to connect to your WIFI.
10. Wait up to 30 seconds and observe the blue status LED. If the board can connect to
    your WIFI, the LED should blink **twice** slowly (on for half a sec and off for 
    half a sec). Otherwise, start again with step 1.

> **Hint:** While the `miniSyno` WIFI is active the blue LED of the board is on all the time


# Development

1. install `requirements.txt` with pip 
2. Flash the micro python firmware by following the instructions here: https://docs.micropython.org/en/latest/esp32/tutorial/intro.html
3. find the port the board is connected to. e.g. with `sudo dmesg | grep tty`
4. adjust the port the board is connected to in `.ampy`.
5. use `upload.sh` to copy all python files in the directory to the board. 
   Alternatively use `ampy` to do so. e.g. `ampy --p /dev/ttyUSBn put main.py /main.py`
6. Run via REPL or by simply pressing reset/boot button on the device.

