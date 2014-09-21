#!/usr/bin/env python2

import pygtk
pygtk.require('2.0')
import gobject, gtk
gtk.gdk.threads_init()

import json, os, random, re, signal, socket, struct, subprocess, sys, threading, time
import redis
from notifier import Notifier

windows = (os.name == 'nt')

class NetherHub(object):
    def __init__(self, user):
        self.user = user
        self.notifier = Notifier()
        self._stop = False
        self._portals = {}
        self._broadcasters = {}

        self.lan_listener = threading.Thread(target=self.listen_for_lan_worlds)
        self.lan_listener.daemon = True
        self.lan_listener.start()

        self.redis_listener = threading.Thread(target=self.subscribe_games)
        self.redis_listener.daemon = True
        self.redis_listener.start()
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
                if not(lancfg.endswith("NetherHub")):
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
    def subscribe_games(self):
        r = redis.StrictRedis(host='gravel.miscjunk.net')
        for k in r.keys("netherhub:game:*"):
            j = json.loads(r.get(k))
            if j['user'] == self.user:
                continue
            gobject.idle_add(self.start_broadcast, j['motd'], '104.131.240.223', int(k.split(':')[-1]))
        pubsub = r.pubsub()
        pubsub.subscribe(('netherhub:game_opens','netherhub:game_closes'))
        for item in pubsub.listen():
            if item['type'] != 'message':
                continue
            if item['channel'] == 'netherhub:game_opens':
                j = json.loads(r.get(item['data']))
                if j['user'] == self.user:
                    continue
                motd = j['motd']
                ip = '104.131.240.223'
                port = int(j['addr'].split(':')[-1])
                gobject.idle_add(self.start_broadcast, motd, ip, port)
            elif item['channel'] == 'netherhub:game_closes':
                ip = '104.131.240.223'
                port = int(item['data'].split(':')[-1])
                gobject.idle_add(self.stop_broadcast, ip, port)
    def start_portal(self, motd, ip, port):
        self.notifier.notify("Broadcasting %s"%motd)
        self._portals[(ip,port)] = Portal(self.user, motd, ip, port)
    def stop_portal(self, ip, port):
        if (ip,port) in self._portals:
            portal = self._portals[(ip,port)]
            self.notifier.notify("Closing %s"%portal.motd)
            portal.close()
            del(self._portals[(ip,port)])
    def start_broadcast(self, motd, ip, port):
        self.notifier.notify("Found %s"%motd)
        self._broadcasters[(ip,port)] = Broadcaster(motd, ip, port)
    def stop_broadcast(self, ip, port):
        if (ip,port) in self._broadcasters:
            b = self._broadcasters[(ip,port)]
            self.notifier.notify("%s closed"%b.motd)
            b.close()
            del(self._broadcasters[(ip,port)])
    def close(self):
        self._stop = True
        for portal in self._portals.values():
            portal.close()
        for b in self._broadcasters.values():
            b.close()

class Portal(object):
    def __init__(self, user, motd, ip, port):
        self.user = user
        self.motd = motd
        self.ip = ip
        self.port = port
        cmd = "lib/portal" if windows else "portal"
        self.popen = subprocess.Popen((cmd, "-s", "portal.netherhubmc.com:9000", "-t", "%s:%d"%(ip,port), "-m", motd, "-a", self.user))
    def close(self):
        print "closing Portal %s:%d"%(self.ip,self.port)
        self.popen.terminate()
        self.popen.wait()
        print "closed Portal %s:%d"%(self.ip,self.port)

class Broadcaster(object):
    def __init__(self, motd, ip, port):
        self.motd = motd
        self.ip = ip
        self.port = port
        self.popen = None
        self._stop = False
        self._thread = threading.Thread(target=self.broadcast)
        self._thread.start()
    def broadcast(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        lport = self._find_open_port()
        cmd = "lib/ncat" if windows else "ncat"
        self.popen = subprocess.Popen((cmd, '-k', '-l', '-p %d'%lport, '--sh-exec', '%s %s %d'%(cmd, self.ip,self.port)))
        while not(self._stop):
            sock.sendto("[MOTD]%s[/MOTD][AD]%d[/AD]NetherHub"%(self.motd,lport), ('224.0.2.60', 4445))
            time.sleep(3)
    def close(self):
        self._stop = True
        print "closing Broadcaster %s:%d"%(self.ip,self.port)
        self.popen.terminate()
        self.popen.wait()
        print "closed Broadcaster %s:%d"%(self.ip,self.port)
    def _find_open_port(self):
        port = random.randrange(1024, 65535)
        while subprocess.call(['ncat', '-w 1', 'localhost', str(port)]) == 0:
            port = random.randrange(1024, 65535)
        return port

if __name__ == "__main__":
    nh = NetherHub(sys.argv[1])
    signal.signal(signal.SIGINT, gtk.main_quit)
    gtk.main()
    nh.close()
    print "exited gtk.main"
