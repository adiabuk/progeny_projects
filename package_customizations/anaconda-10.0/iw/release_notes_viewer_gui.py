#!/usr/bin/python
#
# release_notes_viewer_iw.py - viewer for release notes
#
# Michael Fulbright <msf@redhat.com>
#
# Copyright 2003 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import sys
import os
import gtk

from rhpl.translate import _, N_

sys.path.append('/usr/lib/anaconda')

from gui import TextViewBrowser, addFrame
import htmlbuffer

screenshot = None

def loadReleaseNotes(fn):
    if os.access(fn, os.R_OK):
	file = open(fn, "r")
	if fn.endswith('.html'):
	    buffer = htmlbuffer.HTMLBuffer()
	    buffer.feed(file.read())
	    return buffer.get_buffer()
	else:
	    buffer = gtk.TextBuffer(None)
	    buffer.set_text(file.read())
	file.close()
	return buffer

    buffer = gtk.TextBuffer(None)
    buffer.set_text(_("Release notes are missing.\n"))

    return buffer

def relnotes_closed(widget, data):
    sys.exit(0)


def exposeCB(widget, event, data):
    global screenshot
    
    width = gtk.gdk.screen_width()
    height = gtk.gdk.screen_height()
    gc = gtk.gdk.GC(widget.window)
    screenshot.render_to_drawable(widget.window,
				  gc,
				  0, 0,
				  0, 0,
				  width, height,
				  gtk.gdk.RGB_DITHER_NONE,
				  0, 0)

#
# MAIN
#
if __name__ == "__main__":

    take_screenshot = 0

    #
    # cover up background with screenshot so they cant do anything to it
    #

    if take_screenshot:
	width = gtk.gdk.screen_width()
	height = gtk.gdk.screen_height()
	screenshot = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, gtk.FALSE, 8,
					width, height)

	screenshot.get_from_drawable(gtk.gdk.get_default_root_window(),
					 gtk.gdk.colormap_get_system(),
					 0, 0, 0, 0,
					 width, height)

	screenshot.save ("testimage", "png")

	win = gtk.Window(gtk.WINDOW_TOPLEVEL)

	area = gtk.DrawingArea()
	area.set_size_request(width, height)
	area.connect("expose-event", exposeCB, None)

	win.add(area)
	win.show_all()

    #
    # now do release notes dialog
    #
    
    textWin = gtk.Dialog(flags=gtk.DIALOG_MODAL)

    table = gtk.Table(3, 3, gtk.FALSE)
    textWin.vbox.pack_start(table)
    textWin.add_button('gtk-close', gtk.RESPONSE_NONE)
    textWin.connect("response", relnotes_closed)
    vbox1 = gtk.VBox ()        
    vbox1.set_border_width (10)
    frame = gtk.Frame ("")
    frame.add(vbox1)
    frame.set_label_align (0.5, 0.5)
    frame.set_shadow_type (gtk.SHADOW_NONE)

    textWin.set_position (gtk.WIN_POS_CENTER)

    relnotes = loadReleaseNotes(sys.argv[1])

    if relnotes is not None:
	text = TextViewBrowser()
	text.set_buffer(relnotes)

	sw = gtk.ScrolledWindow()
	sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
	sw.set_shadow_type(gtk.SHADOW_IN)
	sw.add(text)
	vbox1.pack_start(sw)

	a = gtk.Alignment (0, 0, 1.0, 1.0)
	a.add (frame)

	textWin.set_default_size (635, 393)
	textWin.set_size_request (635, 393)
	textWin.set_position (gtk.WIN_POS_CENTER)

	table.attach (a, 1, 2, 1, 2,
		      gtk.FILL | gtk.EXPAND,
		      gtk.FILL | gtk.EXPAND, 5, 5)

	textWin.set_border_width(0)
	addFrame(textWin, _("Release Notes"))
	textWin.show_all()
    else:
	textWin.set_position (gtk.WIN_POS_CENTER)
	label = gtk.Label(_("Unable to load file!"))

	table.attach (label, 1, 2, 1, 2,
		      gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 5, 5)

	textWin.set_border_width(0)
	addFrame(textWin)
	textWin.show_all()

    # set cursor to normal (assuming that anaconda set it to busy when
    # it exec'd this viewer app to give progress indicator to user).
    root = gtk.gdk.get_default_root_window()
    cursor = gtk.gdk.Cursor(gtk.gdk.LEFT_PTR)
    root.set_cursor(cursor)

    gtk.main()
    
