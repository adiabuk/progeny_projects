#
# timezone.py - timezone install data
#
# Copyright 2001 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import iutil
from flags import flags
from rhpl.log import log

def bool(val):
    if val: return "true"
    return "false"

class Timezone:

    def writeKS(self, f):
	f.write("timezone")
	if self.utc:
	    f.write(" --utc")
	f.write(" %s\n" % self.tz)

    def write(self, instPath):
	# dont do this in test mode!
	if flags.test:
	    return
	
	fromFile = instPath + "/usr/share/zoneinfo/" + self.tz

	try:
	    iutil.copyFile(fromFile, instPath + "/etc/localtime")
	except OSError, (errno, msg):
	    log ("Error copying timezone (from %s): %s" % (fromFile, msg))

	f = open(instPath + "/etc/sysconfig/clock", "w")

	f.write('ZONE="%s"\n' % self.tz)
	f.write("UTC=%s\n" % bool(self.utc))
	f.write("ARC=%s\n" % bool(self.arc))

	f.close()

    def getTimezoneInfo(self):
	return (self.tz, self.utc, self.arc)

    def setTimezoneInfo(self, timezone, asUtc = 0, asArc = 0):
	self.tz = timezone
	self.utc = asUtc
	self.arc = asArc

    def __init__(self):
	self.tz = None
	self.utc = 0
	self.arc = 0
        self.utcOffset = 0
        self.dst = 0

