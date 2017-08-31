#
# bootlocwidget.py: widget for setting the location of the boot loader
#
# Jeremy Katz <katzj@redhat.com>
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

import gtk
import gobject
import iutil
import gui
from rhpl.translate import _, N_

from driveorderwidget import DriveOrderWidget

class BootloaderLocationWidget:
    """Widget to set where to install the boot loader to"""
    
    def __init__(self, bl, fsset, diskset, parent, intf):
        self.bl = bl
        self.fsset = fsset
        self.diskset = diskset
        self.parent = parent
        self.intf = intf
        self.driveOrder = bl.drivelist
        self.usingGrub = self.bl.useGrub()

        locationBox = gtk.VBox (gtk.FALSE, 2)
        locationBox.set_border_width(5)

        label = gtk.Label(_("Install Boot Loader record on:"))
        label.set_alignment(0.0, 0.5)
        locationBox.pack_start(label)

        spacer = gtk.Label("")
        spacer.set_size_request(10, 1)
        locationBox.pack_start(spacer, gtk.FALSE)

        choices = fsset.bootloaderChoices(diskset, self.bl)
        self.bootDevices = {}
        
	if choices:
	    radio = None
            keys = choices.keys()
            keys.reverse()
            for key in keys:
                (device, desc) = choices[key]
		radio = gtk.RadioButton(radio,  
				("/dev/%s %s" % (device, _(desc))))
                locationBox.pack_start(radio, gtk.FALSE)
                self.bootDevices[key] = (radio, device, desc)

                if self.bl.getDevice() == device:
                    radio.set_active(gtk.TRUE)
                else:
                    radio.set_active(gtk.FALSE)

        spacer = gtk.Label("")
        spacer.set_size_request(25, 1)
        locationBox.pack_start(spacer, gtk.FALSE)

        orderButton = gtk.Button(_("_Change Drive Order"))
        locationBox.pack_start(orderButton, gtk.FALSE)
        orderButton.connect("clicked", self.editDriveOrder)

        self.setMbrLabel(self.driveOrder[0])
                    
        alignment = gtk.Alignment()
        alignment.set(0.0, 0, 0, 0)
        alignment.add(locationBox)
        self.widget = alignment

    def editDriveOrder(self, *args):
        # we only support this for grub
        if not self.usingGrub:
            self.intf.messageWindow(_("Unable to Change Drive Order for LILO"),
                                    _("We do not support changing the "
                                      "drive order for use with LILO."),
                                    type="ok")
            return
                                      

            
        dialog = gtk.Dialog(_("Edit Drive Order"), flags = gtk.DIALOG_MODAL)
        gui.addFrame(dialog)
        dialog.set_modal(gtk.TRUE)
        dialog.set_position(gtk.WIN_POS_CENTER)

        label = gui.WrappingLabel(_("Arrange the drives to be in the same "
				    "order as used by the BIOS. Changing "
				    "the drive order may be useful if you "
				    "have multiple SCSI adapters or both SCSI "
				    "and IDE adapters and want to boot from "
				    "the SCSI device.\n\n"
				    "Changing the drive order will change "
				    "where the installation program "
				    "locates the Master Boot Record (MBR)."))
        label.set_alignment(0.0, 0.0)
        dialog.vbox.pack_start(label, padding = 25)

        orderWidget = DriveOrderWidget(self.driveOrder, self.diskset)
        alignment = gtk.Alignment()
        alignment.set(0.5, 0, 0, 0)
        alignment.add(orderWidget.getWidget())
        dialog.vbox.pack_start(alignment)

	dialog.add_button('gtk-cancel', 1)
	dialog.add_button('gtk-ok', 0)
	dialog.show_all()

        while 1:
            rc = dialog.run()
            if rc == 1:
                break

            self.driveOrder = orderWidget.getOrder()
            self.setMbrLabel(self.driveOrder[0])
            break

        dialog.destroy()
        return rc


    # set the label on the mbr radio button to show the right device.
    # kind of a hack
    def setMbrLabel(self, firstDrive):
        if not self.bootDevices.has_key("mbr"):
            return

        (radio, olddev, desc) = self.bootDevices["mbr"]
        radio.set_label("/dev/%s %s" % (firstDrive, _(desc)))
        self.bootDevices["mbr"] = (radio, firstDrive, desc)

    def getWidget(self):
        return self.widget

    def getBootDevice(self):
        for key in self.bootDevices.keys():
            if self.bootDevices[key][0].get_active():
                return self.bootDevices[key][1]

    def getDriveOrder(self):
        return self.driveOrder

    def setUsingGrub(self, val):
        self.usingGrub = val
