#
# confirm_gui.py: install/upgrade point of no return screen.
#
# Copyright 2000-2003 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import gtk
from iw_gui import *
from rhpl.translate import _, N_
from constants import *
from package_gui import queryUpgradeContinue
from image import presentRequiredMediaMessage
import gui
import sys

class ConfirmWindow (InstallWindow):

    # ConfirmWindow tag="aboutupgrade" or "aboutinstall"
    def getScreen (self, labelText, longText):
        hbox = gtk.HBox (gtk.TRUE, 5)
        box = gtk.VBox (gtk.FALSE, 5)

        pix = self.ics.readPixmap ("about-to-install.png")
        if pix:
            a = gtk.Alignment ()
            a.add (pix)
            a.set (0.5, 0.5, 1.0, 1.0)
            hbox.pack_start (a, gtk.FALSE)

	label = gtk.Label (labelText)
        label.set_line_wrap (gtk.TRUE)
        label.set_size_request(190, -1)

	label2 = gtk.Label (longText)
        label2.set_line_wrap (gtk.TRUE)
        label2.set_size_request(190, -1)
        
        box.pack_start (label, gtk.FALSE)
        box.pack_start (label2, gtk.FALSE)
        box.set_border_width (5)

        a = gtk.Alignment ()
        a.add (box)
        a.set (0.5, 0.5, 0.0, 0.0)

        hbox.pack_start (a)
        return hbox
        
class InstallConfirmWindow (ConfirmWindow):
    windowTitle = N_("About to Install")
    htmlTag = "aboutinstall"

    def getNext(self):
	if self.id.methodstr.startswith("cdrom://") and (self.id.instClass.name and self.id.instClass.name != "kickstart"):
	    rc = presentRequiredMediaMessage(self.intf, self.id.grpset)
	    
	    if rc == 0:
		rc2 = self.intf.messageWindow(_("Reboot?"),
					_("The system will be rebooted now."),
					type="custom", custom_icon="warning",
					custom_buttons=[_("_Back"), _("_Reboot")])
		if rc2 == 1:
		    sys.exit(0)
		else:
		    raise gui.StayOnScreen

    def getScreen(self, intf, id):
	self.intf = intf
	self.id = id
	
	return ConfirmWindow.getScreen(self,
	    _("Click next to begin installation of %s.") % (productName,),
	    _("A complete log of the installation can be found in "
	      "the file '%s' after rebooting your system.\n\n"
              "A kickstart file containing the installation options "
	      "selected can be found in the file '%s' after rebooting the "
	      "system.") % (u'/root/install.log', '/root/anaconda-ks.cfg'))

class UpgradeConfirmWindow (ConfirmWindow):
    windowTitle = N_("About to Upgrade")
    htmlTag = "aboutupgrade"

    def getNext(self):
	if self.id.methodstr.startswith("cdrom://") and (self.id.instClass.name and self.id.instClass.name != "kickstart"):
	    rc = presentRequiredMediaMessage(self.intf, self.id.grpset)
	    
	    if rc == 0:
		rc2 = self.intf.messageWindow(_("Reboot?"),
					_("The system will be rebooted now."),
					type="custom", custom_icon="warning",
					custom_buttons=[_("_Back"), _("_Reboot")])
		if rc2 == 1:
		    sys.exit(0)
		else:
		    raise gui.StayOnScreen

    def getScreen(self, intf, id):
	self.intf = intf
	self.id = id
	return ConfirmWindow.getScreen(self,
            _("Click next to begin upgrade of %s.") % (productName,),
            _("A complete log of the upgrade can be found in "
	      "the file '%s' after rebooting your system.") % (u'\uFEFF/\uFEFFroot\uFEFF/\uFEFFupgrade\uFEFF.\uFEFFlog',))

