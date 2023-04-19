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

addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(5)

conn, addr = s.accept(5)
conn.send(http_OK)
conn.sendall(html)
conn.close()
