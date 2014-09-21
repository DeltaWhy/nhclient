import pygtk
pygtk.require('2.0')
import gtk

class Notifier(object):
    def __init__(self):
        pass

class Notification(gtk.Window):
    def __init__(self, message):
        gtk.Window.__init__(self, type=gtk.WINDOW_POPUP)
        self.set_opacity(0.75)
        self.set_border_width(0)

        self.label = gtk.Label(message)
        self.box = gtk.HBox()
        self.box.set_border_width(10)
        self.evtbox = gtk.EventBox()
        self.evtbox.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.evtbox.connect("button-press-event", lambda w,e: self.destroy())

        self.add(self.evtbox)
        self.evtbox.add(self.box)
        self.box.add(self.label)

        self.box.show()
        self.evtbox.show()
        self.label.show()
        self.show()

    def close(self):
        print "close handler called"
        self.destroy()

if __name__ == "__main__":
    n = Notification("Hello world")
    gtk.main()
