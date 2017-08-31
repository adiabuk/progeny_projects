#
# partitions.py: partition object containing partitioning info
#
# Matt Wilson <msw@redhat.com>
# Jeremy Katz <katzj@redhat.com>
# Mike Fulbright <msf@redhat.com>
# Harald Hoyer <harald@redhat.de>
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
"""Overarching partition object."""

import parted
import iutil
import isys
import string
import os, sys

from constants import *

import fsset
import raid
import lvm
import partedUtils
import partRequests

from rhpl.translate import _
from rhpl.log import log

class Partitions:
    """Defines all of the partition requests and delete requests."""
    def __init__ (self, diskset = None):
        """Initializes a Partitions object.

        Can pass in the diskset if it already exists.
        """
        self.requests = []
        """A list of RequestSpec objects for all partitions."""

        self.deletes = []
        """A list of DeleteSpec objects for partitions to be deleted."""

        self.autoPartitionRequests = []
        """A list of RequestSpec objects for autopartitioning.
        These are setup by the installclass and folded into self.requests
        by auto partitioning."""

        self.autoClearPartType = CLEARPART_TYPE_NONE
        """What type of partitions should be cleared?"""

        self.autoClearPartDrives = None
        """Drives to clear partitions on (note that None is equiv to all)."""

        self.nextUniqueID = 1
        """Internal counter.  Don't touch unless you're smarter than me."""

        self.reinitializeDisks = 0
        """Should the disk label be reset on all disks?"""

        self.zeroMbr = 0
        """Should the mbr be zero'd?"""

        # partition method to be used.  not to be touched externally
        self.useAutopartitioning = 1
        self.useFdisk = 0

        # autopartitioning info becomes kickstart partition requests
        # and its useful to be able to differentiate between the two
        self.isKickstart = 0

        if diskset:
            self.setFromDisk(diskset)


    def setFromDisk(self, diskset):
        """Clear the delete list and set self.requests to reflect disk."""
        self.deletes = []
        self.requests = []
        diskset.refreshDevices()
        labels = diskset.getLabels()
        drives = diskset.disks.keys()
        drives.sort()
        for drive in drives:
            disk = diskset.disks[drive]
            part = disk.next_partition()
            while part:
                if part.type & parted.PARTITION_METADATA:
                    part = disk.next_partition(part)
                    continue

                format = None
                if part.type & parted.PARTITION_FREESPACE:
                    ptype = None
                elif part.type & parted.PARTITION_EXTENDED:
                    ptype = None
                elif part.get_flag(parted.PARTITION_RAID) == 1:
                    ptype = fsset.fileSystemTypeGet("software RAID")
                elif part.get_flag(parted.PARTITION_LVM) == 1:
                    ptype = fsset.fileSystemTypeGet("physical volume (LVM)")
                else:
                    ptype = partedUtils.get_partition_file_system_type(part)

                    # FIXME: we don't handle ptype being None very well, so
                    # just say it's foreign.  Should probably fix None
                    # handling instead some day.
                    if ptype is None:
                        ptype = fsset.fileSystemTypeGet("foreign")
                    
                start = part.geom.start
                end = part.geom.end
                size = partedUtils.getPartSizeMB(part)
                drive = partedUtils.get_partition_drive(part)

                spec = partRequests.PreexistingPartitionSpec(ptype,
                                                             size = size,
                                                             start = start,
                                                             end = end,
                                                             drive = drive,
                                                             format = format)
                spec.device = fsset.PartedPartitionDevice(part).getDevice()

                # set label if makes sense
                if ptype and ptype.isMountable() and \
                   (ptype.getName() == "ext2" or ptype.getName() == "ext3"):
                    if spec.device in labels.keys():
                        if labels[spec.device] and len(labels[spec.device])>0:
                            spec.fslabel = labels[spec.device]

                self.addRequest(spec)
                part = disk.next_partition(part)

        # now we need to read in all pre-existing RAID stuff
        diskset.startAllRaid()
        mdList = diskset.mdList
        for raidDev in mdList:
            (theDev, devices, level, numActive) = raidDev

            level = "RAID%s" %(level,)
            try:
                chunk = isys.getRaidChunkFromDevice(theDev)
            except Exception, e:
                log("couldn't get chunksize of %s: %s" %(theDev, e))
                chunk = None
            
            # is minor always mdN ?
            minor = int(theDev[2:])
            raidvols = []
            for dev in devices:
                req = self.getRequestByDeviceName(dev)
                if not req:
                    log("RAID device %s using non-existent partition %s"
                        %(theDev, dev))
                    continue
                raidvols.append(req.uniqueID)
                

            fs = partedUtils.sniffFilesystemType(theDev)
            if fs is None:
                fsystem = fsset.fileSystemTypeGet("foreign")
            else:
                fsystem = fsset.fileSystemTypeGet(fs)

            mnt = None
            format = 0
                    
            spares = len(devices) - numActive
            spec = partRequests.RaidRequestSpec(fsystem, format = format,
                                                raidlevel = level,
                                                raidmembers = raidvols,
                                                raidminor = minor,
                                                raidspares = spares,
                                                mountpoint = mnt,
                                                preexist = 1,
                                                chunksize = chunk)
            spec.size = spec.getActualSize(self, diskset)
            self.addRequest(spec)

        # now to read in pre-existing LVM stuff
        lvm.vgscan()
        lvm.vgactivate()

        pvs = lvm.pvlist()
        for (vg, size) in lvm.vglist():
            # FIXME: need to find the pe size of the vg
            pesize = 4096
            try:
                preexist_size = float(size) / 1024.0
            except:
                log("preexisting size for %s not a valid integer, ignoring" %(vg,))
                preexist_size = None

            pvids = []
            for (dev, pvvg, size) in pvs:
                if vg != pvvg:
                    continue
                req = self.getRequestByDeviceName(dev[5:])
                if not req:
                    log("Volume group %s using non-existent partition %s"
                        %(vg, dev))
                    continue
                pvids.append(req.uniqueID)
            spec = partRequests.VolumeGroupRequestSpec(format = 0,
                                                       vgname = vg,
                                                       physvols = pvids,
                                                       pesize = pesize,
                                                       preexist = 1,
                                                       preexist_size = preexist_size)
            vgid = self.addRequest(spec)

            for (lvvg, lv, size) in lvm.lvlist():
                if lvvg != vg:
                    continue
                
                # size is number of bytes, we want size in megs
                lvsize = float(size) / (1024.0 * 1024.0)

                theDev = "/dev/%s/%s" %(vg, lv)
                fs = partedUtils.sniffFilesystemType(theDev)
                if fs is None:
                    fsystem = fsset.fileSystemTypeGet("foreign")
                else:
                    fsystem = fsset.fileSystemTypeGet(fs)

                mnt = 0
                format = 0

                spec = partRequests.LogicalVolumeRequestSpec(fsystem,
                                                             format = format,
                                                             size = lvsize,
                                                             volgroup = vgid,
                                                             lvname = lv,
                                                             mountpoint = mnt,
                                                             preexist = 1)
                self.addRequest(spec)
        lvm.vgdeactivate()

        diskset.stopAllRaid()
            
        

    def addRequest (self, request):
        """Add a new request to the list."""
        if not request.uniqueID:
            request.uniqueID = self.nextUniqueID
            self.nextUniqueID = self.nextUniqueID + 1
        self.requests.append(request)
        self.requests.sort()

        return request.uniqueID

    def addDelete (self, delete):
        """Add a new DeleteSpec to the list."""
        self.deletes.append(delete)
        self.deletes.sort()

    def removeRequest (self, request):
        """Remove a request from the list."""
        self.requests.remove(request)

    def getRequestByMountPoint(self, mount):
        """Find and return the request with the given mountpoint."""
        for request in self.requests:
            if request.mountpoint == mount:
                return request
	    
	for request in self.requests:
	    if request.type == REQUEST_LV and request.mountpoint == mount:
		return request
        return None

    def getRequestByDeviceName(self, device):
        """Find and return the request with the given device name."""
	if device is None:
	    return None
	
        for request in self.requests:
	    if request.type == REQUEST_RAID and request.raidminor is not None:
		tmp = "md%d" % (request.raidminor,)
		if tmp == device:
		    return request
	    elif request.device == device:
                return request
        return None


    def getRequestsByDevice(self, diskset, device):
        """Find and return the requests on a given device (like 'hda')."""
        if device is None:
            return None

        drives = diskset.disks.keys()
        if device not in drives:
            return None

        rc = []
        disk = diskset.disks[device]
        part = disk.next_partition()
        while part:
            dev = partedUtils.get_partition_name(part)
            request = self.getRequestByDeviceName(dev)

            if request:
                rc.append(request)
            part = disk.next_partition(part)

        if len(rc) > 0:
            return rc
        else:
            return None

    def getRequestByVolumeGroupName(self, volname):
        """Find and return the request with the given volume group name."""
	if volname is None:
	    return None
	
	for request in self.requests:
	    if (request.type == REQUEST_VG and
                request.volumeGroupName == volname):
		return request
        return None

    def getRequestByLogicalVolumeName(self, lvname):
        """Find and return the request with the given logical volume name."""
	if lvname is None:
	    return None
	for request in self.requests:
	    if (request.type == REQUEST_LV and
                request.logicalVolumeName == lvname):
		return request
        return None

    def getRequestByID(self, id):
        """Find and return the request with the given unique ID.

        Note that if id is a string, it will be converted to an int for you.
        """
	if type(id) == type("a string"):
	    id = int(id)
        for request in self.requests:
            if request.uniqueID == id:
                return request
        return None

    def getRaidRequests(self):
        """Find and return a list of all of the RAID requests."""
        retval = []
        for request in self.requests:
            if request.type == REQUEST_RAID:
                retval.append(request)

        return retval

    def getRaidDevices(self):
        """Find and return a list of all of the requests for use in RAID."""
        raidRequests = []
        for request in self.requests:
            if isinstance(request, partRequests.RaidRequestSpec):
                raidRequests.append(request)
                
        return raidRequests

    def getAvailableRaidMinors(self):
        """Find and return a list of all of the unused minors for use in RAID."""
        raidMinors = range(0,32)
        for request in self.requests:
            if isinstance(request, partRequests.RaidRequestSpec) and request.raidminor in raidMinors:
                raidMinors.remove(request.raidminor)
                
        return raidMinors
	

    def getAvailRaidPartitions(self, request, diskset):
        """Return a list of tuples of RAID partitions which can be used.

        Return value is (part, size, used) where used is 0 if not,
        1 if so, 2 if used for *this* request.
        """
        rc = []
        drives = diskset.disks.keys()
        raiddevs = self.getRaidDevices()
        drives.sort()
        for drive in drives:
            disk = diskset.disks[drive]
            for part in partedUtils.get_raid_partitions(disk):
                partname = partedUtils.get_partition_name(part)
                used = 0
                for raid in raiddevs:
                    if raid.raidmembers:
                        for raidmem in raid.raidmembers:
                            tmpreq = self.getRequestByID(raidmem)
                            if (partname == tmpreq.device):
                                if raid.uniqueID == request.uniqueID:
                                    used = 2
                                else:
                                    used = 1
                                break
                    if used:
                        break
                size = partedUtils.getPartSizeMB(part)

                if not used:
                    rc.append((partname, size, 0))
                elif used == 2:
                    rc.append((partname, size, 1))
		    
        return rc

    def getRaidMemberParent(self, request):
        """Return RAID device request containing this request."""
        raiddev = self.getRaidRequests()
        if not raiddev or not request.device:
            return None
        for dev in raiddev:
            if not dev.raidmembers:
                continue
            for member in dev.raidmembers:
                if request.device == self.getRequestByID(member).device:
                    return dev
        return None

    def isRaidMember(self, request):
        """Return whether or not the request is being used in a RAID device."""
	if self.getRaidMemberParent(request) is not None:
	    return 1
	else:
	    return 0

    def getLVMLVForVGID(self, vgid):        
        """Find and return a list of all the LVs associated with a VG id."""
        retval = []
        for request in self.requests:
	    if request.type == REQUEST_LV:
		if request.volumeGroup == vgid:
                    retval.append(request)
        return retval

    def getLVMLVForVG(self, vgrequest):
        """Find and return a list of all of the LVs in the VG."""
        vgid = vgrequest.uniqueID
        return self.getLVMLVForVGID(vgid)
		
    def getLVMRequests(self):
        """Return a dictionary of all of the LVM bits.

        The dictionary returned is of the form vgname: [ lvrequests ]
        """
        retval = {}
        for request in self.requests:
            if request.type == REQUEST_VG:
                retval[request.volumeGroupName] = self.getLVMLVForVG(request)
	    
        return retval

    def getLVMVGRequests(self):
        """Find and return a list of all of the volume groups."""
        retval = []
        for request in self.requests:
            if request.type == REQUEST_VG:
                retval.append(request)

        return retval

    def getLVMLVRequests(self):
        """Find and return a list of all of the logical volumes."""
        retval = []
        for request in self.requests:
            if request.type == REQUEST_LV:
                retval.append(request)

        return retval

    def getAvailLVMPartitions(self, request, diskset):
        """Return a list of tuples of PV partitions which can be used.

        Return value is (part, size, used) where used is 0 if not,
        1 if so, 2 if used for *this* request.
        """
        rc = []
        drives = diskset.disks.keys()
        drives.sort()
        volgroups = self.getLVMVGRequests()
        for drive in drives:
            disk = diskset.disks[drive]
            for part in partedUtils.get_lvm_partitions(disk):
                partname = partedUtils.get_partition_name(part)
                partrequest = self.getRequestByDeviceName(partname)
                used = 0
                for volgroup in volgroups:
                    if volgroup.physicalVolumes:
                        if partrequest.uniqueID in volgroup.physicalVolumes:
                            if (request and request.uniqueID and
                                volgroup.uniqueID == request.uniqueID):
                                used = 2
                            else:
                                used = 1

                    if used:
                        break
                size = partedUtils.getPartSizeMB(part)                    

                if used == 0:
                    rc.append((partrequest.uniqueID, size, 0))
                elif used == 2:
                    rc.append((partrequest.uniqueID, size, 1))

	# now find available RAID devices
	raiddev = self.getRaidRequests()
	if raiddev:
	    raidcounter = 0
	    for dev in raiddev:
                used = 0

		if dev.fstype is None:
		    continue
		if dev.fstype.getName() != "physical volume (LVM)":
		    continue
		
                for volgroup in volgroups:
                    if volgroup.physicalVolumes:
                        if dev.uniqueID in volgroup.physicalVolumes:
                            if (request and request.uniqueID and
                                volgroup.uniqueID == request.uniqueID):
                                used = 2
                            else:
                                used = 1

                    if used:
                        break
		    
                size = dev.getActualSize(self, diskset)

                if used == 0:
                    rc.append((dev.uniqueID, size, 0))
                elif used == 2:
                    rc.append((dev.uniqueID, size, 1))

		raidcounter = raidcounter + 1
        return rc

    def getLVMVolumeGroupMemberParent(self, request):
        """Return parent volume group of a physical volume"""
	volgroups = self.getLVMVGRequests()
	if not volgroups:
	    return None

	for volgroup in volgroups:
	    if volgroup.physicalVolumes:
		if request.uniqueID in volgroup.physicalVolumes:
		    return volgroup

	return None

    def isLVMVolumeGroupMember(self, request):
        """Return whether or not the request is being used in an LVM device."""
	if self.getLVMVolumeGroupMemberParent(request) is None:
	    return 0
	else:
	    return 1
    
    def isVolumeGroupNameInUse(self, vgname):
        """Return whether or not the requested volume group name is in use."""
        if not vgname:
            return None

        lvmrequests = self.getLVMRequests()
        if not lvmrequests:
            return None

        if vgname in lvmrequests.keys():
            return 1
        return 0

    def getBootableRequest(self):
        """Return the name of the current 'boot' mount point."""
        bootreq = None

        if iutil.getArch() == "ia64":
            bootreq = self.getRequestByMountPoint("/boot/efi")
            if bootreq:
                return [ bootreq ]
            else:
                return None
        elif iutil.getPPCMachine() == "iSeries":
            for req in self.requests:
                if req.fstype == fsset.fileSystemTypeGet("PPC PReP Boot"):
                    return [ req ]
            return None
        elif iutil.getPPCMachine() == "pSeries":
            # pSeries bootable requests are odd.
            # have to consider both the PReP partition (with potentially > 1
            # existing) as well as /boot,/

            # for the prep partition, we want either the first or the
            # first non-preexisting one
            bestprep = None
            for req in self.requests:
                if req.fstype == fsset.fileSystemTypeGet("PPC PReP Boot"):
                    if ((bestprep is None) or
                        (bestprep.getPreExisting() and
                         not req.getPreExisting())):
                        bestprep = req

            if bestprep:
                ret = [ bestprep ]
            else:
                ret = []

            # now add the /boot
            bootreq = self.getRequestByMountPoint("/boot")
            if not bootreq:
                bootreq = self.getRequestByMountPoint("/")
            if bootreq:
                ret.append(bootreq)

            if len(ret) >= 1:
                return ret
            return None
        
        if not bootreq:
            bootreq = self.getRequestByMountPoint("/boot")
        if not bootreq:
            bootreq = self.getRequestByMountPoint("/")

        if bootreq:
            return [ bootreq ]
        return None

    def getBootableMountpoints(self):
        """Return a list of bootable valid mountpoints for this arch."""
        # FIXME: should be somewhere else, preferably some sort of arch object

        if iutil.getArch() == "ia64":
            return [ "/boot/efi" ]
        else:
            return [ "/boot", "/" ]

    def isBootable(self, request):
        """Returns if the request should be considered a 'bootable' request.

        This basically means that it should be sorted to the beginning of
        the drive to avoid cylinder problems in most cases.
        """
        bootreqs = self.getBootableRequest()
        if not bootreqs:
            return 0

        for bootreq in bootreqs:
            if bootreq == request:
                return 1

            if bootreq.type == REQUEST_RAID and \
                   request.uniqueID in bootreq.raidmembers:
                return 1

        return 0

    def sortRequests(self):
        """Resort the requests into allocation order."""
        n = 0
        while n < len(self.requests):
	    # Ignore LVM Volume Group and Logical Volume requests,
	    # since these are not related to allocating disk partitions
	    if (self.requests[n].type == REQUEST_VG or self.requests[n].type == REQUEST_LV):
		n = n + 1
		continue
	    
            for request in self.requests:
		# Ignore LVM Volume Group and Logical Volume requests,
		# since these are not related to allocating disk partitions
		if (request.type == REQUEST_VG or request.type == REQUEST_LV):
		    continue
                # for raid requests, the only thing that matters for sorting
                # is the raid device since ordering by size is mostly
                # irrelevant.  this also keeps things more consistent
                elif (request.type == REQUEST_RAID or
                    self.requests[n].type == REQUEST_RAID):
                    if (request.type == self.requests[n].type and
                        (self.requests[n].raidminor != None) and
                        ((request.raidminor is None) or
                         request.raidminor > self.requests[n].raidminor)):
                        tmp = self.requests[n]
                        index = self.requests.index(request)
                        self.requests[n] = request
                        self.requests[index] = tmp
                # for sized requests, we want the larger ones first
                elif (request.size and self.requests[n].size and
                    (request.size < self.requests[n].size)):
                    tmp = self.requests[n]
                    index = self.requests.index(request)
                    self.requests[n] = request
                    self.requests[index] = tmp
                # for cylinder-based, sort by order on the drive
                elif (request.start and self.requests[n].start and
                      (request.drive == self.requests[n].drive) and
                      (request.type == self.requests[n].type) and 
                      (request.start > self.requests[n].start)):
                    tmp = self.requests[n]
                    index = self.requests.index(request)
                    self.requests[n] = request
                    self.requests[index] = tmp
                # finally just use when they defined the partition so
                # there's no randomness thrown in
                elif (request.size and self.requests[n].size and
                      (request.size == self.requests[n].size) and
                      (request.uniqueID < self.requests[n].uniqueID)):
                    tmp = self.requests[n]
                    index = self.requests.index(request)
                    self.requests[n] = request
                    self.requests[index] = tmp                
            n = n + 1

        tmp = self.getBootableRequest()

        boot = []
        if tmp:
            for req in tmp:
                # if raid, we want all of the contents of the bootable raid
                if req.type == REQUEST_RAID:
                    for member in req.raidmembers:
                        boot.append(self.getRequestByID(member))
                else:
                    boot.append(req)

        # remove the bootables from the request
        for bootable in boot:
            self.requests.pop(self.requests.index(bootable))

        # move to the front of the list
        boot.extend(self.requests)
        self.requests = boot

    def sanityCheckAllRequests(self, diskset, baseChecks = 0):
        """Do a sanity check of all of the requests.

        This function is called at the end of partitioning so that we
        can make sure you don't have anything silly (like no /, a really
        small /, etc).  Returns (errors, warnings) where each is a list
        of strings or None if there are none.
        If baseChecks is set, the basic sanity tests which the UI runs prior to
        accepting a partition will be run on the requests as well.
        """
        checkSizes = [('/usr', 250), ('/tmp', 50), ('/var', 384),
                      ('/home', 100), ('/boot', 75)]
        warnings = []
        errors = []

        slash = self.getRequestByMountPoint('/')
        if not slash:
            errors.append(_("You have not defined a root partition (/), "
                            "which is required for installation of %s "
                            "to continue.") % (productName,))

        if slash and slash.getActualSize(self, diskset) < 250:
            warnings.append(_("Your root partition is less than 250 "
                              "megabytes which is usually too small to "
                              "install %s.") % (productName,))

        if iutil.getArch() == "ia64":
            bootreq = self.getRequestByMountPoint("/boot/efi")
            if not bootreq or bootreq.getActualSize(self, diskset) < 50:
                errors.append(_("You must create a /boot/efi partition of "
                                "type FAT and a size of 50 megabytes."))

        if (iutil.getPPCMachine() == "pSeries" or
            iutil.getPPCMachine() == "iSeries"):
            reqs = self.getBootableRequest()
            found = 0

            bestreq = None
            if reqs:
                for req in reqs:
                    if req.fstype == fsset.fileSystemTypeGet("PPC PReP Boot"):
                        found = 1
                        # the best one is either the first or the first
                        # newly formatted one
                        if ((bestreq is None) or ((bestreq.format == 0) and
                                                  (req.format == 1))):
                            bestreq = req
                        break
            if iutil.getPPCMachine() == "iSeries" and iutil.hasIbmSis():
                found = 1
                
            if not found:
                errors.append(_("You must create a PPC PReP Boot partition."))

            if bestreq is not None:
                if (iutil.getPPCMachine() == "pSeries"):
                    minsize = 4
                else:
                    minsize = 16
                if bestreq.getActualSize(self, diskset) < minsize:
                    warnings.append(_("Your %s partition is less than %s "
                                      "megabytes which is lower than "
                                      "recommended for a normal %s install.")
                                    %(_("PPC PReP Boot"), minsize, productName))
                    

        for (mount, size) in checkSizes:
            req = self.getRequestByMountPoint(mount)
            if not req:
                continue
            if req.getActualSize(self, diskset) < size:
                warnings.append(_("Your %s partition is less than %s "
                                  "megabytes which is lower than recommended "
                                  "for a normal %s install.")
                                %(mount, size, productName))

        foundSwap = 0
        swapSize = 0
        for request in self.requests:
            if request.fstype and request.fstype.getName() == "swap":
                foundSwap = foundSwap + 1
                swapSize = swapSize + request.getActualSize(self, diskset)
            if baseChecks:
                rc = request.doSizeSanityCheck()
                if rc:
                    warnings.append(rc)
                rc = request.doMountPointLinuxFSChecks()
                if rc:
                    errors.append(rc)
                if isinstance(request, partRequests.RaidRequestSpec):
                    rc = request.sanityCheckRaid(self)
                    if rc:
                        errors.append(rc)

        bootreqs = self.getBootableRequest()
        if bootreqs:
            for bootreq in bootreqs:
                if (bootreq and
                    (isinstance(bootreq, partRequests.RaidRequestSpec)) and
                    (not raid.isRaid1(bootreq.raidlevel))):
                    errors.append(_("Bootable partitions can only be on RAID1 "
                                    "devices."))

                # can't have bootable partition on LV
                if (bootreq and
                    (isinstance(bootreq,
                                partRequests.LogicalVolumeRequestSpec))):
                    errors.append(_("Bootable partitions cannot be on a "
                                    "logical volume."))

                # most arches can't have boot on RAID
                if (bootreq and
                    (isinstance(bootreq, partRequests.RaidRequestSpec)) and
                    (iutil.getArch() not in raid.raidBootArches)):
                    errors.append("Bootable partitions cannot be on a RAID "
                                  "device.")

        if foundSwap == 0:
            warnings.append(_("You have not specified a swap partition.  "
                              "Although not strictly required in all cases, "
                              "it will significantly improve performance for "
                              "most installations."))

        # XXX number of swaps not exported from kernel and could change
        if foundSwap >= 32:
            warnings.append(_("You have specified more than 32 swap devices.  "
                              "The kernel for %s only supports 32 "
                              "swap devices.") % (productName,))

        mem = iutil.memInstalled()
        rem = mem % 16384
        if rem:
            mem = mem + (16384 - rem)
        mem = mem / 1024

        if foundSwap and (swapSize < (mem - 8)) and (mem < 1024):
            warnings.append(_("You have allocated less swap space (%dM) than "
                              "available RAM (%dM) on your system.  This "
                              "could negatively impact performance.")
                            %(swapSize, mem))

        if warnings == []:
            warnings = None
        if errors == []:
            errors = None

        return (errors, warnings)

    def setProtected(self, dispatch):
        """Set any partitions which should be protected to be so."""
        protected = dispatch.method.protectedPartitions()
        if protected:
            for device in protected:
                log("%s is a protected partition" % (device))
                request = self.getRequestByDeviceName(device)
                if request is not None:
                    request.setProtected(1)
                else:
                    log("no request, probably a removable drive")

    def copy (self):
        """Deep copy the object."""
        new = Partitions()
        for request in self.requests:
            new.addRequest(request)
        for delete in self.deletes:
            new.addDelete(delete)
        new.autoPartitionRequests = self.autoPartitionRequests
        new.autoClearPartType = self.autoClearPartType
        new.autoClearPartDrives = self.autoClearPartDrives
        new.nextUniqueID = self.nextUniqueID
        new.useAutopartitioning = self.useAutopartitioning
        new.useFdisk = self.useFdisk
        new.reinitializeDisks = self.reinitializeDisks
        return new

    def getClearPart(self):
        """Get the kickstart directive related to the clearpart being used."""
        clearpartargs = []
        if self.autoClearPartType == CLEARPART_TYPE_LINUX:
            clearpartargs.append('--linux')
        elif self.autoClearPartType == CLEARPART_TYPE_ALL:
            clearpartargs.append('--all')
        else:
            return None

        if self.reinitializeDisks:
            clearpartargs.append('--initlabel')

        if self.autoClearPartDrives:
            drives = string.join(self.autoClearPartDrives, ',')
            clearpartargs.append('--drives=%s' % (drives))

        return "#clearpart %s\n" %(string.join(clearpartargs))
    
    def writeKS(self, f):
        """Write out the partitioning information in kickstart format."""
        f.write("# The following is the partition information you requested\n")
        f.write("# Note that any partitions you deleted are not expressed\n")
        f.write("# here so unless you clear all partitions first, this is\n")
        f.write("# not guaranteed to work\n")
        clearpart = self.getClearPart()
        if clearpart:
            f.write(clearpart)

        # lots of passes here -- parts, raid, volgroup, logvol
        # XXX what do we do with deleted partitions?
        for request in self.requests:
            args = []
            if request.type == REQUEST_RAID:
                continue

            # no fstype, no deal (same with foreigns)
            if not request.fstype or request.fstype.getName() == "foreign":
                continue

            # first argument is mountpoint, which can also be swap or
            # the unique RAID identifier.  I hate kickstart partitioning
            # syntax.  a lot.  too many special cases 
            if request.fstype.getName() == "swap":
                args.append("swap")
            elif request.fstype.getName() == "software RAID":
                # since we guarantee that uniqueIDs are ints now...
                args.append("raid.%s" % (request.uniqueID))
            elif request.fstype.getName() == "physical volume (LVM)":
                # see above about uniqueIDs being ints
                args.append("pv.%s" % (request.uniqueID))
            elif request.mountpoint:
                args.append(request.mountpoint)
                args.append("--fstype")
                args.append(request.fstype.getName())
            else:
                continue

            # generic options
            if not request.format:
                args.append("--noformat")
            if request.badblocks:
                args.append("--badblocks")

            # preexisting only
            if request.type == REQUEST_PREEXIST and request.device:
                args.append("--onpart")
                args.append(request.device)
            # we have a billion ways to specify new partitions
            elif request.type == REQUEST_NEW:
                if request.size:
                    args.append("--size=%s" % (request.size))
                if request.grow:
                    args.append("--grow")
                if request.start:
                    args.append("--start=%s" % (request.start))
                if request.end:
                    args.append("--end=%s" % (request.end))
                if request.maxSizeMB:
                    args.append("--maxsize=%s" % (request.maxSizeMB))
                if request.drive:
                    args.append("--ondisk=%s" % (request.drive[0]))
                if request.primary:
                    args.append("--asprimary")
            else: # how the hell did we get this?
                continue

            f.write("#part %s\n" % (string.join(args)))
                
                
        for request in self.requests:
            args = []
            if request.type != REQUEST_RAID:
                continue

            # no fstype, no deal (same with foreigns)
            if not request.fstype or request.fstype.getName() == "foreign":
                continue

            # also require a raidlevel and raidmembers for raid
            if (request.raidlevel == None) or not request.raidmembers:
                continue

            # first argument is mountpoint, which can also be swap
            if request.fstype.getName() == "swap":
                args.append("swap")
            elif request.fstype.getName() == "physical volume (LVM)":
                # see above about uniqueIDs being ints
                args.append("pv.%s" % (request.uniqueID))
            elif request.mountpoint:
                args.append(request.mountpoint)
            else:
                continue

            # generic options
            if not request.format:
                args.append("--noformat")
            if request.fstype:
                args.append("--fstype")
                args.append(request.fstype.getName())
            if request.badblocks:
                args.append("--badblocks")

            args.append("--level=%s" % (request.raidlevel))

            if request.raidspares:
                args.append("--spares=%s" % (request.raidspares))

            # silly raid member syntax
            raidmems = []
            for member in request.raidmembers:
                if (type(member) != type("")) or (member[0:5] != "raid."):
                    raidmems.append("raid.%s" % (member))
                else:
                    raidmems.append(member)
            args.append("%s" % (string.join(raidmems)))

            f.write("#raid %s\n" % (string.join(args)))

        for request in self.requests:
            args = []
            if request.type != REQUEST_VG:
                continue

            args.append(request.volumeGroupName)

            # silly pv syntax
            pvs = []
            for member in request.physicalVolumes:
                if (type(member) != type("")) or not member.startswith("pv."):
                    pvs.append("pv.%s" % (member))
                else:
                    pvs.append(member)
            args.append("%s" % (string.join(pvs)))

            f.write("#volgroup %s\n" % (string.join(args)))

        for request in self.requests:
            args = []
            if request.type != REQUEST_LV:
                continue

            # no fstype, no deal (same with foreigns)
            if not request.fstype or request.fstype.getName() == "foreign":
                continue

            # require a vg name and an lv name
            if (request.logicalVolumeName is None or
                request.volumeGroup is None):
                continue

            # first argument is mountpoint, which can also be swap
            if request.fstype.getName() == "swap":
                args.append("swap")
            elif request.mountpoint:
                args.append(request.mountpoint)
            else:
                continue

            # generic options
            if not request.format:
                args.append("--noformat")
            if request.fstype:
                args.append("--fstype")
                args.append(request.fstype.getName())

            vg = self.getRequestByID(request.volumeGroup)
            if vg is None:
                continue

            args.extend(["--name=%s" %(request.logicalVolumeName,),
                         "--vgname=%s" %(vg.volumeGroupName,)])

	    if request.grow:
		if request.startSize is not None:
		    args.append("--size=%s" % (request.startSize,))
		else:
		    # shouldnt happen
		    continue
		
		args.append("--grow")
		if request.maxSizeMB is not None and int(request.maxSizeMB) > 0:
		    args.append("--maxsize=%s" % (request.maxSizeMB,))
	    else:
		if request.percent is not None:
		    args.append("--percent=%s" %(request.percent,))
		elif request.size is not None:
		    args.append("--size=%s" %(request.size,))
		else:
		    continue
            
            f.write("#logvol %s\n" % (string.join(args)))            

    def deleteAllLogicalPartitions(self, part):
        """Add delete specs for all logical partitions in part."""
        for partition in partedUtils.get_logical_partitions(part.disk):
            partName = partedUtils.get_partition_name(partition)
            request = self.getRequestByDeviceName(partName)
            self.removeRequest(request)
            if request.preexist:
                drive = partedUtils.get_partition_drive(partition)
                delete = partRequests.DeleteSpec(drive, partition.geom.start,
                                                 partition.geom.end)
                self.addDelete(delete)

    def containsImmutablePart(self, part):
        """Returns whether the partition contains parts we can't delete."""
        if not part or (type(part) == type("RAID")) or (type(part) == type(1)):
            return None

        if not part.type & parted.PARTITION_EXTENDED:
            return None

        disk = part.disk
        while part:
            if not part.is_active():
                part = disk.next_partition(part)
                continue

            device = partedUtils.get_partition_name(part)
            request = self.getRequestByDeviceName(device)

            if request:
                if request.getProtected():
                    return _("the partition in use by the installer.")

                if self.isRaidMember(request):
                    return _("a partition which is a member of a RAID array.")

                if self.isLVMVolumeGroupMember(request):
                    return _("a partition which is a member of a LVM Volume Group.")
                    
            part = disk.next_partition(part)
        return None


    def doMetaDeletes(self, diskset):
        """Does the removal of all of the non-physical volumes in the delete list."""

        # have to have lvm on, which requires raid to be started
        diskset.startAllRaid()
        lvm.vgactivate()

        # now, go through and delete logical volumes
        for delete in self.deletes:
            if isinstance(delete, partRequests.DeleteLogicalVolumeSpec):
                if not delete.beenDeleted():
                    lvm.lvremove(delete.name, delete.vg)
                    delete.setDeleted(1)

        # now, go through and delete volume groups
        for delete in self.deletes:
            if isinstance(delete, partRequests.DeleteVolumeGroupSpec):
                if not delete.beenDeleted():
                    lvm.vgremove(delete.name)
                    delete.setDeleted(1)

        lvm.vgdeactivate()
        diskset.stopAllRaid()


    def deleteDependentRequests(self, request):
        """Handle deletion of this request and all requests which depend on it.

        eg, delete all logical volumes from a volume group, all volume groups
        which depend on the raid device.

        Side effects: removes all dependent requests from self.requests
                      adds needed dependent deletes to self.deletes
        """

        toRemove = []
        id = request.uniqueID
        for req in self.requests:
            if isinstance(req, partRequests.RaidRequestSpec):
                if id in req.raidmembers:
                    toRemove.append(req)
                # XXX do we need to do anything special with preexisting raids?
            elif isinstance(req, partRequests.VolumeGroupRequestSpec):
                if id in req.physicalVolumes:
                    toRemove.append(req)
                    if req.getPreExisting():
                        delete = partRequests.DeleteVolumeGroupSpec(req.volumeGroupName)
                        self.addDelete(delete)
            elif isinstance(req, partRequests.LogicalVolumeRequestSpec):
                if id == req.volumeGroup:
                    toRemove.append(req)
                    tmp = self.getRequestByID(req.volumeGroup)
                    if not tmp:
                        log("Unable to find the vg for %s"
                            % (req.logicalVolumeName,))
                        vgname = req.volumeGroup
                    else:
                        vgname = tmp.volumeGroupName

                    if req.getPreExisting():
                        delete = partRequests.DeleteLogicalVolumeSpec(req.logicalVolumeName,
                                                                      vgname)
                        self.addDelete(delete)

        for req in toRemove:
            self.deleteDependentRequests(req)
            self.removeRequest(req)
        
