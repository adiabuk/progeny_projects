#
# lvm_dialog_gui.py: dialog for editting a volume group request
#
# Michael Fulbright <msf@redhat.com>
#
# Copyright 2002 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import copy

import gobject
import gtk

from rhpl.translate import _, N_

import gui
from fsset import *
from partRequests import *
from partition_ui_helpers_gui import *
from constants import *
import lvm


class VolumeGroupEditor:

    def numAvailableLVSlots(self):
	return max(0, lvm.MAX_LV_SLOTS - len(self.logvolreqs))

    def computeSpaceValues(self, alt_pvlist=None, usepe=None):
	if usepe is None:
	    pesize = self.peOptionMenu.get_active().get_data("value")
	else:
	    pesize = usepe

        if alt_pvlist is None:
            pvlist = self.getSelectedPhysicalVolumes(self.lvmlist.get_model())
        else:
            pvlist = alt_pvlist
	tspace = self.computeVGSize(pvlist, pesize)
	uspace = self.computeLVSpaceNeeded(self.logvolreqs)
	fspace =  tspace - uspace

	return (tspace, uspace, fspace)

    def getPVWastedRatio(self, newpe):
        """ given a new pe value, return percentage of smallest PV wasted

        newpe - (int) new value of PE, in KB
        """
        pvlist = self.getSelectedPhysicalVolumes(self.lvmlist.get_model())

	waste = 0.0
	for id in pvlist:
	    pvreq = self.partitions.getRequestByID(id)
	    pvsize = pvreq.getActualSize(self.partitions, self.diskset)
	    waste = max(waste, (long(pvsize*1024) % newpe)/(pvsize*1024.0))

	return waste

    def getSmallestPVSize(self):
        """ finds the smallest PV and returns its size in MB
        """
	first = 1
        pvlist = self.getSelectedPhysicalVolumes(self.lvmlist.get_model())
	for id in pvlist:
	    pvreq = self.partitions.getRequestByID(id)
	    pvsize = pvreq.getActualSize(self.partitions, self.diskset)
	    if first:
		minpvsize = pvsize
		first = 0
	    else:
		minpvsize = min(pvsize, minpvsize)

	return minpvsize


    def reclampLV(self, newpe):
        """ given a new pe value, set logical volume sizes accordingly

        newpe - (int) new value of PE, in KB
        """

        pvlist = self.getSelectedPhysicalVolumes(self.lvmlist.get_model())
        availSpaceMB = self.computeVGSize(pvlist, newpe)

	# see if total space is enough
        oldused = 0
        used = 0
	resize = 0
        for lv in self.logvolreqs:
            osize = lv.getActualSize(self.partitions, self.diskset)
            oldused = oldused + osize
            nsize = lvm.clampLVSizeRequest(osize, newpe, roundup=1)
	    if nsize != osize:
		resize = 1
		
            used = used + nsize

        if used > availSpaceMB:
            self.intf.messageWindow(_("Not enough space"),
                                    _("The physical extent size cannot be "
                                      "changed because otherwise the space "
                                      "required by the currently defined "
                                      "logical volumes will be increased "
                                      "to more than the available space."),
				    custom_icon="error")
            return 0

	if resize:
	    rc = self.intf.messageWindow(_("Confirm Physical Extent Change"),
					 _("This change in the value of the "
					   "physical extent will require the "
					   "sizes of the current logical "
					   "volume requests to be rounded "
					   "up in size to an integer multiple "
					   "of the "
					   "physical extent.\n\nThis change "
					   "will take affect immediately."),
					 type="custom", custom_icon="question",
					 custom_buttons=["gtk-cancel", _("C_ontinue")])
	    if not rc:
		return 0
        
        for lv in self.logvolreqs:
            osize = lv.getActualSize(self.partitions, self.diskset)
            nsize = lvm.clampLVSizeRequest(osize, newpe, roundup=1)
            lv.setSize(nsize)

        return 1
            
    def peChangeCB(self, widget, peOption):
        """ handle changes in the Physical Extent option menu

        widget - menu item which was activated
        peOption - the Option menu containing the items. The data value for
                   "lastval" is the previous PE value.
        """
        curval = widget.get_data("value")
        lastval = peOption.get_data("lastpe")
	lastidx = peOption.get_data("lastidx")

	# see if PE is too large compared to smallest PV
	# remember PE is in KB, PV size is in MB
	maxpvsize = self.getSmallestPVSize()
	if curval > maxpvsize * 1024:
            self.intf.messageWindow(_("Not enough space"),
                                    _("The physical extent size cannot be "
                                      "changed because the value selected "
				      "(%10.2f MB) is larger than the smallest "
				      "physical volume (%10.2f MB) in the "
				      "volume group.") % (curval/1024.0, maxpvsize), custom_icon="error")
	    peOption.set_history(lastidx)
            return 0

	# see if new PE will make any PV useless due to overhead
	if lvm.clampPVSize(maxpvsize, curval) * 1024 < curval:
            self.intf.messageWindow(_("Not enough space"),
                                    _("The physical extent size cannot be "
                                      "changed because the value selected "
				      "(%10.2f MB) is too large compared "
                                      "to the size of the "
				      "smallest physical volume "
				      "(%10.2f MB) in the "
				      "volume group.") % (curval/1024.0,
                                                          maxpvsize),
                                    custom_icon="error")
	    peOption.set_history(lastidx)
            return 0
	    

	if self.getPVWastedRatio(curval) > 0.10:
	    rc = self.intf.messageWindow(_("Too small"),
					 _("This change in the value of the "
					   "physical extent will waste "
					   "substantial space on one or more "
					   "of the physical volumes in the "
					   "volume group."),
					 type="custom", custom_icon="error",
					   custom_buttons=["gtk-cancel", _("C_ontinue")])
	    if not rc:
		peOption.set_history(lastidx)
		return 0

	# now see if we need to fixup effect PV and LV sizes based on PE
        if curval > lastval:
            rc = self.reclampLV(curval)
            if not rc:
		peOption.set_history(lastidx)
		return 0
            else:
                self.updateLogVolStore()
	else:
	    maxlv = lvm.getMaxLVSize(curval)
	    for lv in self.logvolreqs:
		lvsize = lv.getActualSize(self.partitions, self.diskset)
		if lvsize > maxlv:
		    self.intf.messageWindow(_("Not enough space"),
					    _("The physical extent size "
					      "cannot be changed because the "
					      "resulting maximum logical "
					      "volume size (%10.2f MB) is "
					      "smaller "
					      "than one or more of the "
					      "currently defined logical "
					      "volumes.") % (maxlv,),
					    custom_icon="error")
		    peOption.set_history(lastidx)
		    return 0
            
        peOption.set_data("lastpe", curval)
	peOption.set_data("lastidx", peOption.get_history())
        self.updateAllowedLvmPartitionsList(self.availlvmparts,
					    self.partitions,
					    self.lvmlist)
	self.updateVGSpaceLabels()

    def prettyFormatPESize(self, val):
        if val < 1024:
            return "%s KB" % (val,)
        elif val < 1024*1024:
            return "%s MB" % (val/1024,)
        else:
            return "%s GB" % (val/1024/1024,)

    def createPEOptionMenu(self, default=4096):
	peOption = gtk.OptionMenu()
	peOptionMenu = gtk.Menu()

	idx = 0
	defindex = None
	actualPE = lvm.getPossiblePhysicalExtents(floor=1024)
	for curpe in actualPE:
	    # dont show PE over 64M
	    if curpe > 65536:
		continue
	    
            val = self.prettyFormatPESize(curpe)

            item = gtk.MenuItem(val)
            item.set_data("value", curpe)
	    item.show()
	    peOptionMenu.add(item)
            item.connect("activate", self.peChangeCB, peOption)

	    if default == curpe:
		defindex = idx
		
	    idx = idx + 1

	peOption.set_menu(peOptionMenu)
        peOption.set_data("lastpe", default)

	if defindex:
	    peOption.set_history(defindex)

        peOption.set_data("lastidx", peOption.get_history())
	
	return (peOption, peOptionMenu)

    def clickCB(self, row, data):
	model = self.lvmlist.get_model()
	pvlist = self.getSelectedPhysicalVolumes(model)

	# get the selected row
	iter = model.get_iter((string.atoi(data),))

	# we invert val because we get called before checklist
	# changes the toggle state
	val      = not model.get_value(iter, 0)
	partname = model.get_value(iter, 1)
	id = self.partitions.getRequestByDeviceName(partname).uniqueID
	if val:
	    pvlist.append(id)
	else:
	    pvlist.remove(id)

	(availSpaceMB, neededSpaceMB, fspace) = self.computeSpaceValues(alt_pvlist=pvlist)
	if availSpaceMB < neededSpaceMB:
	    self.intf.messageWindow(_("Not enough space"),
				    _("You cannot remove this physical "
				      "volume because otherwise the "
				      "volume group will be too small to "
				      "hold the currently defined logical "
				      "volumes."), custom_icon="error")
	    return gtk.FALSE

	self.updateVGSpaceLabels(alt_pvlist = pvlist)
	return gtk.TRUE
	

    def createAllowedLvmPartitionsList(self, alllvmparts, reqlvmpart, partitions, preexist = 0):

	store = gtk.TreeStore(gobject.TYPE_BOOLEAN,
			      gobject.TYPE_STRING,
			      gobject.TYPE_STRING)
	partlist = WideCheckList(2, store, self.clickCB)

	sw = gtk.ScrolledWindow()
	sw.add(partlist)
	sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
	sw.set_shadow_type(gtk.SHADOW_IN)

	for uid, size, used in alllvmparts:
	    request = partitions.getRequestByID(uid)
	    if request.type != REQUEST_RAID:
		partname = "%s" % (request.device,)
	    else:
		partname = "md%d" % (request.raidminor,)

	    # clip size to current PE
	    pesize = self.peOptionMenu.get_active().get_data("value")
	    size = lvm.clampPVSize(size, pesize)
	    partsize = "%10.2f MB" % size
	    if used or not reqlvmpart:
		selected = 1
	    else:
		selected = 0

            if preexist == 0 or selected == 1:
                partlist.append_row((partname, partsize), selected)

	return (partlist, sw)

    def updateAllowedLvmPartitionsList(self, alllvmparts, partitions, partlist):
	""" update sizes in pv list

	alllvmparts - list of pv from partitions.getAvailLVMPartitions
	partitions - object holding all partition requests
	partlist - the checklist containing pv list
	"""

	row = 0
	for uid, size, used in alllvmparts:
	    # clip size to current PE
	    pesize = self.peOptionMenu.get_active().get_data("value")
	    size = lvm.clampPVSize(size, pesize)
	    partsize = "%10.2f MB" % size

	    iter = partlist.store.get_iter((int(row),))
	    partlist.store.set_value(iter, 2, partsize)
	    row = row + 1
	
    def getCurrentLogicalVolume(self):
	selection = self.logvollist.get_selection()
	(model, iter) = selection.get_selected()
	return iter


    def editLogicalVolume(self, logrequest, isNew = 0):
	if isNew:
	    tstr = _("Make Logical Volume")
	else:
	    try:
		tstr = _("Edit Logical Volume: %s") % (logrequest.logicalVolumeName,)
	    except:
		tstr = _("Edit Logical Volume")
	    
        dialog = gtk.Dialog(tstr, self.parent)
        gui.addFrame(dialog)
        dialog.add_button('gtk-cancel', 2)
        dialog.add_button('gtk-ok', 1)
        dialog.set_position(gtk.WIN_POS_CENTER)

        maintable = gtk.Table()
        maintable.set_row_spacings(5)
        maintable.set_col_spacings(5)
        row = 0

        lbl = createAlignedLabel(_("_Mount Point:"))
	maintable.attach(lbl, 0, 1, row,row+1)
        mountCombo = createMountPointCombo(logrequest, excludeMountPoints=["/boot"])
        lbl.set_mnemonic_widget(mountCombo.entry)
        maintable.attach(mountCombo, 1, 2, row, row + 1)
        row = row + 1

        if not logrequest or not logrequest.getPreExisting():
            lbl = createAlignedLabel(_("_File System Type:"))
            maintable.attach(lbl, 0, 1, row, row + 1)
            (newfstype, newfstypeMenu) = createFSTypeMenu(logrequest.fstype,
                                                          fstypechangeCB,
                                                          mountCombo,
                                                          ignorefs = ["software RAID", "physical volume (LVM)", "vfat", "PPC PReP Boot"])
            lbl.set_mnemonic_widget(newfstype)
        else:
            maintable.attach(createAlignedLabel(_("Original File System Type:")),
                             0, 1, row, row + 1)
            if logrequest.origfstype and logrequest.origfstype.getName():
                newfstype = gtk.Label(logrequest.origfstype.getName())
            else:
                newfstype = gtk.Label(_("Unknown"))
	maintable.attach(newfstype, 1, 2, row, row + 1)
	row = row+1


        if not logrequest or not logrequest.getPreExisting():
            lbl = createAlignedLabel(_("_Logical Volume Name:"))
            lvnameEntry = gtk.Entry(16)
            lbl.set_mnemonic_widget(lvnameEntry)
            if logrequest and logrequest.logicalVolumeName:
                lvnameEntry.set_text(logrequest.logicalVolumeName)
            else:
                lvnameEntry.set_text(lvm.createSuggestedLVName(self.logvolreqs))
        else:
            lbl = createAlignedLabel(_("Logical Volume Name:"))
            lvnameEntry = gtk.Label(logrequest.logicalVolumeName)
            
        maintable.attach(lbl, 0, 1, row, row + 1)
        maintable.attach(lvnameEntry, 1, 2, row, row + 1)
        row = row + 1

        if not logrequest or not logrequest.getPreExisting():
            lbl = createAlignedLabel(_("_Size (MB):"))
            sizeEntry = gtk.Entry(16)
            lbl.set_mnemonic_widget(sizeEntry)
            if logrequest:
                sizeEntry.set_text("%g" % (logrequest.getActualSize(self.partitions, self.diskset),))
        else:
            lbl = createAlignedLabel(_("Size (MB):"))
            sizeEntry = gtk.Label(str(logrequest.size))
            
        maintable.attach(lbl, 0, 1, row, row+1)
        maintable.attach(sizeEntry, 1, 2, row, row + 1)
        row = row + 1

        if not logrequest or not logrequest.getPreExisting():
            pesize = self.peOptionMenu.get_active().get_data("value")
            (tspace, uspace, fspace) = self.computeSpaceValues(usepe=pesize)
            maxlv = min(lvm.getMaxLVSize(pesize), fspace)

            # add in size of current logical volume if it has a size
            if logrequest and not isNew:
                maxlv = maxlv + logrequest.getActualSize(self.partitions, self.diskset)
            maxlabel = createAlignedLabel(_("(Max size is %s MB)") % (maxlv,))
            maintable.attach(maxlabel, 1, 2, row, row + 1)

	self.fsoptionsDict = {}
	if logrequest.getPreExisting():
	    (row, self.fsoptionsDict) = createPreExistFSOptionSection(logrequest, maintable, row, mountCombo, showbadblocks=0, ignorefs = ["software RAID", "physical volume (LVM)", "vfat"])

        dialog.vbox.pack_start(maintable)
        dialog.show_all()

	while 1:
	    rc = dialog.run()
	    if rc == 2:
		dialog.destroy()
		return

            if not logrequest or not logrequest.getPreExisting():
                fsystem = newfstypeMenu.get_active().get_data("type")
                format = 1
                migrate = 0
            else:
		if self.fsoptionsDict.has_key("formatrb"):
		    formatrb = self.fsoptionsDict["formatrb"]
		else:
		    formatrb = None

		if formatrb:
                    format = formatrb.get_active()
                    if format:
                        fsystem = self.fsoptionsDict["fstypeMenu"].get_active().get_data("type")
                else:
                    format = 0

		if self.fsoptionsDict.has_key("migraterb"):
		    migraterb = self.fsoptionsDict["migraterb"]
		else:
		    migraterb = None
		    
		if migraterb:
                    migrate = migraterb.get_active()
                    if migrate:
                        fsystem = self.fsoptionsDict["migfstypeMenu"].get_active().get_data("type")
                else:
                    migrate = 0

                # set back if we are not formatting or migrating
		origfstype = logrequest.origfstype
                if not format and not migrate:
                    fsystem = origfstype

            mntpt = string.strip(mountCombo.entry.get_text())

            if not logrequest or not logrequest.getPreExisting():
                # check size specification
                badsize = 0
                try:
                    size = long(sizeEntry.get_text())
                except:
                    badsize = 1

                if badsize or size <= 0:
                    self.intf.messageWindow(_("Illegal size"),
                                            _("The requested size as entered is "
                                              "not a valid number greater "
                                              "than 0."), custom_icon="error")
                    continue
            else:
                size = logrequest.size

	    # is this an existing logical volume or one we're editting
            if logrequest:
                preexist = logrequest.getPreExisting()
            else:
                preexist = 0

	    # test mount point
            # check in pending logical volume requests
	    # these may not have been put in master list of requests
	    # yet if we have not hit 'OK' for the volume group creation
	    if fsystem.isMountable():
		used = 0
		if logrequest:
		    curmntpt = logrequest.mountpoint
		else:
		    curmntpt = None
		    
		for lv in self.logvolreqs:
		    if curmntpt and lv.mountpoint == curmntpt:
			continue

		    if lv.mountpoint == mntpt:
			used = 1
			break

		if used:
		    self.intf.messageWindow(_("Mount point in use"),
					    _("The mount point \"%s\" is in "
					      "use, please pick another.") %
					    (mntpt,), custom_icon="error")
		    continue

	    # check out logical volumne name
	    lvname = string.strip(lvnameEntry.get_text())

            if not logrequest or not logrequest.getPreExisting():
                err = sanityCheckLogicalVolumeName(lvname)
                if err:
                    self.intf.messageWindow(_("Illegal Logical Volume Name"),err, custom_icon="error")
                    continue

	    # is it in use?
	    used = 0
	    if logrequest:
		origlvname = logrequest.logicalVolumeName
	    else:
		origlvname = None

	    for lv in self.logvolreqs:
		if origlvname and lv.logicalVolumeName == origlvname:
		    continue

		if lv.logicalVolumeName == lvname:
		    used = 1
		    break

	    if used:
		self.intf.messageWindow(_("Illegal logical volume name"),
					_("The logical volume name \"%s\" is "
					  "already in use. Please pick "
					  "another.") % (lvname,), custom_icon="error")
		continue

	    # create potential request
	    request = copy.copy(logrequest)
	    pesize = self.peOptionMenu.get_active().get_data("value")
	    size = lvm.clampLVSizeRequest(size, pesize, roundup=1)

	    # do some final tests
	    maxlv = lvm.getMaxLVSize(pesize)
	    if size > maxlv:
		self.intf.messageWindow(_("Not enough space"),
					_("The current requested size "
					  "(%10.2f MB) is larger than maximum "
					  "logical volume size (%10.2f MB). "
					  "To increase this limit you can "
					  "increase the Physical Extent size "
					  "for this Volume Group."), custom_icon="error")
		continue

 	    request.fstype = fsystem

 	    if request.fstype.isMountable():
 		request.mountpoint = mntpt
 	    else:
 		request.mountpoint = None

            request.preexist = preexist
	    request.logicalVolumeName = lvname
	    request.size = size
            request.format = format
            request.migrate = migrate
	    request.badblock = None

	    # this is needed to clear out any cached info about the device
	    # only a workaround - need to change way this is handled in
	    # partRequest.py really.
	    request.dev = None
	    
	    # make list of original logvol requests so we can skip them
	    # in tests below. We check for mount point name conflicts
	    # above within the current volume group, so it is not
	    # necessary to do now.
 	    err = request.sanityCheckRequest(self.partitions, skipMntPtExistCheck=1)
	    if err is None:
		skiplist = []
		for lv in self.origvolreqs:
		    skiplist.append(lv.uniqueID)
		    
		err = request.isMountPointInUse(self.partitions, requestSkipList=skiplist)

 	    if err:
 		self.intf.messageWindow(_("Error With Request"),
 					"%s" % (err), custom_icon="error")
 		continue

	    if (not request.format and
		request.mountpoint and request.formatByDefault()):
		if not queryNoFormatPreExisting(self.intf):
		    continue

	    # see if there is room for request
	    (availSpaceMB, neededSpaceMB, fspace) = self.computeSpaceValues(usepe=pesize)

	    tmplogreqs = []
	    for l in self.logvolreqs:
		if origlvname and l.logicalVolumeName == origlvname:
		    continue
		
		tmplogreqs.append(l)

	    tmplogreqs.append(request)
	    neededSpaceMB = self.computeLVSpaceNeeded(tmplogreqs)

	    if neededSpaceMB > availSpaceMB:
		self.intf.messageWindow(_("Not enough space"),
					_("The logical volumes you have "
					  "configured require %g MB, but the "
					  "volume group only has %g MB.  Please "
					  "either make the volume group larger "
					  "or make the logical volume(s) smaller.") % (neededSpaceMB, availSpaceMB), custom_icon="error")
		del tmplogreqs
		continue

	    # everything ok
	    break

	# now remove the previous request, insert request created above
	if not isNew:
	    self.logvolreqs.remove(logrequest)
	    iter = self.getCurrentLogicalVolume()
	    self.logvolstore.remove(iter)
	    
        self.logvolreqs.append(request)

	iter = self.logvolstore.append()
	self.logvolstore.set_value(iter, 0, lvname)
	if request.fstype and request.fstype.isMountable():
	    self.logvolstore.set_value(iter, 1, mntpt)
	else:
	    self.logvolstore.set_value(iter, 1, "N/A")
	    
	self.logvolstore.set_value(iter, 2, "%g" % (size,))

	self.updateVGSpaceLabels()
        dialog.destroy()
	
    def editCurrentLogicalVolume(self):
	iter = self.getCurrentLogicalVolume()

	if iter is None:
	    return
	
	logvolname = self.logvolstore.get_value(iter, 0)
	logrequest = None
	for lv in self.logvolreqs:
	    if lv.logicalVolumeName == logvolname:
		logrequest = lv
		
	if logrequest is None:
	    return

	self.editLogicalVolume(logrequest)

    def addLogicalVolumeCB(self, widget):
	if self.numAvailableLVSlots() < 1:
	    self.intf.messageWindow(_("No free slots"),
				    _("You cannot create more than %s logical "
				    "volumes per volume group.") % (lvm.MAX_LV_SLOTS,), custom_icon="error")
	    return
	
        (tspace, uspace, fspace) = self.computeSpaceValues()
	if fspace <= 0:
	    self.intf.messageWindow(_("No free space"),
				    _("There is no room left in the "
				      "volume group to create new logical "
				      "volumes. "
				      "To add a logical volume you will need "
				      "to reduce the size of one or more of "
				      "the currently existing "
				      "logical volumes"), custom_icon="error")
	    return
	    
        request = LogicalVolumeRequestSpec(fileSystemTypeGetDefault(),
					   size = fspace)
	self.editLogicalVolume(request, isNew = 1)
	return

    def editLogicalVolumeCB(self, widget):
	self.editCurrentLogicalVolume()
	return

    def delLogicalVolumeCB(self, widget):
	iter = self.getCurrentLogicalVolume()
	if iter is None:
	    return
	
	logvolname = self.logvolstore.get_value(iter, 0)
	if logvolname is None:
	    return

	rc = self.intf.messageWindow(_("Confirm Delete"),
				_("Are you sure you want to Delete the "
				"logical volume \"%s\"?") % (logvolname,),
				type = "custom", custom_buttons=["gtk-cancel", _("_Delete")], custom_icon="warning")
	if not rc:
	    return

	for lv in self.logvolreqs:
	    if lv.logicalVolumeName == logvolname:
		self.logvolreqs.remove(lv)

	self.logvolstore.remove(iter)

	self.updateVGSpaceLabels()
	return
    
    def logvolActivateCb(self, view, path, col):
	self.editCurrentLogicalVolume()

    def getSelectedPhysicalVolumes(self, model):
	pv = []
	next = model.get_iter_first()
	currow = 0
	while next is not None:
	    iter = next
	    val      = model.get_value(iter, 0)
	    partname = model.get_value(iter, 1)
	    
	    if val:
		pvreq = self.partitions.getRequestByDeviceName(partname)
		id = pvreq.uniqueID
		pv.append(id)

	    next = model.iter_next(iter)
	    currow = currow + 1

	return pv

    def computeVGSize(self, pvlist, curpe):
	availSpaceMB = 0
	for id in pvlist:
	    pvreq = self.partitions.getRequestByID(id)
	    pvsize = pvreq.getActualSize(self.partitions, self.diskset)
	    pvsize = lvm.clampPVSize(pvsize, curpe)

	    # have to clamp pvsize to multiple of PE
	    availSpaceMB = availSpaceMB + pvsize

	return availSpaceMB

    def computeLVSpaceNeeded(self, logreqs):
	neededSpaceMB = 0
	for lv in logreqs:
	    neededSpaceMB = neededSpaceMB + lv.getActualSize(self.partitions, self.diskset)

	return neededSpaceMB

    def updateLogVolStore(self):
        self.logvolstore.clear()
        for lv in self.logvolreqs:
            iter = self.logvolstore.append()
            size = lv.getActualSize(self.partitions, self.diskset)
            lvname = lv.logicalVolumeName
            mntpt = lv.mountpoint
            if lvname:
                self.logvolstore.set_value(iter, 0, lvname)
                
            if lv.fstype and lv.fstype.isMountable() and mntpt:
                self.logvolstore.set_value(iter, 1, mntpt)
	    else:
		self.logvolstore.set_value(iter, 1, "N/A")
                
            self.logvolstore.set_value(iter, 2, "%g" % (size,))
        

    def updateVGSpaceLabels(self, alt_pvlist=None):
	if alt_pvlist == None:
	    pvlist = self.getSelectedPhysicalVolumes(self.lvmlist.get_model())
	else:
	    pvlist = alt_pvlist
	    
        (tspace, uspace, fspace) = self.computeSpaceValues(alt_pvlist=pvlist)

	self.totalSpaceLabel.set_text("%10.2f MB" % (tspace,))
	self.usedSpaceLabel.set_text("%10.2f MB" % (uspace,))

	if tspace > 0:
	    usedpercent = (100.0*uspace)/tspace
	else:
	    usedpercent = 0.0
	    
	self.usedPercentLabel.set_text("(%4.1f %%)" % (usedpercent,))

	self.freeSpaceLabel.set_text("%10.2f MB" % (fspace,))
	if tspace > 0:
	    freepercent = (100.0*fspace)/tspace
	else:
	    freepercent = 0.0

	self.freePercentLabel.set_text("(%4.1f %%)" % (freepercent,))

