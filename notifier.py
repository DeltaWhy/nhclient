import pygtk
pygtk.require('2.0')
import gobject, gtk, pango

class Notifier(object):
    def __init__(self):
        self.queue = []
    def notify(self, message):
        n = Notification(message)
        if len(self.queue) > 0:
            x1, y1 = n.get_position()
            w1, h1 = n.get_size()
            last = self.queue[-1]
            x2, y2 = last.get_position()
            w2, h2 = last.get_size()
            n.move(x1, y2+h2+10)
        self.queue.append(n)
        n.connect("hide", self.remove)
        n.timeout = gobject.timeout_add(5000, self.pop)
        return False
    def pop(self):
        n = self.queue.pop(0)
        n.destroy()
        return False # otherwise the timeout repeats
    def remove(self, n, event=None):
        if hasattr(n, 'timeout'):
            gobject.source_remove(n.timeout)
        if n in self.queue:
            self.queue.remove(n)

class Notification(gtk.Window):
    def __init__(self, message):
        gtk.Window.__init__(self, type=gtk.WINDOW_POPUP)
        self.set_opacity(0.75)
        self.set_border_width(0)
        self.set_gravity(gtk.gdk.GRAVITY_NORTH_EAST)
        font = pango.FontDescription()
        font.set_weight(500) # a little bolder than normal
        font.set_size(12*pango.SCALE)

        self.label = gtk.Label(message)
        self.label.set_property("wrap", True)
        self.label.modify_font(font)
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#222"))
        self.label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.Color("white"))
        self.box = gtk.HBox()
        self.box.set_border_width(10)
        self.evtbox = gtk.EventBox()
        self.evtbox.set_property("visible-window", False)
        self.evtbox.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.evtbox.connect("button-press-event", lambda w,e: self.hide())

        self.add(self.evtbox)
        self.evtbox.add(self.box)
        self.box.add(self.label)

        self.box.show()
        self.evtbox.show()
        self.label.show()
        w, h = self.get_size()
        self.move(gtk.gdk.screen_width()-w-10, 10)
        self.show()

    def close(self):
        print "close handler called"
        self.destroy()

if __name__ == "__main__":
    n = Notifier()
    n.notify("Hello world")
    gobject.timeout_add(1500, n.notify, "This is a longer message")
    gtk.main()
