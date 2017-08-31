#
# users.py - user account install data
#
# Matt Wilson <msw@redhat.com>
# Brent Fox <bfox@redhat.com>
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
import whrandom
import crypt
import os
import string
from flags import flags

from rhpl.log import log

class Accounts:
    def __repr__(self):
	return "<Type Accounts>"

    def __str__(self):
	return "<Type Accounts>"

    # List of (accountName, fullName, password) tupes
    def setUserList(self, users):
	self.users = users

    def getUserList(self):
	return self.users

    def writeKScommands(self, f, auth):
	for (account, name, password) in self.users:
	    crypted = cryptPassword(password, auth.useMD5)

	    f.write("/usr/sbin/useradd %s\n" % (account));
	    f.write("chfn -f '%s' %s\n" % (name, account))
	    f.write("/usr/sbin/usermod -p '%s' %s\n" % (crypted, account))
	    f.write("\n")

    def write(self, instPath, auth):
	if not self.users: return

        if not flags.setupFilesystems:
            return

	for (account, name, password) in self.users:
	    argv = [ "/usr/sbin/useradd", account ]
	    iutil.execWithRedirect(argv[0], argv, root = instPath,
				   stdout = None)

	    argv = [ "/usr/bin/chfn", "-f", name, account]
	    iutil.execWithRedirect(argv[0], argv, root = instPath,
				   stdout = None)
	
	    setPassword(instPath, account, password, auth.useMD5)

    def __init__(self):
	self.users = []

class Password:
    def __init__ (self):
        self.crypt = None
	self.pure = None

    def getPure(self):
	return self.pure

    def set (self, password, isCrypted = 0):
	if isCrypted:
	    self.crypt = password
	    self.pure = None
	else:
            salt = (whrandom.choice (string.letters +
                                     string.digits + './') + 
                    whrandom.choice (string.letters +
                                     string.digits + './'))
            self.crypt = crypt.crypt (password, salt)
	    self.pure = password

    def getCrypted(self):
	return self.crypt

class RootPassword(Password):
    def __repr__(self):
	return "<Type RootPassword>"

    def __str__(self):
	return "<Type RootPassword>"

    def write(self, instPath, auth):
	pure = self.getPure()
	if pure:
	    setPassword(instPath, "root", pure, auth.useMD5)
	else:
	    setPassword(instPath, "root", self.getCrypted (),
                        auth.useMD5, alreadyCrypted = 1)

    def writeKS(self, f, auth):
        pure = self.getPure()
        if pure:
            f.write("rootpw --iscrypted %s\n" %(cryptPassword(pure, auth.useMD5)))
        else:
            f.write("rootpw --iscrypted %s\n" %(self.getCrypted()))

def cryptPassword(password, useMD5):
    if useMD5:
	salt = "$1$"
	saltLen = 8
    else:
	salt = ""
	saltLen = 2

    for i in range(saltLen):
	salt = salt + whrandom.choice (string.letters +
                                       string.digits + './')

    return crypt.crypt (password, salt)

def setPassword(instPath, account, password, useMD5, alreadyCrypted = 0):
    if not alreadyCrypted:
	password = cryptPassword(password, useMD5)

    devnull = os.open("/dev/null", os.O_RDWR)

    argv = [ "/usr/sbin/usermod", "-p", password, account ]
    iutil.execWithRedirect(argv[0], argv, root = instPath, 
			   stdout = '/dev/null', stderr = None)
    os.close(devnull)

class Authentication:
    def __init__ (self):
        self.useShadow = 1
        self.useMD5 = 1

        self.useNIS = 0
        self.nisDomain = ""
        self.nisuseBroadcast = 1
        self.nisServer = ""

        self.useLdap = 0
        self.useLdapauth = 0
        self.ldapServer = ""
        self.ldapBasedn = ""
        self.ldapTLS = ""

        self.useKrb5 = 0
        self.krb5Realm = ""
        self.krb5Kdc = ""
        self.krb5Admin = ""

        self.useHesiod = 0
        self.hesiodLhs = ""
        self.hesiodRhs = ""

        self.useSamba = 0
        self.sambaServer = ""
        self.sambaWorkgroup = ""

        self.enableCache = 0

    def writeKS(self, f):
	f.write("authconfig")
	for arg in self.getArgList():
	    if arg[0:9] != "--disable":
		f.write(" " + arg)
	f.write("\n")

    def getArgList(self):
	args = []

        if self.useShadow:
            args.append ("--enableshadow")
        else:
            args.append ("--disableshadow")

        if self.useMD5:
            args.append ("--enablemd5")
        else:
            args.append ("--disablemd5")

        if self.enableCache:
            args.append("--enablecache")
        else:
            args.append("--disablecache")

        if self.useNIS:
            args.append ("--enablenis")
            args.append ("--nisdomain")
            args.append (self.nisDomain)
            if not self.nisuseBroadcast:
                args.append ("--nisserver")
                args.append (self.nisServer)
        else:
            args.append ("--disablenis")

        if self.useLdap:
            args.append ("--enableldap")
        else:
            args.append ("--disableldap")
        if self.useLdapauth:
            args.append ("--enableldapauth")
        else:
            args.append ("--disableldapauth")
        if self.useLdap or self.useLdapauth:
            args.append ("--ldapserver")
            args.append (self.ldapServer)
            args.append ("--ldapbasedn")
            args.append (self.ldapBasedn)
        if self.ldapTLS:
            args.append ("--enableldaptls")
        else:
            args.append ("--disableldaptls")

        if self.useKrb5:
            args.append ("--enablekrb5")
            args.append ("--krb5realm")
            args.append (self.krb5Realm)
            args.append ("--krb5kdc")
            args.append (self.krb5Kdc)
            args.append ("--krb5adminserver")
            args.append (self.krb5Admin)
        else:
	    args.append("--disablekrb5")

        if self.useHesiod:
            args.append ("--enablehesiod")
            args.append ("--hesiodlhs")
            args.append (self.hesiodLhs)
            args.append ("--hesiodrhs")
            args.append (self.hesiodRhs)
        else:
	    args.append("--disablehesiod")

        if self.useSamba:
            args.append ("--enablesmbauth")
            args.append ("--smbservers")
            args.append (self.sambaServer)
            args.append ("--smbworkgroup")
            args.append (self.sambaWorkgroup)
        else:
	    args.append("--disablesmbauth")

	return args
 
    def write (self, instPath):
        args = [ "/usr/sbin/authconfig", "--kickstart", "--nostart" ]
	args = args + self.getArgList()

        try:
            if flags.setupFilesystems:
                iutil.execWithRedirect(args[0], args,
                                       stdout = None, stderr = None,
                                       searchPath = 1,
                                       root = instPath)
            else:
                log("Would have run %s", args)
        except RuntimeError, msg:
            log ("Error running %s: %s", args, msg)

