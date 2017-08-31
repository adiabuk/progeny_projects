#
# timezone_text.py: text mode timezone selection dialog
#
# Copyright 2000-2002 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import string
import iutil
import os
from time import *
from snack import *
from constants_text import *
from rhpl.translate import _, textdomain

textdomain("system-config-date")

class TimezoneWindow:

    def getTimezoneList(self):
	if os.access("/usr/lib/timezones.gz", os.R_OK):
	    cmd = "/usr/bin/gunzip"
	    stdin = os.open("/usr/lib/timezones.gz", 0)
	else:
	    zoneList = iutil.findtz('/usr/share/zoneinfo', '')
	    cmd = ""
	    stdin = None

        if cmd != "":
            zones = iutil.execWithCapture(cmd, [ cmd ], stdin = stdin)
            zoneList = string.split(zones)

	if (stdin != None):
            os.close(stdin)

	return zoneList

    def updateSysClock(self):
	if os.access("/sbin/hwclock", os.X_OK):
	    args = [ "/sbin/hwclock" ]
	else:
	    args = [ "/usr/sbin/hwclock" ]

	args.append("--hctosys")
	if self.c.selected():
	    args.append("--utc")

	iutil.execWithRedirect(args[0], args)
	self.g.setTimer(500)
	self.updateClock()

    def updateClock(self):
        # disable for now
        return
        
#	if os.access("/usr/share/zoneinfo/" + self.l.current(), os.R_OK):
#	    os.environ['TZ'] = self.l.current()
#	    self.label.setText(self.currentTime())
#	else:
#	    self.label.setText("")

    def currentTime(self):
	return "Current time: " + strftime("%X %Z", localtime(time()))

    def __call__(self, screen, instLang, timezone):
	timezones = self.getTimezoneList()
	(default, asUtc, asArc) = timezone.getTimezoneInfo()
        if not default:
	    default = instLang.getDefaultTimeZone()

	bb = ButtonBar(screen, [TEXT_OK_BUTTON, TEXT_BACK_BUTTON])
	t = TextboxReflowed(30, 
			_("What time zone are you located in?"))

#
# disabling this for now
# 
#	self.label = Label(self.currentTime())
		
	self.l = Listbox(5, scroll = 1, returnExit = 0)

        for tz in timezones:
	    self.l.append(_(tz), tz)

	self.l.setCurrent(default)
#	self.l.setCallback(self.updateClock)
        
        # avoid breaking string freeze while still making it so that
        # we have the same string as in gui
        txt = _("System clock uses _UTC")
        txt = txt.replace("_", "")
        
	self.c = Checkbox(txt, isOn = asUtc)
#	self.c.setCallback(self.updateSysClock)

	self.g = GridFormHelp(screen, _("Time Zone Selection"), "timezone",
			      1, 5)
	self.g.add(t, 0, 0)
#	self.g.add(self.label, 0, 1, padding = (0, 1, 0, 0), anchorLeft = 1)
	self.g.add(self.c, 0, 2, padding = (0, 1, 0, 1), anchorLeft = 1)
	self.g.add(self.l, 0, 3, padding = (0, 0, 0, 1))
	self.g.add(bb, 0, 4, growx = 1)

# disabling for now
#	self.updateClock()
#	self.updateSysClock()
#
#	self.g.setTimer(500)
#
#	result = "TIMER"
#	while result == "TIMER":
#	    result = self.g.run()
#	    if result == "TIMER":
#		self.updateClock()

        result = ""
        while 1:
            result = self.g.run()
            rc = bb.buttonPressed (result)
            
            if rc == TEXT_BACK_CHECK:
                screen.popWindow()
                return INSTALL_BACK
            else:
                break

        screen.popWindow()
	timezone.setTimezoneInfo(self.l.current(), asUtc = self.c.selected())

	return INSTALL_OK


