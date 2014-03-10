import socket
import base64
import time

from PyQt4.QtCore import *

class ConsoleConnection(QThread):
    def __init__(self):
        super(ConsoleConnection, self).__init__()

        self.setTerminationEnabled(True)

        self.sock = None
        self._is_connected = False

        self.connect(self, SIGNAL("terminated()"), self.onTerminate)

        self.data = ""

    def setConnection(self, host_ip, host_port, host_user, host_pass, vm_uuid):
        self.host_ip = host_ip
        self.host_port = host_port
        self.host_user = host_user
        self.host_pass = host_pass
        self.vm_uuid = vm_uuid

    def base64_auth(self):
        return base64.b64encode("{0}:{1}".format(self.host_user,
                                                 self.host_pass))

    def onTerminate(self):
        self.sock.close()

    def run(self):
        print("Connecting to VT100 to {0}".format(self.host_ip))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host_ip, self.host_port))
        self.sock.send('CONNECT /console?uuid={0} HTTP/1.1\r\n'.format(self.vm_uuid))
        self.sock.send('Authorization: Basic {0}\r\n'.format(self.base64_auth()))
        self.sock.send('Host: {0}\r\n'.format(self.host_ip))
        self.sock.send('\r\n\r\n')

        while True:
            data = self.sock.recv(32768)

            if not data:
                self.sock.close()
                return

            self.emit(SIGNAL("dataReceived"), data)

            # make buffer for connection data
            self.data = "%s%s" % (self.data, data)
            self.data = self.data[:32768]

    def send(self, data):
        self.sock.send(data)
