#
# security.py - security install data and installation
#
# Jeremy Katz <katzj@redhat.com>
#
# Copyright 2004 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import os, string
import iutil
from flags import flags

from rhpl.log import log

SEL_DISABLED = 0
SEL_PERMISSIVE = 1
SEL_ENFORCING = 2

selinux_states = { SEL_DISABLED: "disabled",
                   SEL_ENFORCING: "enforcing",
                   SEL_PERMISSIVE: "permissive" }

class Security:
    def __init__(self):
        if flags.selinux == 1:
            self.selinux = SEL_ENFORCING
        else:
            self.selinux = SEL_DISABLED

    def setSELinux(self, val):
        if not selinux_states.has_key(val):
            log("Tried to set to invalid SELinux state: %s" %(val,))
            val = SEL_DISABLED

        self.selinux = val

    def getSELinux(self):
        return self.selinux

    def writeKS(self, f):
        if not selinux_states.has_key(self.selinux):
            log("ERROR: unknown selinux state: %s" %(self.selinux,))
            return

	f.write("selinux --%s\n" %(selinux_states[self.selinux],))

    def write(self, instPath):
        args = [ "/usr/sbin/lokkit", "--quiet", "--nostart" ]

        if not selinux_states.has_key(self.selinux):
            log("ERROR: unknown selinux state: %s" %(self.selinux,))
            return

        args = args + [ "--selinux=%s" %(selinux_states[self.selinux],) ]

        try:
            if flags.setupFilesystems:
                iutil.execWithRedirect(args[0], args, root = instPath,
                                       stdout = None, stderr = None)
            else:
                log("would have run %s", args)
        except RuntimeError, msg:
            log ("lokkit run failed: %s", msg)
        except OSError, (errno, msg):
            log ("lokkit run failed: %s", msg)
        
        
