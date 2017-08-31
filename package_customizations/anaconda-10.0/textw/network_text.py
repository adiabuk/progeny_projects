#
# network_text.py: text mode network configuration dialogs
#
# Jeremy Katz <katzj@redhat.com>
# Michael Fulbright <msf@redhat.com>
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

import iutil
import os
import isys
import string
from network import isPtpDev, anyUsingDHCP, sanityCheckIPString
from network import sanityCheckHostname
from snack import *
from constants_text import *
from rhpl.translate import _
from rhpl.log import log


def badIPDisplay(screen, the_ip):
    ButtonChoiceWindow(screen, _("Invalid IP string"),
                       _("The entered IP '%s' is not a valid IP.") %(the_ip,),
                       buttons = [ _("OK") ])
    return

class NetworkDeviceWindow:
    def setsensitive(self):
        if self.dhcpCb.selected ():
            sense = FLAGS_SET
        else:
            sense = FLAGS_RESET

        for n in self.entries.values():
            n.setFlags (FLAG_DISABLED, sense)

    def calcNM(self):
        ip = self.entries["ipaddr"].value()
        if ip and not self.entries["netmask"].value ():
            try:
                mask = "255.255.255.0"
            except ValueError:
                return

            self.entries["netmask"].set (mask)
        
    def runScreen(self, screen, network, dev, showonboot=1):
        boot = dev.get("bootproto")
        onboot = dev.get("onboot")

        devnames = self.devices.keys()
        devnames.sort()
        if devnames.index(dev.get("DEVICE")) == 0:
            onbootIsOn = 1
        else:
            onbootIsOn = (onboot == "yes")
        if not boot:
            boot = "dhcp"

	options = [(_("IP Address"), "ipaddr"),
		   (_("Netmask"),    "netmask")]
        if (isPtpDev(dev.info["DEVICE"])):
	    newopt = (_("Point to Point (IP)"), "remip")
	    options.append(newopt)

	descr = dev.get("desc")
	if descr is not None and len(descr) > 0:
	    toprows = 2
	else:
	    descr = None
	    toprows = 1

	topgrid = Grid(1, toprows)

        topgrid.setField(Label (_("Network Device: %s")
                                %(dev.info['DEVICE'],)),
                         0, 0, padding = (0, 0, 0, 0), anchorLeft = 1,
                         growx = 1)

	if descr is not None:
	    topgrid.setField(Label (_("Description: %s") % (descr[:70],)),
			     0, 1, padding = (0, 0, 0, 0), anchorLeft = 1,
			     growx = 1)

	botgrid = Grid(2, 2+len(options))
        self.dhcpCb = Checkbox(_("Configure using DHCP"),
                               isOn = (boot == "dhcp"))

	if not showonboot:
	    ypad = 1
	else:
	    ypad = 0

	currow = 0
        botgrid.setField(self.dhcpCb, 0, currow, anchorLeft = 1, growx = 1,
			 padding = (0, 0, 0, ypad))
	currow += 1
        
        self.onbootCb = Checkbox(_("Activate on boot"), isOn = onbootIsOn)
	if showonboot:
	    botgrid.setField(self.onbootCb, 0, currow, anchorLeft = 1, growx = 1,
			     padding = (0, 0, 0, 1))
	    currow += 1

	row = currow
        self.entries = {}
        for (name, opt) in options:
            botgrid.setField(Label(name), 0, row, anchorLeft = 1)

            entry = Entry (16)
            entry.set(dev.get(opt))
            botgrid.setField(entry, 1, row, padding = (1, 0, 0, 0))

            self.entries[opt] = entry
            row = row + 1

        self.dhcpCb.setCallback(self.setsensitive)
        self.entries["ipaddr"].setCallback(self.calcNM)

        bb = ButtonBar(screen, (TEXT_OK_BUTTON, TEXT_BACK_BUTTON))

        toplevel = GridFormHelp(screen, _("Network Configuration for %s") %
                                (dev.info['DEVICE']), 
                                "networkdev", 1, 4)

        toplevel.add(topgrid,  0, 0, (0, 0, 0, 1), anchorLeft = 1)
        toplevel.add(botgrid,  0, 1, (0, 0, 0, 1), anchorLeft = 1)
        toplevel.add(bb, 0, 3, growx = 1)

        self.setsensitive()
        
        while 1:
            result = toplevel.run()
            rc = bb.buttonPressed (result)

            if rc == TEXT_BACK_CHECK:
                screen.popWindow()
                return INSTALL_BACK

            if self.onbootCb.selected() != 0:
                dev.set(("onboot", "yes"))
            else:
                dev.unset("onboot")

            if self.dhcpCb.selected() != 0:
                dev.set(("bootproto", "dhcp"))
                dev.unset("ipaddr", "netmask", "network", "broadcast", "remip")
            else:
                ip = self.entries["ipaddr"].value()
                nm = self.entries["netmask"].value()
                try:
                    (net, bc) = isys.inet_calcNetBroad(ip, nm)
                except:
                    if self.onbootCb.selected() != 0:
                        ButtonChoiceWindow(screen, _("Invalid information"),
                                           _("You must enter valid IP "
                                             "information to continue"),
                                           buttons = [ _("OK") ])
                        continue
                    else:
                        net = ""
                        bc = ""

                dev.set(("bootproto", "static"))

                for val in self.entries.keys():
                    if self.entries[val].value():
                        dev.set((val, self.entries[val].value()))
                        
                if bc and net:
                    dev.set(("broadcast", bc), ("network", net))

            break

        screen.popWindow()
        return INSTALL_OK


    def __call__(self, screen, network, dir, intf, showonboot=1):

        self.devices = network.available()
        if not self.devices:
            return INSTALL_NOOP

        list = self.devices.keys()
        list.sort()
        devLen = len(list)
        if dir == 1:
            currentDev = 0
        else:
            currentDev = devLen - 1

        while currentDev < devLen and currentDev >= 0:
            rc = self.runScreen(screen, network,
                                self.devices[list[currentDev]],
                                showonboot)
            if rc == INSTALL_BACK:
                currentDev = currentDev - 1
            else:
                currentDev = currentDev + 1

        if currentDev < 0:
            return INSTALL_BACK
        else:
            return INSTALL_OK

