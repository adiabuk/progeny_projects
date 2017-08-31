#
# partition_ui_helpers_gui.py: convenience functions for partition_gui.py
#                              and friends.
#
# Michael Fulbright <msf@redhat.com>
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

import gobject
import gtk
import checklist

from constants import *
from fsset import *
from partitioning import *
from partIntfHelpers import *
from partRequests import *
from partedUtils import *

from rhpl.translate import _, N_

class WideCheckList(checklist.CheckList):
    def toggled_item(self, data, row):

	rc = gtk.TRUE
	if self.clickCB:
	    rc = self.clickCB(data, row)

	if rc == gtk.TRUE:
	    checklist.CheckList.toggled_item(self, data, row)

    
    def __init__(self, columns, store, clickCB=None):
	checklist.CheckList.__init__(self, columns=columns,
				     custom_store=store)

	selection = self.get_selection()
	selection.set_mode(gtk.SELECTION_NONE)

	# make checkbox column wider
	column = self.get_column(0)
	column.set_fixed_width(75)
	column.set_alignment(0.0)

	self.clickCB = clickCB

def createAlignedLabel(text):
    label = gtk.Label(text)
    label.set_alignment(0.0, 0.5)
    label.set_property("use-underline", gtk.TRUE)

    return label

def createMountPointCombo(request, excludeMountPoints=[]):
    mountCombo = gtk.Combo()

    mntptlist = []
    if request.type != REQUEST_NEW and request.fslabel:
	mntptlist.append(request.fslabel)
    
    for p in defaultMountPoints:
	if p in excludeMountPoints:
	    continue
	
	if not p in mntptlist and (p[0] == "/"):
	    mntptlist.append(p)
	
    mountCombo.set_popdown_strings (mntptlist)

    mountpoint = request.mountpoint

    if request.fstype and request.fstype.isMountable():
        mountCombo.set_sensitive(1)
        if mountpoint:
            mountCombo.entry.set_text(mountpoint)
        else:
            mountCombo.entry.set_text("")
    else:
        mountCombo.entry.set_text(_("<Not Applicable>"))
        mountCombo.set_sensitive(0)

    mountCombo.set_data("saved_mntpt", None)

    return mountCombo

def setMntPtComboStateFromType(fstype, mountCombo):
    prevmountable = mountCombo.get_data("prevmountable")
    mountpoint = mountCombo.get_data("saved_mntpt")

    if prevmountable and fstype.isMountable():
        return

    if fstype.isMountable():
        mountCombo.set_sensitive(1)
        if mountpoint != None:
            mountCombo.entry.set_text(mountpoint)
        else:
            mountCombo.entry.set_text("")
    else:
        if mountCombo.entry.get_text() != _("<Not Applicable>"):
            mountCombo.set_data("saved_mntpt", mountCombo.entry.get_text())
        mountCombo.entry.set_text(_("<Not Applicable>"))
        mountCombo.set_sensitive(0)

    mountCombo.set_data("prevmountable", fstype.isMountable())
    
def fstypechangeCB(widget, mountCombo):
    fstype = widget.get_data("type")
    setMntPtComboStateFromType(fstype, mountCombo)

def createAllowedDrivesList(disks, reqdrives):
    store = gtk.TreeStore(gobject.TYPE_BOOLEAN,
			  gobject.TYPE_STRING,
			  gobject.TYPE_STRING,
			  gobject.TYPE_STRING)
    drivelist = WideCheckList(3, store)

    driverow = 0
    drives = disks.keys()
    drives.sort()
    for drive in drives:
        size = getDeviceSizeMB(disks[drive].dev)
	selected = 0
        if reqdrives:
            if drive in reqdrives:
		selected = 1
        else:
	    selected = 1

	sizestr = "%8.0f MB" % size
	drivelist.append_row((drive, sizestr, disks[drive].dev.model),selected)

    if len(drives) < 2:
	drivelist.set_sensitive(0)

    return drivelist

# pass in callback for when fs changes because of python scope issues
def createFSTypeMenu(fstype, fstypechangeCB, mountCombo,
                     availablefstypes = None, ignorefs = None):
    fstypeoption = gtk.OptionMenu()
    fstypeoptionMenu = gtk.Menu()
    types = fileSystemTypeGetTypes()
    if availablefstypes:
        names = availablefstypes
    else:
        names = types.keys()
    if fstype and fstype.isSupported() and fstype.isFormattable():
        default = fstype
    else:
        default = fileSystemTypeGetDefault()
        
    names.sort()
    defindex = None
    i = 0
    for name in names:
        if not fileSystemTypeGet(name).isSupported():
            continue

        if ignorefs and name in ignorefs:
            continue
        
        if fileSystemTypeGet(name).isFormattable():
            item = gtk.MenuItem(name)
            item.set_data("type", types[name])
            # XXX gtk bug, if you don't show then the menu will be larger
            # than the largest menu item
            item.show()
            fstypeoptionMenu.add(item)
            if default and default.getName() == name:
                defindex = i
                defismountable = types[name].isMountable()
            if fstypechangeCB and mountCombo:
                item.connect("activate", fstypechangeCB, mountCombo)
            i = i + 1

    fstypeoption.set_menu(fstypeoptionMenu)

    if defindex:
        fstypeoption.set_history(defindex)

    if mountCombo:
        mountCombo.set_data("prevmountable",
                            fstypeoptionMenu.get_active().get_data("type").isMountable())

    return (fstypeoption, fstypeoptionMenu)

