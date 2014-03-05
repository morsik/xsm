from PyQt4 import QtCore

import xenapi
import socket
try:
    import Queue as queue
except ImportError:
    import queue


class XapiConnection(QtCore.QThread):
    def __init__(self, host, user, password):
        super(XapiConnection, self).__init__()

        self.q = queue.Queue()
        self.timeout = 1.0 / 60

        self.xapi = None
        self.session = None

        self.host = host
        self.user = user
        self.password = password

        self.data = {
            'pool': {},
            'host': {},
            'vm': {},
            'task': {},
            'pbd': {},
            'sr': {},
            'console': {}
        }

    def connectXenApi(self):
        self.is_connected = False

        print("Connecting to {0}...".format(self.host))

        self.session = xenapi.Session('https://' + self.host)
        try:
            self.session.login_with_password(self.user, self.password)
        except xenapi.Failure as e:
            if e.details[0] == 'HOST_IS_SLAVE':
                self.host = e.details[1]
                print("Host is slave. Connecting to master at {0}...".format(self.host))
                self.session = xenapi.Session('https://' + self.host)
                self.session.login_with_password(self.user, self.password)
            else:
                raise
        except socket.error as e:
            self.emit(QtCore.SIGNAL("connectionError"), self.host, e)
            return None

        self.is_connected = True

        # populate all information right after connected
        self.data['pool'] = self.session.xenapi.pool.get_all_records()
        self.data['host'] = self.session.xenapi.host.get_all_records()
        self.data['vm'] = self.session.xenapi.VM.get_all_records()
        self.data['task'] = self.session.xenapi.task.get_all_records()
        self.data['pbd'] = self.session.xenapi.PBD.get_all_records()
        self.data['sr'] = self.session.xenapi.SR.get_all_records()
        self.data['console'] = self.session.xenapi.console.get_all_records()

        # this is strange... but i couldn't find any other way to get pool ref
        pool_i = 1
        for ref, pool in self.data['pool'].items():
            if pool_i > 1:
                raise Exception("There should be only 1 pool! Something strange happened.")

            self.pool_ref = ref
            pool_i += 1

        print("Connected to pool '{0}' at {1}.".format(self.data['pool'][self.pool_ref]['name_label'], self.host))

    def __del__(self):
        self.wait()

    def onThread(self, callback, function, *args, **kwargs):
        self.q.put((callback, function, args, kwargs))

    def processEvent(self, event):
        name = "(unknown)"
        if "snapshot" in event.keys():
            snapshot = event["snapshot"]
            if "name_label" in snapshot.keys():
                name = snapshot["name_label"]
        prg = ""
        if event['class'] == 'task':
            prg = "%.1f%%" % (event['snapshot']['progress'] * 100)

        #print("%12s %8s  %12s  %5s  %6s  %s" % (self.data['pool'][self.pool_ref]['name_label'], event['id'], event['class'], event['operation'], prg, name))

        if event['operation'] == 'add':
            self.emit(QtCore.SIGNAL("%sAdded" % event['class']), self.pool_ref, event['ref'], event['snapshot'])
        elif event['operation'] == 'mod':
            self.emit(QtCore.SIGNAL("%sModified" % event['class']), self.pool_ref, event['ref'], event['snapshot'])
        elif event['operation'] == 'del':
            self.emit(QtCore.SIGNAL("%sDeleted" % event['class']), self.pool_ref, event['ref'], event['snapshot'])
        else:
            raise Exception("Unknown XenAPI event operation: %s" % event['operation'])

    def run(self):
        try:
            self.connectXenApi()

            s = self.session

            if self.is_connected:
                self.emit(QtCore.SIGNAL("connectionSuccessful"), self.pool_ref, self)

            s.xenapi.event.register(["*"])
            while True:
                try:
                    callback, function, args, kwargs = self.q.get(timeout=self.timeout)
                    self.emit(QtCore.SIGNAL("asyncCallback"), callback, self.pool_ref, function(*args, **kwargs))
                except queue.Empty:
                    try:
                        for event in s.xenapi.event.next():
                            self.processEvent(event)
                    except xenapi.Failure as e:
                        if e.details == ["EVENTS_LOST"]:
                            print("Caught EVENTS_LOST; should reregister")
        except socket.error as e:
            self.is_connected = False
            self.emit(QtCore.SIGNAL("connectionError"), e)

        self.terminate()
