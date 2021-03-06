#ifndef LOADER_H
#define LOADER_H

#define LOADER_OK 0
#define LOADER_BACK 1
#define LOADER_NOOP 2
#define LOADER_ERROR -1


#define LOADER_FLAGS_TESTING		(1 << 0)
#define LOADER_FLAGS_EXPERT		(1 << 1)
#define LOADER_FLAGS_TEXT		(1 << 2)
#define LOADER_FLAGS_RESCUE		(1 << 3)
#define LOADER_FLAGS_KICKSTART		(1 << 4)
#define LOADER_FLAGS_KICKSTART_SEND_MAC	(1 << 5)
#define LOADER_FLAGS_NOPROBE		(1 << 7)
#define LOADER_FLAGS_MODDISK		(1 << 8)
#define LOADER_FLAGS_ISA		(1 << 9)
#define LOADER_FLAGS_SERIAL		(1 << 10)
#define LOADER_FLAGS_UPDATES		(1 << 11)
#define LOADER_FLAGS_KSFILE		(1 << 12)
#define LOADER_FLAGS_NOUSB              (1 << 16)
#define LOADER_FLAGS_NOSHELL            (1 << 17)
#define LOADER_FLAGS_NOPCMCIA           (1 << 18)
#define LOADER_FLAGS_TELNETD	        (1 << 19)
#define LOADER_FLAGS_NOPASS	        (1 << 20)
#define LOADER_FLAGS_MEDIACHECK         (1 << 22)
#define LOADER_FLAGS_NOUSBSTORAGE       (1 << 23)
#define LOADER_FLAGS_ASKMETHOD          (1 << 24)
#define LOADER_FLAGS_NOPARPORT          (1 << 25)
#define LOADER_FLAGS_NOIEEE1394         (1 << 26)
#define LOADER_FLAGS_NOFB		(1 << 27)
#define LOADER_FLAGS_CMDLINE            (1 << 28)
#define LOADER_FLAGS_GRAPHICAL		(1 << 29)
/* FIXME: this should go away */
#define LOADER_FLAGS_ENABLECDDMA       	(1 << 13)
#define LOADER_FLAGS_SELINUX            (1 << 14)

#define FL_TESTING(a)	    ((a) & LOADER_FLAGS_TESTING)
#define FL_EXPERT(a)	    ((a) & LOADER_FLAGS_EXPERT)
#define FL_TEXT(a)	    ((a) & LOADER_FLAGS_TEXT)
#define FL_RESCUE(a)	    ((a) & LOADER_FLAGS_RESCUE)
#define FL_KICKSTART(a)	    ((a) & LOADER_FLAGS_KICKSTART)
#define FL_KICKSTART_SEND_MAC(a) ((a) & LOADER_FLAGS_KICKSTART_SEND_MAC)
#define FL_NOPROBE(a)	    ((a) & LOADER_FLAGS_NOPROBE)
#define FL_MODDISK(a)	    ((a) & LOADER_FLAGS_MODDISK)
#define FL_ISA(a)	    ((a) & LOADER_FLAGS_ISA)
#define FL_SERIAL(a)	    ((a) & LOADER_FLAGS_SERIAL)
#define FL_UPDATES(a)	    ((a) & LOADER_FLAGS_UPDATES)
#define FL_KSFILE(a)	    ((a) & LOADER_FLAGS_KSFILE)
#define FL_NOUSB(a)	    ((a) & LOADER_FLAGS_NOUSB)
#define FL_NOSHELL(a)	    ((a) & LOADER_FLAGS_NOSHELL)
#define FL_NOFB(a)          ((a) & LOADER_FLAGS_NOFB)
#define FL_NOPCMCIA(a)	    ((a) & LOADER_FLAGS_NOPCMCIA)
#define FL_RESCUE_NOMOUNT(a) ((a) & LOADER_FLAGS_RESCUE_NOMOUNT)
#define FL_TELNETD(a)	    ((a) & LOADER_FLAGS_TELNETD)
#define FL_NOPASS(a)	    ((a) & LOADER_FLAGS_NOPASS)
#define FL_MEDIACHECK(a)    ((a) & LOADER_FLAGS_MEDIACHECK)
#define FL_NOUSBSTORAGE(a)  ((a) & LOADER_FLAGS_NOUSBSTORAGE)
#define FL_ASKMETHOD(a)     ((a) & LOADER_FLAGS_ASKMETHOD)
#define FL_NOPARPORT(a)     ((a) & LOADER_FLAGS_NOPARPORT)
#define FL_NOIEEE1394(a)    ((a) & LOADER_FLAGS_NOIEEE1394)
#define FL_NOFB(a)	    ((a) & LOADER_FLAGS_NOFB)
#define FL_GRAPHICAL(a)	    ((a) & LOADER_FLAGS_GRAPHICAL)
#define FL_CMDLINE(a)	    ((a) & LOADER_FLAGS_CMDLINE)
/* FIXME: this should go away */
#define FL_ENABLECDDMA(a)   ((a) & LOADER_FLAGS_ENABLECDDMA)
#define FL_SELINUX(a)       ((a) & LOADER_FLAGS_SELINUX)


void startNewt(int flags);
void stopNewt();
char * getProductName(void);
char * getProductPath(void);

#include "modules.h"
#include "moduledeps.h"
/* JKFIXME: I don't like all of the _set attribs, but without them,
 * we can't tell if it was explicitly set by kickstart/cmdline or 
 * if we just got it going through the install.   */
struct loaderData_s {
    char * lang;
    int lang_set;
    char * kbd;
    int kbd_set;
    char * netDev;
    int netDev_set;
    char * netCls;
    int netCls_set;
    char * ip, * netmask, *gateway, *dns, *hostname, *ptpaddr, *ethtool;
    int mtu;
    int noDns;
    int ipinfo_set;
    char * ksFile;
    char * method;
    char * ddsrc;
    void * methodData;

    moduleList modLoaded;
    moduleDeps * modDepsPtr;
    moduleInfoSet modInfo;
};

/* 64 bit platforms, definitions courtesy of glib */
#if defined (__x86_64__) || defined(__ia64__) || defined(__alpha__) || defined(__powerpc64__) || defined(__sparc64__) || defined(__s390x__)
#define POINTER_TO_INT(p)  ((int) (long) (p))
#define INT_TO_POINTER(i)  ((void *) (long) (i))
#else
#define POINTER_TO_INT(p)  ((int) (p))
#define INT_TO_POINTER(i)  ((void *) (i))
#endif

/* library paths */
#if defined(__x86_64__) || defined(__s390x__) || defined(__ppc64__)
#define LIBPATH "/lib64:/usr/lib64:/usr/X11R6/lib64:/usr/kerberos/lib64:/mnt/usr/lib64:/mnt/sysimage/lib64:/mnt/sysimage/usr/lib64"
#else
#define LIBPATH "/lib:/usr/lib:/usr/X11R6/lib:/usr/kerberos/lib:/mnt/usr/lib:/mnt/sysimage/lib:/mnt/sysimage/usr/lib"
#endif


#endif
