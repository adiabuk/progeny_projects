#!/usr/bin/python
#
# raid.py - raid probing control
#
# Erik Troan <ewt@redhat.com>
#
# Copyright 1999-2002 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
"""Raid probing control."""

import parted
import isys
import os
import partitioning
import partedUtils

from rhpl.log import log

# these arches can have their /boot on RAID and not have their
# boot loader blow up
raidBootArches = [ "i386", "x86_64" ]

def scanForRaid(drives):
    """Scans for raid devices on drives.

    drives is a list of device names.
    Returns a list of (mdMinor, devices, level, totalDisks) tuples.
    """
    
    raidSets = {}
    raidDevices = {}

    for d in drives:
        parts = []
	isys.makeDevInode(d, "/tmp/" + d)
        try:
            dev = parted.PedDevice.get("/tmp/" + d)
            disk = parted.PedDisk.new(dev)

            raidParts = partedUtils.get_raid_partitions(disk)
            for part in raidParts:
                parts.append(partedUtils.get_partition_name(part))
        except:
            pass

	os.remove("/tmp/" + d)
        for dev in parts:
            try:
                (major, minor, raidSet, level, nrDisks, totalDisks, mdMinor) =\
                        isys.raidsb(dev)
            except ValueError:
                # bad magic, this can't be part of our raid set
                log("reading raid sb failed for %s",dev)
                continue

	    if raidSets.has_key(raidSet):
	    	(knownLevel, knownDisks, knownMinor, knownDevices) = \
			raidSets[raidSet]
		if knownLevel != level or knownDisks != totalDisks or \
		   knownMinor != mdMinor:
                    # Raise hell
		    log("raid set inconsistency for md%d: "
                        "all drives in this raid set do not "
                        "agree on raid parameters.  Skipping raid device",
                        mdMinor)
                    continue
		knownDevices.append(dev)
		raidSets[raidSet] = (knownLevel, knownDisks, knownMinor,
				     knownDevices)
	    else:
		raidSets[raidSet] = (level, totalDisks, mdMinor, [dev,])

	    if raidDevices.has_key(mdMinor):
	    	if (raidDevices[mdMinor] != raidSet):
		    log("raid set inconsistency for md%d: "
                        "found members of multiple raid sets "
                        "that claim to be md%d.  Using only the first "
                        "array found.", mdMinor, mdMinor)
                    continue
	    else:
	    	raidDevices[mdMinor] = raidSet

    raidList = []
    for key in raidSets.keys():
	(level, totalDisks, mdMinor, devices) = raidSets[key]
	if len(devices) < totalDisks:
            log("missing components of raid device md%d.  The "
                "raid device needs %d drive(s) and only %d (was/were) found. "
                "This raid device will not be started.", mdMinor,
                totalDisks, len(devices))
	    continue
	raidList.append((mdMinor, devices, level, totalDisks))

    return raidList
		
def startAllRaid(driveList):
    """Do a raid start on raid devices and return a list like scanForRaid."""
    rc = []
    mdList = scanForRaid(driveList)
    for mdDevice, deviceList, level, numActive in mdList:
    	devName = "md%d" % (mdDevice,)
	isys.raidstart(devName, deviceList[0])
        rc.append((devName, deviceList, level, numActive))
    return rc

def stopAllRaid(mdList):
    """Do a raid stop on each of the raid device tuples given."""
    for dev, devices, level, numActive in mdList:
	isys.raidstop(dev)


def isRaid5(raidlevel):
    """Return whether raidlevel is a valid descriptor of RAID5."""
    if raidlevel == "RAID5":
        return 1
    elif raidlevel == 5:
        return 1
    elif raidlevel == "5":
        return 1
    return 0

def isRaid1(raidlevel):
    """Return whether raidlevel is a valid descriptor of RAID1."""
    if raidlevel == "RAID1":
        return 1
    elif raidlevel == 1:
        return 1
    elif raidlevel == "1":
        return 1
    return 0

def isRaid0(raidlevel):
    """Return whether raidlevel is a valid descriptor of RAID0."""
    if raidlevel == "RAID0":
        return 1
    elif raidlevel == 0:
        return 1
    elif raidlevel == "0":
        return 1
    return 0

def get_raid_min_members(raidlevel):
    """Return the minimum number of raid members required for raid level"""
    if isRaid0(raidlevel):
        return 2
    elif isRaid1(raidlevel):
        return 2
    elif isRaid5(raidlevel):
        return 3
    else:
        raise ValueError, "invalid raidlevel in get_raid_min_members"

def get_raid_max_spares(raidlevel, nummembers):
    """Return the maximum number of raid spares for raidlevel."""
    if isRaid0(raidlevel):
        return 0
    elif isRaid1(raidlevel) or isRaid5(raidlevel):
        return max(0, nummembers - get_raid_min_members(raidlevel))
    else:
        raise ValueError, "invalid raidlevel in get_raid_max_spares"

def register_raid_device(mdname, newdevices, newlevel, newnumActive):
    """Register a new RAID device in the mdlist."""
    for dev, devices, level, numActive in partedUtils.DiskSet.mdList:
        if mdname == dev:
            if (devices != newdevices or level != newlevel or
                numActive != newnumActive):
                raise ValueError, "%s is already in the mdList!" % (mdname,)
            else:
                return
    partedUtils.DiskSet.mdList.append((mdname, newdevices[:], newlevel,
                                       newnumActive))

def lookup_raid_device(mdname):
    """Return the requested RAID device information."""
    for dev, devices, level, numActive in partedUtils.DiskSet.mdList:
        if mdname == dev:
            return (dev, devices, level, numActive)
    raise KeyError, "md device not found"