class NetworkGlobalWindow:
    def getFirstGatewayGuess(self, devices):
        list = devices.keys()
        list.sort()
        for dev in list:
            thedev = devices[dev]
            bootproto = thedev.get("bootproto")
            if bootproto and bootproto == "dhcp":
                continue
            onboot = thedev.get("onboot")
            if onboot and onboot == "no":
                continue
            bcast = thedev.get("broadcast")
            if not bcast:
                continue
            return isys.inet_calcGateway(bcast)
        return ""
            
    def __call__(self, screen, network, dir, intf):
        devices = network.available()
        if not devices:
            return INSTALL_NOOP

        # we don't let you set gateway/dns if you've got any interfaces
        # using dhcp (for better or worse)
        if anyUsingDHCP(devices):
            return INSTALL_NOOP

        thegrid = Grid(2, 4)

        thegrid.setField(Label(_("Gateway:")), 0, 0, anchorLeft = 1)
        gwEntry = Entry(16)
        # if it's set already, use that... otherwise, get the first
        # non-dhcp and active device and use it to guess the gateway
        if network.gateway:
            gwEntry.set(network.gateway)
        else:
            gwEntry.set(self.getFirstGatewayGuess(devices))
        thegrid.setField(gwEntry, 1, 0, padding = (1, 0, 0, 0))
        
        thegrid.setField(Label(_("Primary DNS:")), 0, 1, anchorLeft = 1)
        ns1Entry = Entry(16)
        ns1Entry.set(network.primaryNS)
        thegrid.setField(ns1Entry, 1, 1, padding = (1, 0, 0, 0))
        
        thegrid.setField(Label(_("Secondary DNS:")), 0, 2, anchorLeft = 1)
        ns2Entry = Entry(16)
        ns2Entry.set(network.secondaryNS)
        thegrid.setField(ns2Entry, 1, 2, padding = (1, 0, 0, 0))
        
        thegrid.setField(Label(_("Tertiary DNS:")), 0, 3, anchorLeft = 1)
        ns3Entry = Entry(16)
        ns3Entry.set(network.ternaryNS)
        thegrid.setField(ns3Entry, 1, 3, padding = (1, 0, 0, 0))

        bb = ButtonBar (screen, (TEXT_OK_BUTTON, TEXT_BACK_BUTTON))

        toplevel = GridFormHelp (screen, _("Miscellaneous Network Settings"),
				 "miscnetwork", 1, 3)
        toplevel.add (thegrid, 0, 0, (0, 0, 0, 1), anchorLeft = 1)
        toplevel.add (bb, 0, 2, growx = 1)

        while 1:
            result = toplevel.run()
            rc = bb.buttonPressed (result)

            if rc == TEXT_BACK_CHECK:
                screen.popWindow()
                return INSTALL_BACK

            val = gwEntry.value()
            if val and sanityCheckIPString(val) is None:
                badIPDisplay(screen, val)
                continue
            network.gateway = val

            val = ns1Entry.value()
            if val and sanityCheckIPString(val) is None:
                badIPDisplay(screen, val)
                continue
            network.primaryNS = val

            val = ns2Entry.value()
            if val and sanityCheckIPString(val) is None:
                badIPDisplay(screen, val)
                continue
            network.secondaryNS = val

            val = ns3Entry.value()
            if val and sanityCheckIPString(val) is None:
                badIPDisplay(screen, val)
                continue
            network.ternaryNS = val
            break

        screen.popWindow()        
        return INSTALL_OK
        