#
# run the VG editor we created
#
    def run(self):
	if self.dialog is None:
	    return None
	
	while 1:
	    rc = self.dialog.run()

	    if rc == 2:
		self.destroy()
		return None

	    pvlist = self.getSelectedPhysicalVolumes(self.lvmlist.get_model())
	    pesize = self.peOptionMenu.get_active().get_data("value")
	    availSpaceMB = self.computeVGSize(pvlist, pesize)
	    neededSpaceMB = self.computeLVSpaceNeeded(self.logvolreqs)

	    if neededSpaceMB > availSpaceMB:
		self.intf.messageWindow(_("Not enough space"),
					_("The logical volumes you have "
					  "configured require %g MB, but the "
					  "volume group only has %g MB.  Please "
					  "either make the volume group larger "
					  "or make the logical volume(s) smaller.") % (neededSpaceMB, availSpaceMB), custom_icon="error")
		continue

	    # check volume name
	    volname = string.strip(self.volnameEntry.get_text())
	    err = sanityCheckVolumeGroupName(volname)
	    if err:
		self.intf.messageWindow(_("Invalid Volume Group Name"), err,
					custom_icon="error")
		continue

	    if self.origvgrequest:
		origvname = self.origvgrequest.volumeGroupName
	    else:
		origname = None

	    if origvname != volname:
		tmpreq = VolumeGroupRequestSpec(physvols = pvlist,
                                                vgname = volname)
		if self.partitions.isVolumeGroupNameInUse(volname):
		    self.intf.messageWindow(_("Name in use"),
					    _("The volume group name \"%s\" is "
					      "already in use. Please pick "
					      "another." % (volname,)),
					    custom_icon="error")
		    del tmpreq
		    continue
		
		del tmpreq

	    # get physical extent
	    pesize = self.peOptionMenu.get_active().get_data("value")

	    # everything ok
	    break

	request = VolumeGroupRequestSpec(physvols = pvlist, vgname = volname,
					 pesize = pesize)

        # if it was preexisting, it still should be
        if self.origvgrequest and self.origvgrequest.getPreExisting():
            request.preexist = 1
            
	return (request, self.logvolreqs)

    def destroy(self):
	if self.dialog:
	    self.dialog.destroy()
	self.dialog = None

    def __init__(self, partitions, diskset, intf, parent, origvgrequest, isNew = 0):
	self.partitions = partitions
	self.diskset = diskset
	self.origvgrequest = origvgrequest
	self.isNew = isNew
	self.intf = intf
	self.parent = parent

        self.availlvmparts = self.partitions.getAvailLVMPartitions(self.origvgrequest,
                                                              self.diskset)
        self.logvolreqs = self.partitions.getLVMLVForVG(self.origvgrequest)
	self.origvolreqs = copy.copy(self.logvolreqs)

        # if no PV exist, raise an error message and return
        if len(self.availlvmparts) < 1:
	    self.intf.messageWindow(_("Not enough physical volumes"),
			       _("At least one unused physical "
				 "volume partition is "
				 "needed to create an LVM Volume Group.\n\n"
				 "Create a partition or RAID array "
				 "of type \"physical volume (LVM)\" and then "
				 "select the \"LVM\" option again."),
				    custom_icon="error")
	    self.dialog = None
            return

	if isNew:
	    tstr = _("Make LVM Volume Group")
	else:
	    try:
		tstr = _("Edit LVM Volume Group: %s") % (origvgrequest.volumeGroupName,)
	    except:
		tstr = _("Edit LVM Volume Group")
	    
        dialog = gtk.Dialog(tstr, self.parent)
        gui.addFrame(dialog)
        dialog.add_button('gtk-cancel', 2)
        dialog.add_button('gtk-ok', 1)

        dialog.set_position(gtk.WIN_POS_CENTER)

        maintable = gtk.Table()
        maintable.set_row_spacings(5)
        maintable.set_col_spacings(5)
        row = 0

        # volume group name
        if not origvgrequest.getPreExisting():
            lbl = createAlignedLabel(_("_Volume Group Name:"))
            self.volnameEntry = gtk.Entry(16)
            lbl.set_mnemonic_widget(self.volnameEntry)
            if not self.isNew:
                self.volnameEntry.set_text(self.origvgrequest.volumeGroupName)
            else:
                self.volnameEntry.set_text(lvm.createSuggestedVGName(self.partitions))
        else:
            lbl = createAlignedLabel(_("Volume Group Name:"))
            self.volnameEntry = gtk.Label(self.origvgrequest.volumeGroupName)
	    
	maintable.attach(lbl, 0, 1, row, row + 1,
                         gtk.EXPAND|gtk.FILL, gtk.SHRINK)
        maintable.attach(self.volnameEntry, 1, 2, row, row + 1, gtk.EXPAND|gtk.FILL, gtk.SHRINK)
	row = row + 1

        if not origvgrequest.getPreExisting():
            lbl = createAlignedLabel(_("_Physical Extent:"))
            (self.peOption, self.peOptionMenu) = self.createPEOptionMenu(self.origvgrequest.pesize)
            lbl.set_mnemonic_widget(self.peOption)
        else:
            # FIXME: this is a nice hack -- if we create the option menu, but
            # don't display it, getting the value always returns what we init'd
            # it to
            lbl = createAlignedLabel(_("Physical Extent:"))
            (self.peOption, self.peOptionMenu) = self.createPEOptionMenu(self.origvgrequest.pesize)            
            self.peOption = gtk.Label(self.prettyFormatPESize(origvgrequest.pesize))

        maintable.attach(lbl, 0, 1, row, row + 1,
                         gtk.EXPAND|gtk.FILL, gtk.SHRINK)
        maintable.attach(self.peOption, 1, 2, row, row + 1, gtk.EXPAND|gtk.FILL, gtk.SHRINK)
        row = row + 1

        (self.lvmlist, sw) = self.createAllowedLvmPartitionsList(self.availlvmparts, self.origvgrequest.physicalVolumes, self.partitions, origvgrequest.getPreExisting())
        if origvgrequest.getPreExisting():
            self.lvmlist.set_sensitive(gtk.FALSE)
        self.lvmlist.set_size_request(275, 80)
        lbl = createAlignedLabel(_("Physical Volumes to _Use:"))
        lbl.set_mnemonic_widget(self.lvmlist)
        maintable.attach(lbl, 0, 1, row, row + 1)
        maintable.attach(sw, 1, 2, row, row + 1)
        row = row + 1

        maintable.attach(createAlignedLabel(_("Used Space:")), 0, 1, row,
			 row + 1, gtk.EXPAND|gtk.FILL, gtk.SHRINK)
	lbox = gtk.HBox()
	self.usedSpaceLabel = gtk.Label("")
	labelalign = gtk.Alignment()
	labelalign.set(1.0, 0.5, 0.0, 0.0)
	labelalign.add(self.usedSpaceLabel)
	lbox.pack_start(labelalign, gtk.FALSE, gtk.FALSE)
	self.usedPercentLabel = gtk.Label("")
	labelalign = gtk.Alignment()
	labelalign.set(1.0, 0.5, 0.0, 0.0)
	labelalign.add(self.usedPercentLabel)
	lbox.pack_start(labelalign, gtk.FALSE, gtk.FALSE, padding=10)
        maintable.attach(lbox, 1, 2, row, row + 1, gtk.EXPAND|gtk.FILL, gtk.SHRINK)
	maintable.set_row_spacing(row, 0)
        row = row + 1

        maintable.attach(createAlignedLabel(_("Free Space:")), 0, 1, row,
			 row + 1, gtk.EXPAND|gtk.FILL, gtk.SHRINK)
	lbox = gtk.HBox()
	self.freeSpaceLabel = gtk.Label("")
	labelalign = gtk.Alignment()
	labelalign.set(1.0, 0.5, 0.0, 0.0)
	labelalign.add(self.freeSpaceLabel)
	lbox.pack_start(labelalign, gtk.FALSE, gtk.FALSE)
	self.freePercentLabel = gtk.Label("")
	labelalign = gtk.Alignment()
	labelalign.set(1.0, 0.5, 0.0, 0.0)
	labelalign.add(self.freePercentLabel)
	lbox.pack_start(labelalign, gtk.FALSE, gtk.FALSE, padding=10)

        maintable.attach(lbox, 1, 2, row, row + 1, gtk.EXPAND|gtk.FILL, gtk.SHRINK)
	maintable.set_row_spacing(row, 0)
        row = row + 1

        maintable.attach(createAlignedLabel(_("Total Space:")), 0, 1, row,
			 row + 1, gtk.EXPAND|gtk.FILL, gtk.SHRINK)
	self.totalSpaceLabel = gtk.Label("")
	labelalign = gtk.Alignment()
	labelalign.set(0.0, 0.5, 0.0, 0.0)
	labelalign.add(self.totalSpaceLabel)
        maintable.attach(labelalign, 1, 2, row, row + 1, gtk.EXPAND|gtk.FILL, gtk.SHRINK)
	maintable.set_row_spacing(row, 5)
        row = row + 1

	# populate list of logical volumes
        lvtable = gtk.Table()
        lvtable.set_row_spacings(5)
        lvtable.set_col_spacings(5)
	self.logvolstore = gtk.ListStore(gobject.TYPE_STRING,
				      gobject.TYPE_STRING,
				      gobject.TYPE_STRING)
	
	if self.logvolreqs:
	    for lvrequest in self.logvolreqs:
		iter = self.logvolstore.append()
		self.logvolstore.set_value(iter, 0, lvrequest.logicalVolumeName)
                if lvrequest.mountpoint is not None:
		    self.logvolstore.set_value(iter, 1, lvrequest.mountpoint)
		else:
		    self.logvolstore.set_value(iter, 1, "")
		self.logvolstore.set_value(iter, 2, "%g" % (lvrequest.getActualSize(self.partitions, self.diskset)))

	self.logvollist = gtk.TreeView(self.logvolstore)
        col = gtk.TreeViewColumn(_("Logical Volume Name"),
				 gtk.CellRendererText(), text=0)
        self.logvollist.append_column(col)
        col = gtk.TreeViewColumn(_("Mount Point"),
				 gtk.CellRendererText(), text=1)
        self.logvollist.append_column(col)
        col = gtk.TreeViewColumn(_("Size (MB)"),
				 gtk.CellRendererText(), text=2)
        self.logvollist.append_column(col)
        self.logvollist.connect('row-activated', self.logvolActivateCb)

        sw = gtk.ScrolledWindow()
        sw.add(self.logvollist)
        sw.set_size_request(100, 100)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
	sw.set_shadow_type(gtk.SHADOW_IN)
        lvtable.attach(sw, 0, 1, 0, 1)

	# button box of options
	lvbbox = gtk.VBox()
        add = gtk.Button(_("_Add"))
        add.connect("clicked", self.addLogicalVolumeCB)
	lvbbox.pack_start(add)
        edit = gtk.Button(_("_Edit"))
        edit.connect("clicked", self.editLogicalVolumeCB)
	lvbbox.pack_start(edit)
        delete = gtk.Button(_("_Delete"))
        delete.connect("clicked", self.delLogicalVolumeCB)
	lvbbox.pack_start(delete)

	lvalign = gtk.Alignment()
	lvalign.set(0.5, 0.0, 0.0, 0.0)
	lvalign.add(lvbbox)
        lvtable.attach(lvalign, 1, 2, 0, 1, gtk.SHRINK, gtk.SHRINK)

	# pack all logical volumne stuff in a frame
	lvtable.set_border_width(12)
        l = gtk.Label()
        l.set_markup("<b>%s</b>" %(_("Logical Volumes"),))
	frame = gtk.Frame()
        frame.set_label_widget(l)
	frame.add(lvtable)
        frame.set_shadow_type(gtk.SHADOW_NONE)

#	dialog.vbox.pack_start(frame)
	maintable.attach(frame, 0, 2, row, row+1)
	row = row + 1
	
        dialog.vbox.pack_start(maintable)
	dialog.set_size_request(500, 450)
        dialog.show_all()

	# set space labels to correct values
	self.updateVGSpaceLabels()

	self.dialog = dialog
