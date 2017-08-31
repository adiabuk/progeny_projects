ExcludeArch: ppc64
Name: anaconda
Version: 10.0
Release: 5
License: GPL
Summary: Graphical system installer
Group: Applications/System
Source: anaconda-%{PACKAGE_VERSION}.tar.bz2
BuildPreReq: pump-devel >= 0.8.20, kudzu-devel >= 1.1.52, pciutils-devel, bzip2-devel, e2fsprogs-devel, python-devel gtk2-devel rpm-python >= 4.2-0.61, newt-devel, rpm-devel, gettext >= 0.11, rhpl, booty, libxml2-python, zlib-devel, bogl-devel >= 0:0.1.9-17, bogl-bterm >= 0:0.1.9-17, elfutils-devel, beecrypt-devel, libselinux-devel >= 1.6
%ifarch i386
BuildRequires: dietlibc
%endif
Requires: rpm-python >= 4.2-0.61, rhpl > 0.63, parted >= 1.6.3-7, booty, kudzu
Requires: pyparted
Url: http://rhlinux.redhat.com/anaconda/

BuildRoot: %{_tmppath}/anaconda-%{PACKAGE_VERSION}

%description
The anaconda package contains the program which was used to install your 
system.  These files are of little use on an already installed system.

%package runtime
Summary: Red Hat Linux installer portions needed only for fresh installs.
Group: Applications/System
AutoReqProv: false
Requires: libxml2-python

%description runtime
The anaconda-runtime package contains parts of the installation system which 
are needed for installing new systems.  These files are used to build media 
sets, but are not meant for use on already installed systems.

%prep

%setup -q

%build
make depend
make RPM_OPT_FLAGS="$RPM_OPT_FLAGS"

%install
rm -rf $RPM_BUILD_ROOT
make DESTDIR=$RPM_BUILD_ROOT install
#strip $RPM_BUILD_ROOT/usr/sbin/ddcprobe

strip $RPM_BUILD_ROOT/usr/lib/anaconda/*.so

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%doc COPYING
%doc docs/command-line.txt
%doc docs/install-methods.txt
%doc docs/kickstart-docs.txt
%doc docs/kickstart-docs.html
%doc docs/mediacheck.txt
%doc docs/anaconda-release-notes.txt
/usr/bin/mini-wm
/usr/sbin/anaconda
/usr/share/anaconda
/usr/share/locale/*/*/*
/usr/lib/anaconda

%files runtime
%defattr(-,root,root)
/usr/lib/anaconda-runtime

%triggerun -- anaconda < 8.0-1
/sbin/chkconfig --del reconfig >/dev/null 2>&1 || :

%define date    %(echo `LC_ALL="C" date +"%a %b %d %Y"`)

%changelog
* %{date} Anaconda team <bugzilla@redhat.com>
- built new version from CVS

* Fri Apr 30 2004 Jeremy Katz <katzj@redhat.com>
- Update description, remove prereq on stuff that was only needed 
  for reconfig mode 

* Tue Feb 24 2004 Jeremy Katz <katzj@redhat.com>
- buildrequire libselinux-devel

* Thu Nov  6 2003 Jeremy Katz <katzj@redhat.com>
- require booty (#109272)

* Tue Oct  8 2002 Jeremy Katz <katzj@redhat.com>
- back to mainstream rpm instead of rpm404

* Mon Sep  9 2002 Jeremy Katz <katzj@redhat.com>
- can't buildrequire dietlibc and kernel-pcmcia-cs since they don't always
  exist

* Wed Aug 21 2002 Jeremy Katz <katzj@redhat.com>
- added URL

* Thu May 23 2002 Jeremy Katz <katzj@redhat.com>
- add require and buildrequire on rhpl

* Tue Apr 02 2002 Michael Fulbright <msf@redhat.com>
- added some more docs

* Fri Feb 22 2002 Jeremy Katz <katzj@redhat.com>
- buildrequire kernel-pcmcia-cs as we've sucked the libs the loader needs 
  to there now

* Thu Feb 07 2002 Michael Fulbright <msf@redhat.com>
- goodbye reconfig

* Thu Jan 31 2002 Jeremy Katz <katzj@redhat.com>
- update the BuildRequires a bit

* Fri Jan  4 2002 Jeremy Katz <katzj@redhat.com>
- ddcprobe is now done from kudzu

* Wed Jul 18 2001 Jeremy Katz <katzj@redhat.com>
- own /usr/lib/anaconda and /usr/share/anaconda

* Fri Jan 12 2001 Matt Wilson <msw@redhat.com>
- sync text with specspo

* Thu Aug 10 2000 Matt Wilson <msw@redhat.com>
- build on alpha again now that I've fixed the stubs

* Wed Aug  9 2000 Michael Fulbright <drmike@redhat.com>
- new build

* Fri Aug  4 2000 Florian La Roche <Florian.LaRoche@redhat.com>
- allow also subvendorid and subdeviceid in trimpcitable

* Fri Jul 14 2000 Matt Wilson <msw@redhat.com>
- moved init script for reconfig mode to /etc/init.d/reconfig
- move the initscript back to /etc/rc.d/init.d
- Prereq: /etc/init.d

* Thu Feb 03 2000 Michael Fulbright <drmike@redhat.com>
- strip files
- add lang-table to file list

* Wed Jan 05 2000 Michael Fulbright <drmike@redhat.com>
- added requirement for rpm-python

* Mon Dec 06 1999 Michael Fulbright <drmike@redhat.com>
- rename to 'anaconda' instead of 'anaconda-reconfig'

* Fri Dec 03 1999 Michael Fulbright <drmike@redhat.com>
- remove ddcprobe since we don't do X configuration in reconfig now

* Tue Nov 30 1999 Michael Fulbright <drmike@redhat.com>
- first try at packaging reconfiguration tool