class HostnameWindow:
    def hostTypeCb(self, (radio, hostEntry)):
        if radio.getSelection() != "manual":
            sense = FLAGS_SET
        else:
            sense = FLAGS_RESET

        hostEntry.setFlags(FLAG_DISABLED, sense)
            
    def __call__(self, screen, network, dir, intf):
        devices = network.available ()
        if not devices:
            return INSTALL_NOOP

        # figure out if the hostname is currently manually set
        if anyUsingDHCP(devices):
            if (network.hostname != "localhost.localdomain" and
                network.overrideDHCPhostname):
                manual = 1
            else:
                manual = 0
        else:
            manual = 1

        thegrid = Grid(2, 2)
        radio = RadioGroup()
        autoCb = radio.add(_("automatically via DHCP"), "dhcp",
                                not manual)
        thegrid.setField(autoCb, 0, 0, growx = 1, anchorLeft = 1)

        manualCb = radio.add(_("manually"), "manual", manual)
        thegrid.setField(manualCb, 0, 1, anchorLeft = 1)
        hostEntry = Entry(24)
        if network.hostname != "localhost.localdomain":
            hostEntry.set(network.hostname)
        thegrid.setField(hostEntry, 1, 1, padding = (1, 0, 0, 0),
                         anchorLeft = 1)            

        # disable the dhcp if we don't have any dhcp
        if anyUsingDHCP(devices):
            autoCb.w.checkboxSetFlags(FLAG_DISABLED, FLAGS_RESET)            
        else:
            autoCb.w.checkboxSetFlags(FLAG_DISABLED, FLAGS_SET)

        self.hostTypeCb((radio, hostEntry))

        autoCb.setCallback(self.hostTypeCb, (radio, hostEntry))
        manualCb.setCallback(self.hostTypeCb, (radio, hostEntry))

        toplevel = GridFormHelp(screen, _("Hostname Configuration"),
                                "hostname", 1, 4)
        text = TextboxReflowed(55,
                               _("If your system is part of a larger network "
                                 "where hostnames are assigned by DHCP, "
                                 "select automatically via DHCP. Otherwise, "
                                 "select manually and enter in a hostname for "
                                 "your system. If you do not, your system "
                                 "will be known as 'localhost.'"))
        toplevel.add(text, 0, 0, (0, 0, 0, 1))

        bb = ButtonBar(screen, (TEXT_OK_BUTTON, TEXT_BACK_BUTTON))
        toplevel.add(thegrid, 0, 1, padding = (0, 0, 0, 1))
        toplevel.add(bb, 0, 2, growx = 1)

        while 1:
            result = toplevel.run()
            rc = bb.buttonPressed(result)
            
            if rc == TEXT_BACK_CHECK:
                screen.popWindow()
                return INSTALL_BACK

            if radio.getSelection() != "manual":
                network.overrideDHCPhostname = 0
                network.hostname = "localhost.localdomain"
            else:
                hname = string.strip(hostEntry.value())
                if len(hname) == 0:
                    ButtonChoiceWindow(screen, _("Invalid Hostname"),
                                       _("You have not specified a hostname."),
                                       buttons = [ _("OK") ])
                    continue
                neterrors = sanityCheckHostname(hname)
                if neterrors is not None:
                    ButtonChoiceWindow(screen, _("Invalid Hostname"),
                                       _("The hostname \"%s\" is not valid "
                                         "for the following reason:\n\n%s")
                                       %(hname, neterrors),
                                       buttons = [ _("OK") ])
                    continue

                network.overrideDHCPhostname = 1
                network.hostname = hname
            break

        screen.popWindow()
        return INSTALL_OK
            

            

        
