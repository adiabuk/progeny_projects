#
# splashscreen.py: a quick splashscreen window that displays during ipl
#
# Matt Wilson <msw@redhat.com>
#
# Copyright 2001-2002 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import os
os.environ["PYGTK_DISABLE_THREADS"] = "1"
os.environ["GNOME_DISABLE_CRASH_DIALOG"] = "1"

import gtk
from flags import flags
from rhpl.translate import cat

# for GTK+ 2.0
cat.setunicode(1)

splashwindow = None

def splashScreenShow(configFileData):
    #set the background to a dark gray
    if flags.setupFilesystems:
        path = ("/usr/X11R6/bin/xsetroot",)
        args = ("-solid", "gray45")

        child = os.fork()
        if (child == 0):
            os.execv(path[0], path + args)
        try:
            pid, status = os.waitpid(child, 0)
        except OSError, (errno, msg):
            print __name__, "waitpid:", msg

    root = gtk.gdk.get_default_root_window()
    cursor = gtk.gdk.Cursor(gtk.gdk.LEFT_PTR)
    root.set_cursor(cursor)

    def load_image(file):
        # FIXME: this should use findPixmap() in gui.py
        fn = None
        for path in ("/mnt/source/RHupdates/pixmaps/",
                     "/mnt/source/RHupdates/",
                     "/tmp/updates/pixmaps/", "/tmp/updates/",
                     "/tmp/product/pixmaps/", "/tmp/product/",
                     "/usr/share/anaconda/pixmaps/", "pixmaps/",
                     "/usr/share/pixmaps/",
                     "/usr/share/anaconda/", ""):
            if os.access(path + file, os.R_OK):
                fn = path + file
                break

        p = gtk.Image()
        if fn is None:
            return p
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(fn)
        except RuntimeError:
            pixbuf = None
        if pixbuf:
            (pixmap, mask) = pixbuf.render_pixmap_and_mask()
            pixbuf.render_to_drawable(pixmap, gtk.gdk.GC(pixmap),
                                      0, 0, 0, 0,
                                      pixbuf.get_width(), pixbuf.get_height(),
                                      gtk.gdk.RGB_DITHER_MAX, 0, 0)
            
            p.set_from_pixmap(pixmap, mask)
        return p

    global splashwindow
    
    width = gtk.gdk.screen_width()
    p = None

    # If the xserver is running at 800x600 res or higher, use the
    # 800x600 splash screen.
    if width >= 800:
        p = load_image("pixmaps/first.png")
    else:
        p = load_image('pixmaps/first-lowres.png')
                        
    if p:
        splashwindow = gtk.Window()
        splashwindow.set_position(gtk.WIN_POS_CENTER)
        box = gtk.EventBox()
        box.modify_bg(gtk.STATE_NORMAL, box.get_style().white)
        box.add(p)
        splashwindow.add(box)
        box.show_all()
        splashwindow.show_now()
        gtk.gdk.flush()
        while gtk.events_pending():
            gtk.main_iteration(gtk.FALSE)

def splashScreenPop():
    global splashwindow
    if splashwindow:
        splashwindow.destroy()
