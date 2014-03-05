from xapiconnection import XapiConnection


class XapiConnectionManager():
    def __init__(self):
        self.connections = []

    def newConnection(self, host, user, password):
        c = XapiConnection(host, user, password)
        c.start()
        self.connections.append(c)

    def getConnectionByPoolRef(self, ref):
        for connection in self.connections:
            if ref == connection.pool_ref:
                return connection

        return None