def formatOptionCB(widget, data):
    (menuwidget, menu, mntptcombo, ofstype) = data
    menuwidget.set_sensitive(widget.get_active())

    # inject event for fstype menu
    if widget.get_active():
	fstype = menu.get_active().get_data("type")
	setMntPtComboStateFromType(fstype, mntptcombo)
        menuwidget.grab_focus()
    else:
	setMntPtComboStateFromType(ofstype, mntptcombo)

def noformatCB(widget, badblocks):
    badblocks.set_sensitive(widget.get_active())

def noformatCB2(widget, data):
    (menuwidget, menu, mntptcombo, ofstype) = data
    menuwidget.set_sensitive(not widget.get_active())

    # inject event for fstype menu
    if widget.get_active():
	setMntPtComboStateFromType(ofstype, mntptcombo)


""" createPreExistFSOptionSection: given inputs for a preexisting partition,
    create a section that will provide format and migrate options

    Returns the value of row after packing into the maintable,
    and a dictionary consistenting of:
       noformatrb    - radiobutton for 'leave fs unchanged'
       formatrb      - radiobutton for 'format as new fs'
       fstype        - part of format fstype menu
       fstypeMenu    - part of format fstype menu
       migraterb     - radiobutton for migrate fs
       migfstype     - menu for migrate fs types
       migfstypeMenu - menu for migrate fs types
       badblocks     - toggle button for badblock check
"""
def createPreExistFSOptionSection(origrequest, maintable, row, mountCombo,
                                  showbadblocks=0, ignorefs=[]):
    ofstype = origrequest.fstype

    maintable.attach(gtk.HSeparator(), 0, 2, row, row + 1)
    row = row + 1

    label = gtk.Label(_("How would you like to prepare the file system "
		       "on this partition?"))
    label.set_line_wrap(1)
    label.set_alignment(0.0, 0.0)

    maintable.attach(label, 0, 2, row, row + 1)
    row = row + 1

    noformatrb = gtk.RadioButton(label=_("Leave _unchanged "
					 "(preserve data)"))
    noformatrb.set_active(1)
    maintable.attach(noformatrb, 0, 2, row, row + 1)
    row = row + 1

    formatrb = gtk.RadioButton(label=_("_Format partition as:"),
				    group=noformatrb)
    formatrb.set_active(0)
    if origrequest.format:
	formatrb.set_active(1)

    maintable.attach(formatrb, 0, 1, row, row + 1)
    (fstype, fstypeMenu) = createFSTypeMenu(ofstype, fstypechangeCB,
					    mountCombo, ignorefs=ignorefs)
    fstype.set_sensitive(formatrb.get_active())
    maintable.attach(fstype, 1, 2, row, row + 1)
    row = row + 1

    if not formatrb.get_active() and not origrequest.migrate:
	mountCombo.set_data("prevmountable", ofstype.isMountable())

    formatrb.connect("toggled", formatOptionCB,
		     (fstype, fstypeMenu, mountCombo, ofstype))

    noformatrb.connect("toggled", noformatCB2,
		     (fstype, fstypeMenu, mountCombo, origrequest.origfstype))

    if origrequest.origfstype.isMigratable():
	migraterb = gtk.RadioButton(label=_("Mi_grate partition to:"),
				    group=noformatrb)
	migraterb.set_active(0)
	if origrequest.migrate:
	    migraterb.set_active(1)

	migtypes = origrequest.origfstype.getMigratableFSTargets()

	maintable.attach(migraterb, 0, 1, row, row + 1)
	(migfstype, migfstypeMenu)=createFSTypeMenu(ofstype, None, None,
						    availablefstypes = migtypes)
	migfstype.set_sensitive(migraterb.get_active())
	maintable.attach(migfstype, 1, 2, row, row + 1)
	row = row + 1

	migraterb.connect("toggled", formatOptionCB,
			       (migfstype, migfstypeMenu, mountCombo, ofstype))
    else:
	migraterb = None
	migfstype = None
	migfstypeMenu = None

    if showbadblocks:
        badblocks = gtk.CheckButton(_("Check for _bad blocks?"))
        badblocks.set_active(0)
        maintable.attach(badblocks, 0, 1, row, row + 1)
        formatrb.connect("toggled", noformatCB, badblocks)
        if not origrequest.format:
            badblocks.set_sensitive(0)

        if origrequest.badblocks:
            badblocks.set_active(1)

    else:
        badblocks = None
        
    row = row + 1

    rc = {}
    for var in ['noformatrb', 'formatrb', 'fstype', 'fstypeMenu',
	    'migraterb', 'migfstype', 'migfstypeMenu', 'badblocks' ]:
        if eval("%s" % (var,)) is not None:
            rc[var] = eval("%s" % (var,))

    return (row, rc)

# do tests we just want in UI for now, not kickstart
def doUIRAIDLVMChecks(request, diskset):
    fstype = request.fstype
    numdrives = len(diskset.disks.keys())
    
##     if fstype and fstype.getName() == "physical volume (LVM)":
## 	if request.grow:
## 	    return (_("Partitions of type '%s' must be of fixed size, and "
## 		     "cannot be marked to fill to use available space.")) % (fstype.getName(),)

    if fstype and fstype.getName() in ["physical volume (LVM)", "software RAID"]:
	if numdrives > 1 and (request.drive is None or len(request.drive) > 1):
	    return (_("Partitions of type '%s' must be constrained to "
		      "a single drive.  This is done by selecting the "
		      "drive in the 'Allowable Drives' checklist.")) % (fstype.getName(),)
    
    return None
