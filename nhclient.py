#!/usr/bin/env python2

import pygtk
pygtk.require('2.0')
import gobject, gtk
gtk.gdk.threads_init()

import os, re, signal, socket, struct, subprocess, threading, time
from notifier import Notifier

windows = (os.name == 'nt')

class NetherHub(object):
    def __init__(self):
        self.notifier = Notifier()
        self.notifier.notify("App started")
        self._stop = False
        self._portals = {}

        self.lan_listener = threading.Thread(target=self.listen_for_lan_worlds)
        self.lan_listener.start()
    def listen_for_lan_worlds(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 4445))
        mreq = struct.pack("4sl", socket.inet_aton('224.0.2.60'), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.settimeout(10)

        last_seen = {}
        while not(self._stop):
            try:
                lancfg, addr = sock.recvfrom(10240)
                if lancfg.endswith("NetherHub"):
                    continue
                motd, port = re.search(r'\[MOTD\](.*?)\[/MOTD\]\[AD\]([0-9]*?)\[/AD\]', lancfg).groups()
                port = int(port)
                if not((addr[0], port) in last_seen):
                    gobject.idle_add(self.start_portal, motd, addr[0], port)
                last_seen[(addr[0], port)] = time.time()
            except socket.timeout:
                pass
            for (ip, port), timestamp in last_seen.items():
                if timestamp < time.time() - 10:
                    gobject.idle_add(self.stop_portal, ip, port)
                    del(last_seen[(ip, port)])
    def start_portal(self, motd, ip, port):
        self.notifier.notify("Broadcasting %s"%motd)
        self._portals[(ip,port)] = Portal(motd, ip, port)
    def stop_portal(self, ip, port):
        if (ip,port) in self._portals:
            portal = self._portals[(ip,port)]
            self.notifier.notify("Closing %s"%portal.motd)
            portal.close()
            del(self._portals[(ip,port)])

class Portal(object):
    def __init__(self, motd, ip, port):
        self.motd = motd
        self.ip = ip
        self.port = port
        cmd = "lib/portal" if windows else "portal"
        self.popen = subprocess.Popen((cmd, "-s", "brick.miscjunk.net:9000", "-t", "%s:%d"%(ip,port), "-m", motd))
    def close(self):
        self.popen.terminate()
        self.popen.wait()

if __name__ == "__main__":
    nh = NetherHub()
    gtk.main()
