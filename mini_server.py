import socket
import logging

logger = logging.getLogger("MicroServer")

# https://randomnerdtutorials.com/esp32-esp8266-micropython-web-server/


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


HTML = """<!DOCTYPE html>
<html>
    <head> <title>MiniSyno Wifi Settings</title> </head>
    <form action="/wifi" method="GET">
      <label for="ssid">SSID:</label>
      <input type="text" id="ssid" name="ssid"><br><br>
      <label for="pwd">PWD: </label>
      <input type="text" id="pwd" name="pwd"><br><br>
      <input type="submit" value="Submit">
    </form>
    </body>
</html>
"""

HTTP_OK = "HTTP/1.0 200 OK\nContent-type: text/html\n\n"


# https://randomnerdtutorials.com/esp32-esp8266-micropython-web-server/
def serve_website():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", 80))
        sock.listen(1)
        ssid, pwd = "", ""
        while ssid is "":
            conn, addr = sock.accept()
            logger.info(f"New connection from {addr}")
            request = str(conn.recv(1024))
            logger.debug(f"{request=}")
            i0 = request.find("?ssid=") + 6
            i1 = request[i0:].find("&pwd=") + i0
            i2 = request[i1:].find(" ") + i1
            ssid = url_decode(request[i0:i1])
            pwd = url_decode(request[i1 + 5 : i2])
            logger.info(f"new wifi config: {ssid=}, {pwd=}")
            conn.send(HTTP_OK)
            conn.sendall(HTML)
            conn.close()
    finally:
        sock.close()
    return ssid, pwd
