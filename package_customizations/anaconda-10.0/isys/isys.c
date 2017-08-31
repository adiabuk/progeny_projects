#include <Python.h>

#include <stdio.h>
#include <dirent.h>
#include <errno.h>
#include <linux/ext2_fs.h>
#include <linux/ext3_fs.h>
#include <ext2fs/ext2fs.h>
#include <fcntl.h>
#include <popt.h>
/* Need to tell loop.h what the actual dev_t type is. */
#undef dev_t
#if defined(__alpha) || (defined(__sparc__) && defined(__arch64__))
#define dev_t unsigned int
#else
#if defined(__x86_64__)
#define dev_t unsigned long
#else
#define dev_t unsigned short
#endif
#endif
#include <linux/loop.h>
#undef dev_t
#define dev_t dev_t
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/time.h>
#include <sys/utsname.h>
#include <sys/vfs.h>
#include <unistd.h>
#include <resolv.h>
#include <pump.h>
#include <scsi/scsi.h>
#include <scsi/scsi_ioctl.h>
#include <sys/vt.h>
#include <sys/types.h>
#include <linux/hdreg.h>
#include <linux/fb.h>
#include <libintl.h>
#include <selinux/selinux.h>

#include "md-int.h"
#include "imount.h"
#include "isys.h"
#include "net.h"
#include "smp.h"
#include "lang.h"
#include "getmacaddr.h"

#ifndef CDROMEJECT
#define CDROMEJECT 0x5309
#endif

static PyObject * doGetOpt(PyObject * s, PyObject * args);
/*static PyObject * doInsmod(PyObject * s, PyObject * args);
static PyObject * doRmmod(PyObject * s, PyObject * args);*/
static PyObject * doMount(PyObject * s, PyObject * args);
static PyObject * doUMount(PyObject * s, PyObject * args);
static PyObject * makeDevInode(PyObject * s, PyObject * args);
static PyObject * pyMakeDev(PyObject * s, PyObject * args);
static PyObject * doMknod(PyObject * s, PyObject * args);
static PyObject * smpAvailable(PyObject * s, PyObject * args);
static PyObject * htAvailable(PyObject * s, PyObject * args);
static PyObject * summitAvailable(PyObject * s, PyObject * args);
static PyObject * doCheckBoot(PyObject * s, PyObject * args);
static PyObject * doSwapon(PyObject * s, PyObject * args);
static PyObject * doSwapoff(PyObject * s, PyObject * args);
static PyObject * doPoptParse(PyObject * s, PyObject * args);
static PyObject * doFbconProbe(PyObject * s, PyObject * args);
static PyObject * doLoSetup(PyObject * s, PyObject * args);
static PyObject * doUnLoSetup(PyObject * s, PyObject * args);
static PyObject * doLoChangeFd(PyObject * s, PyObject * args);
static PyObject * doDdFile(PyObject * s, PyObject * args);
static PyObject * doGetRaidSuperblock(PyObject * s, PyObject * args);
static PyObject * doGetRaidChunkSize(PyObject * s, PyObject * args);
static PyObject * doDevSpaceFree(PyObject * s, PyObject * args);
static PyObject * doRaidStart(PyObject * s, PyObject * args);
static PyObject * doRaidStop(PyObject * s, PyObject * args);
static PyObject * doConfigNetDevice(PyObject * s, PyObject * args);
static PyObject * doPumpNetDevice(PyObject * s, PyObject * args);
static PyObject * doResetResolv(PyObject * s, PyObject * args);
static PyObject * doSetResolvRetry(PyObject * s, PyObject * args);
static PyObject * doLoadFont(PyObject * s, PyObject * args);
static PyObject * doLoadKeymap(PyObject * s, PyObject * args);
static PyObject * doReadE2fsLabel(PyObject * s, PyObject * args);
static PyObject * doExt2Dirty(PyObject * s, PyObject * args);
static PyObject * doExt2HasJournal(PyObject * s, PyObject * args);
static PyObject * doIsScsiRemovable(PyObject * s, PyObject * args);
static PyObject * doIsIdeRemovable(PyObject * s, PyObject * args);
static PyObject * doEjectCdrom(PyObject * s, PyObject * args);
static PyObject * doVtActivate(PyObject * s, PyObject * args);
static PyObject * doisPsudoTTY(PyObject * s, PyObject * args);
static PyObject * doisVioConsole(PyObject * s);
static PyObject * doSync(PyObject * s, PyObject * args);
static PyObject * doisIsoImage(PyObject * s, PyObject * args);
static PyObject * dogetGeometry(PyObject * s, PyObject * args);
static PyObject * getFramebufferInfo(PyObject * s, PyObject * args);
static PyObject * printObject(PyObject * s, PyObject * args);
static PyObject * doGetPageSize(PyObject * s, PyObject * args);
static PyObject * py_bind_textdomain_codeset(PyObject * o, PyObject * args);
static PyObject * getLinkStatus(PyObject * s, PyObject * args);
static PyObject * hasIdeRaidMagic(PyObject * s, PyObject * args);
static PyObject * start_bterm(PyObject * s, PyObject * args);
static PyObject * py_getDasdPorts(PyObject * s, PyObject * args);
static PyObject * py_isUsableDasd(PyObject * s, PyObject * args);
static PyObject * py_isLdlDasd(PyObject * s, PyObject * args);
static PyObject * doGetMacAddress(PyObject * s, PyObject * args);
static PyObject * doGetIPAddress(PyObject * s, PyObject * args);
static PyObject * doResetFileContext(PyObject * s, PyObject * args);

static PyMethodDef isysModuleMethods[] = {
    { "ejectcdrom", (PyCFunction) doEjectCdrom, METH_VARARGS, NULL },
    { "e2dirty", (PyCFunction) doExt2Dirty, METH_VARARGS, NULL },
    { "e2hasjournal", (PyCFunction) doExt2HasJournal, METH_VARARGS, NULL },
    { "e2fslabel", (PyCFunction) doReadE2fsLabel, METH_VARARGS, NULL },
    { "devSpaceFree", (PyCFunction) doDevSpaceFree, METH_VARARGS, NULL },
    { "raidstop", (PyCFunction) doRaidStop, METH_VARARGS, NULL },
    { "raidstart", (PyCFunction) doRaidStart, METH_VARARGS, NULL },
    { "getraidsb", (PyCFunction) doGetRaidSuperblock, METH_VARARGS, NULL },
    { "getraidchunk", (PyCFunction) doGetRaidChunkSize, METH_VARARGS, NULL },
    { "lochangefd", (PyCFunction) doLoChangeFd, METH_VARARGS, NULL },
    { "losetup", (PyCFunction) doLoSetup, METH_VARARGS, NULL },
    { "unlosetup", (PyCFunction) doUnLoSetup, METH_VARARGS, NULL },
    { "ddfile", (PyCFunction) doDdFile, METH_VARARGS, NULL },
    { "getopt", (PyCFunction) doGetOpt, METH_VARARGS, NULL },
    { "poptParseArgv", (PyCFunction) doPoptParse, METH_VARARGS, NULL },
    { "mkdevinode", (PyCFunction) makeDevInode, METH_VARARGS, NULL },
    { "makedev", (PyCFunction) pyMakeDev, METH_VARARGS, NULL },
    { "mknod", (PyCFunction) doMknod, METH_VARARGS, NULL },
    { "mount", (PyCFunction) doMount, METH_VARARGS, NULL },
    { "smpavailable", (PyCFunction) smpAvailable, METH_VARARGS, NULL },
    { "htavailable", (PyCFunction) htAvailable, METH_VARARGS, NULL },
    { "summitavailable", (PyCFunction) summitAvailable, METH_VARARGS, NULL },
    { "umount", (PyCFunction) doUMount, METH_VARARGS, NULL },
    { "confignetdevice", (PyCFunction) doConfigNetDevice, METH_VARARGS, NULL },
    { "pumpnetdevice", (PyCFunction) doPumpNetDevice, METH_VARARGS, NULL },
    { "checkBoot", (PyCFunction) doCheckBoot, METH_VARARGS, NULL },
    { "swapon",  (PyCFunction) doSwapon, METH_VARARGS, NULL },
    { "swapoff",  (PyCFunction) doSwapoff, METH_VARARGS, NULL },
    { "fbconprobe", (PyCFunction) doFbconProbe, METH_VARARGS, NULL },
    { "resetresolv", (PyCFunction) doResetResolv, METH_VARARGS, NULL },
    { "setresretry", (PyCFunction) doSetResolvRetry, METH_VARARGS, NULL },
    { "loadFont", (PyCFunction) doLoadFont, METH_VARARGS, NULL },
    { "loadKeymap", (PyCFunction) doLoadKeymap, METH_VARARGS, NULL },
    { "isScsiRemovable", (PyCFunction) doIsScsiRemovable, METH_VARARGS, NULL},
    { "isIdeRemovable", (PyCFunction) doIsIdeRemovable, METH_VARARGS, NULL},
    { "vtActivate", (PyCFunction) doVtActivate, METH_VARARGS, NULL},
    { "isPsudoTTY", (PyCFunction) doisPsudoTTY, METH_VARARGS, NULL},
    { "isVioConsole", (PyCFunction) doisVioConsole, METH_NOARGS, NULL},
    { "sync", (PyCFunction) doSync, METH_VARARGS, NULL},
    { "isisoimage", (PyCFunction) doisIsoImage, METH_VARARGS, NULL},
    { "getGeometry", (PyCFunction) dogetGeometry, METH_VARARGS, NULL},
    { "fbinfo", (PyCFunction) getFramebufferInfo, METH_VARARGS, NULL},
    { "getpagesize", (PyCFunction) doGetPageSize, METH_VARARGS, NULL},
    { "printObject", (PyCFunction) printObject, METH_VARARGS, NULL},
    { "bind_textdomain_codeset", (PyCFunction) py_bind_textdomain_codeset, METH_VARARGS, NULL},
    { "getLinkStatus", (PyCFunction) getLinkStatus, METH_VARARGS, NULL },
    { "hasIdeRaidMagic", (PyCFunction) hasIdeRaidMagic, METH_VARARGS, NULL },
    { "startBterm", (PyCFunction) start_bterm, METH_VARARGS, NULL },
    { "getDasdPorts", (PyCFunction) py_getDasdPorts, METH_VARARGS, NULL},
    { "isUsableDasd", (PyCFunction) py_isUsableDasd, METH_VARARGS, NULL},
    { "isLdlDasd", (PyCFunction) py_isLdlDasd, METH_VARARGS, NULL},
    { "getMacAddress", (PyCFunction) doGetMacAddress, METH_VARARGS, NULL},
    { "getIPAddress", (PyCFunction) doGetIPAddress, METH_VARARGS, NULL},
    { "resetFileContext", (PyCFunction) doResetFileContext, METH_VARARGS, NULL },
    { NULL }
} ;

static PyObject * pyMakeDev(PyObject * s, PyObject * args) {
    int major, minor;

    if (!PyArg_ParseTuple(args, "ii", &major, &minor)) return NULL;
    return Py_BuildValue("i", makedev(major, minor));
}

static PyObject * makeDevInode(PyObject * s, PyObject * args) {
    char * devName, * where;

    if (!PyArg_ParseTuple(args, "ss", &devName, &where)) return NULL;

    switch (devMakeInode(devName, where)) {
      case -1:
	PyErr_SetString(PyExc_TypeError, "unknown device");
      case -2:
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doMknod(PyObject * s, PyObject * args) {
    char * pathname;
    int mode, dev;

    if (!PyArg_ParseTuple(args, "sii", &pathname, &mode, &dev)) return NULL;

    if (mknod(pathname, mode, dev)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doDdFile(PyObject * s, PyObject * args) {
    int fd;
    int megs;
    char * ptr;
    int i;

    if (!PyArg_ParseTuple(args, "ii", &fd, &megs)) return NULL;

    ptr = calloc(1024 * 256, 1);

    while (megs--) {
	for (i = 0; i < 4; i++) {
	    if (write(fd, ptr, 1024 * 256) != 1024 * 256) {
		PyErr_SetFromErrno(PyExc_SystemError);
		free(ptr);
		return NULL;
	    }
	    sync();
	}
    }

    free(ptr);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doUnLoSetup(PyObject * s, PyObject * args) {
    int loopfd;

    if (!PyArg_ParseTuple(args, "i", &loopfd)) return NULL;
    if (ioctl(loopfd, LOOP_CLR_FD, 0)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* XXX - msw */
#ifndef LOOP_CHANGE_FD
#define LOOP_CHANGE_FD	0x4C06
#endif

static PyObject * doLoChangeFd(PyObject * s, PyObject * args) {
    int loopfd;
    int targfd;

    if (!PyArg_ParseTuple(args, "ii", &loopfd, &targfd)) 
	return NULL;
    if (ioctl(loopfd, LOOP_CHANGE_FD, targfd)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doLoSetup(PyObject * s, PyObject * args) {
    int loopfd;
    int targfd;
    struct loop_info loopInfo;
    char * loopName;

    if (!PyArg_ParseTuple(args, "iis", &loopfd, &targfd, &loopName)) 
	return NULL;
    if (ioctl(loopfd, LOOP_SET_FD, targfd)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    memset(&loopInfo, 0, sizeof(loopInfo));
    strcpy(loopInfo.lo_name, loopName);

    if (ioctl(loopfd, LOOP_SET_STATUS, &loopInfo)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doGetOpt(PyObject * s, PyObject * pyargs) {
    PyObject * argList, * longArgs, * strObject;
    PyObject * retList, * retArgs;
    char * shortArgs;
    struct poptOption * options;
    int numOptions, i, rc;
    char * ch;
    poptContext optCon;
    char * str;
    char * error;
    const char ** argv;
    char strBuf[3];

    if (!PyArg_ParseTuple(pyargs, "OsO", &argList, &shortArgs, &longArgs)) 
	return NULL;

    if (!(PyList_Check(argList))) {
	PyErr_SetString(PyExc_TypeError, "list expected");
    }
    if (!(PyList_Check(longArgs))) {
	PyErr_SetString(PyExc_TypeError, "list expected");
    }

    numOptions = PyList_Size(longArgs);
    for (ch = shortArgs; *ch; ch++)
	if (*ch != ':') numOptions++;

    options = alloca(sizeof(*options) * (numOptions + 1));

    ch = shortArgs;
    numOptions = 0;
    while (*ch) {
        options[numOptions].shortName = *ch++;
        options[numOptions].longName = NULL;
	options[numOptions].val = 0;
	options[numOptions].descrip = NULL;
	options[numOptions].argDescrip = NULL;
	options[numOptions].arg = NULL;
	if (*ch == ':') {
	    options[numOptions].argInfo = POPT_ARG_STRING;
	    ch++;
	} else {
	    options[numOptions].argInfo = POPT_ARG_NONE;
	}

	options[numOptions].val = numOptions + 1;

	numOptions++;
    }

    for (i = 0; i < PyList_Size(longArgs); i++) {
        options[numOptions].shortName = 0;
	options[numOptions].val = 0;
	options[numOptions].descrip = NULL;
	options[numOptions].argDescrip = NULL;
	options[numOptions].arg = NULL;

        strObject = PyList_GetItem(longArgs, i);
	str = PyString_AsString(strObject);
	if (!str) return NULL;

	if (str[strlen(str) - 1] == '=') {
	    str = strcpy(alloca(strlen(str) + 1), str);
	    str[strlen(str) - 1] = '\0';
	    options[numOptions].argInfo = POPT_ARG_STRING;
	} else {
	    options[numOptions].argInfo = POPT_ARG_NONE;
	}

	options[numOptions].val = numOptions + 1;
	options[numOptions].longName = str;

	numOptions++;
    }

    memset(options + numOptions, 0, sizeof(*options));

    argv = alloca(sizeof(*argv) * (PyList_Size(argList) + 1));
    for (i = 0; i < PyList_Size(argList); i++) {
        strObject = PyList_GetItem(argList, i);
	str = PyString_AsString(strObject);
	if (!str) return NULL;

	argv[i] = str;
    }

    argv[i] = NULL;

    optCon = poptGetContext("", PyList_Size(argList), argv,
			    options, POPT_CONTEXT_KEEP_FIRST);
    retList = PyList_New(0);
    retArgs = PyList_New(0);

    while ((rc = poptGetNextOpt(optCon)) >= 0) {
	const char * argument;

	rc--;

	if (options[rc].argInfo == POPT_ARG_STRING)
	    argument = poptGetOptArg(optCon);
	else
	    argument = NULL;
	    
	if (options[rc].longName) {
	    str = alloca(strlen(options[rc].longName) + 3);
	    sprintf(str, "--%s", options[rc].longName);
	} else {
	    str = strBuf;
	    sprintf(str, "-%c", options[rc].shortName);
	}

	if (argument) {
	    argument = strcpy(alloca(strlen(argument) + 1), argument);
	    PyList_Append(retList, 
			    Py_BuildValue("(ss)", str, argument));
	} else {
	    PyList_Append(retList, Py_BuildValue("(ss)", str, ""));
	}
    }

    if (rc < -1) {
	i = strlen(poptBadOption(optCon, POPT_BADOPTION_NOALIAS)) +
	    strlen(poptStrerror(rc));

	error = alloca(i) + 50;

	sprintf(error, "bad argument %s: %s\n", 
		poptBadOption(optCon, POPT_BADOPTION_NOALIAS), 
		poptStrerror(rc));

	PyErr_SetString(PyExc_TypeError, error);
	return NULL;
    }

    argv = (const char **) poptGetArgs(optCon);
    for (i = 0; argv && argv[i]; i++) {
	PyList_Append(retArgs, PyString_FromString(argv[i]));
    }

    poptFreeContext(optCon);

    return Py_BuildValue("(OO)", retList, retArgs);
}

static PyObject * doUMount(PyObject * s, PyObject * args) {
    char * fs;

    if (!PyArg_ParseTuple(args, "s", &fs)) return NULL;

    if (umount(fs)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doMount(PyObject * s, PyObject * args) {
    char * fs, * device, * mntpoint;
    int rc;
    int readOnly;
    int bindMount;
    int reMount;

    if (!PyArg_ParseTuple(args, "sssiii", &fs, &device, &mntpoint,
			  &readOnly, &bindMount, &reMount)) return NULL;

    rc = doPwMount(device, mntpoint, fs, readOnly, 0, NULL, NULL, bindMount, reMount);
    if (rc == IMOUNT_ERR_ERRNO) 
	PyErr_SetFromErrno(PyExc_SystemError);
    else if (rc)
	PyErr_SetString(PyExc_SystemError, "mount failed");

    if (rc) return NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

#define BOOT_SIGNATURE	0xaa55	/* boot signature */
#define BOOT_SIG_OFFSET	510	/* boot signature offset */

static PyObject * doCheckBoot (PyObject * s, PyObject * args) {
    char * path;
    int fd, size;
    unsigned short magic;

    /* code from LILO */
    
    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;

    if ((fd = open (path, O_RDONLY)) == -1) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    if (lseek(fd,(long) BOOT_SIG_OFFSET, 0) < 0) {
	close (fd);
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }
    
    if ((size = read(fd,(char *) &magic, 2)) != 2) {
	close (fd);
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    close (fd);
    
    return Py_BuildValue("i", magic == BOOT_SIGNATURE);
}

int swapoff(const char * path);
int swapon(const char * path, int priorty);

static PyObject * doSwapoff (PyObject * s, PyObject * args) {
    char * path;

    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;

    if (swapoff (path)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }
    
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doSwapon (PyObject * s, PyObject * args) {
    char * path;

    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;

    if (swapon (path, 0)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }
    
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * smpAvailable(PyObject * s, PyObject * args) {
    if (!PyArg_ParseTuple(args, "")) return NULL;

    return Py_BuildValue("i", detectSMP());
}

static PyObject * htAvailable(PyObject * s, PyObject * args) {
    if (!PyArg_ParseTuple(args, "")) return NULL;

    return Py_BuildValue("i", detectHT());
}

static PyObject * summitAvailable(PyObject * s, PyObject * args) {
    if (!PyArg_ParseTuple(args, "")) return NULL;

    return Py_BuildValue("i", detectSummit());
}

void init_isys(void) {
    PyObject * m, * d;

    m = Py_InitModule("_isys", isysModuleMethods);
    d = PyModule_GetDict(m);

    PyDict_SetItemString(d, "MIN_RAM", PyInt_FromLong(MIN_RAM));
    PyDict_SetItemString(d, "MIN_GUI_RAM", PyInt_FromLong(MIN_GUI_RAM));
    PyDict_SetItemString(d, "EARLY_SWAP_RAM", PyInt_FromLong(EARLY_SWAP_RAM));
}

static PyObject * doConfigNetDevice(PyObject * s, PyObject * args) {
    char * dev, * ip, * netmask;
    char * gateway;
    struct pumpNetIntf device;
    typedef int int32;
    
    if (!PyArg_ParseTuple(args, "ssss", &dev, &ip, &netmask, &gateway)) 
	return NULL;

    memset(&device,'\0',sizeof(struct pumpNetIntf));
    strncpy(device.device, dev, sizeof(device.device) - 1);
    device.ip.s_addr = inet_addr(ip);
    device.netmask.s_addr = inet_addr(netmask);

    *((int32 *) &device.broadcast) = (*((int32 *) &device.ip) & 
		       *((int32 *) &device.netmask)) | 
		       ~(*((int32 *) &device.netmask));

    *((int32 *) &device.network) = 
	    *((int32 *) &device.ip) & *((int32 *) &device.netmask);

    device.set = PUMP_INTFINFO_HAS_IP | PUMP_INTFINFO_HAS_NETMASK |
		 PUMP_INTFINFO_HAS_BROADCAST | PUMP_INTFINFO_HAS_NETWORK;
    
    if (pumpSetupInterface(&device)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    if (strlen(gateway)) {
	device.gateway.s_addr = inet_addr(gateway);
	if (pumpSetupDefaultGateway(&device.gateway)) {
	    PyErr_SetFromErrno(PyExc_SystemError);
	    return NULL;
	}
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doPumpNetDevice(PyObject * s, PyObject * args) {
    char * device;
    char * dhcpclass = NULL;
    char * chptr;
    struct pumpNetIntf cfg;
    PyObject * rc;

    if (!PyArg_ParseTuple(args, "s|s", &device, &dhcpclass))
	return NULL;

    chptr = pumpDhcpClassRun(device, 0, 0, NULL, dhcpclass, &cfg, NULL);
    if (chptr) {
	Py_INCREF(Py_None);
	return Py_None;
    }

    if (pumpSetupInterface(&cfg)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    if (pumpSetupDefaultGateway(&cfg.gateway)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    if (cfg.numDns)
	rc = PyString_FromString(inet_ntoa(cfg.dnsServers[0]));
    else
	rc = PyString_FromString("");

    return rc;
}

static PyObject * doPoptParse(PyObject * s, PyObject * args) {
    char * str;
    int argc = 0, i;
    int ret;
    const char ** argv = NULL;
    PyObject * list;

    if (!PyArg_ParseTuple(args, "s", &str)) return NULL;

    ret = poptParseArgvString(str, &argc, &argv);
    if ((ret != 0) && (ret != POPT_ERROR_NOARG)) {
	PyErr_SetString(PyExc_ValueError, "bad string for parsing");
	return NULL;
    }

    list = PyList_New(argc);
    for (i = 0; i < argc; i++)
	PyList_SetItem(list, i, PyString_FromString(argv[i]));

    free(argv);

    return list;
}

#include <linux/fb.h>

static PyObject * doFbconProbe (PyObject * s, PyObject * args) {
    char * path;
    int fd, size;
    struct fb_fix_screeninfo fix;
    struct fb_var_screeninfo var;
    char vidres[1024], vidmode[40];
    int depth = 0;

    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;
    
    if ((fd = open (path, O_RDONLY)) == -1) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    if (ioctl(fd, FBIOGET_FSCREENINFO, &fix) < 0) {
	close (fd);
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    vidres[0] = 0;    
    if (ioctl(fd, FBIOGET_VSCREENINFO, &var) >= 0 && var.pixclock) {
	int x[4], y[4], vtotal, laced = 0, dblscan = 0;
	char *p;
	double drate, hrate, vrate;
#ifdef __sparc__
	switch (fix.accel) {
	case FB_ACCEL_SUN_CREATOR:
	    var.bits_per_pixel = 24;
	    /* FALLTHROUGH */
	case FB_ACCEL_SUN_LEO:
	case FB_ACCEL_SUN_CGSIX:
	case FB_ACCEL_SUN_CG14:
	case FB_ACCEL_SUN_BWTWO:
	case FB_ACCEL_SUN_CGTHREE:
	case FB_ACCEL_SUN_TCX:
	    var.xres = var.xres_virtual;
	    var.yres = var.yres_virtual;
	    fix.smem_len = 0;
	    break;
	}
#endif
	depth = var.bits_per_pixel;
	sprintf(vidmode, "%dx%d", var.xres, var.yres);
	x[0] = var.xres;
	x[1] = x[0] + var.right_margin;
	x[2] = x[1] + var.hsync_len;
	x[3] = x[2] + var.left_margin;
	y[0] = var.yres;
	y[1] = y[0] + var.lower_margin;
	y[2] = y[1] + var.vsync_len;
	y[3] = y[2] + var.upper_margin;
	vtotal = y[3];
	drate = 1E12/var.pixclock;
	switch (var.vmode & FB_VMODE_MASK) {
	case FB_VMODE_INTERLACED: laced = 1; break;
	case FB_VMODE_DOUBLE: dblscan = 1; break;
	}
	if (dblscan) vtotal <<= 2;
	else if (!laced) vtotal <<= 1;
	hrate = drate / x[3];
	vrate = hrate / vtotal * 2;
	sprintf (vidres,
	    "Section \"Monitor\"\n"
	    "    Identifier  \"Probed Monitor\"\n"
	    "    VendorName  \"Unknown\"\n"
	    "    ModelName   \"Unknown\"\n"
	    "    HorizSync   %5.3f\n"
	    "    VertRefresh %5.3f\n"
	    "    ModeLine    \"%dx%d\" %5.3f %d %d %d %d %d %d %d %d",
	    hrate/1E3, vrate,
	    x[0], y[0],
	    drate/1E6+0.001,
	    x[0], x[1], x[2], x[3],
	    y[0], y[1], y[2], y[3]);
	if (laced) strcat (vidres, " Interlaced");
	if (dblscan) strcat (vidres, " DoubleScan");
	p = strchr (vidres, 0);
	sprintf (p, " %cHSync %cVSync",
		 (var.sync & FB_SYNC_HOR_HIGH_ACT) ? '+' : '-',
		 (var.sync & FB_SYNC_VERT_HIGH_ACT) ? '+' : '-');
	if (var.sync & FB_SYNC_COMP_HIGH_ACT)
	    strcat (vidres, " Composite");
	if (var.sync & FB_SYNC_BROADCAST)
	    strcat (vidres, " bcast");
	strcat (vidres, "\nEndSection\n");
    }

    close (fd);
    /* Allow 64K from VIDRAM to be taken for other purposes */
    size = fix.smem_len + 65536;
    /* And round down to some multiple of 256K */
    size = size & ~0x3ffff;
    /* And report in KB */
    size >>= 10;

    switch (depth) {
    case 8:
    case 16:
    case 24:
    case 32:
    	return Py_BuildValue("(iiss)", size, depth, vidmode, vidres);
    }
    return Py_BuildValue("(iiss)", size, 0, "", "");
}

static PyObject * doGetRaidSuperblock(PyObject * s, PyObject * args) {
    int fd;
    unsigned long size;
    struct md_superblock_s sb;

    if (!PyArg_ParseTuple(args, "i", &fd)) return NULL;

    if (ioctl(fd, BLKGETSIZE, &size)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    /* put the size in 1k blocks */
    size >>= 1;

    if (lseek64(fd, ((off64_t) 1024) * (off64_t) MD_NEW_SIZE_BLOCKS(size), SEEK_SET) < 0) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    } 

    if (read(fd, &sb, sizeof(sb)) != sizeof(sb)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    if (sb.md_magic != MD_SB_MAGIC) {
	PyErr_SetString(PyExc_ValueError, "bad md magic on device");
	return NULL;
    }

    return Py_BuildValue("(iiiiiii)", sb.major_version, sb.minor_version,
			 sb.set_magic, sb.level, sb.nr_disks,
			 sb.raid_disks, sb.md_minor);
}

static PyObject * doGetRaidChunkSize(PyObject * s, PyObject * args) {
    int fd;
    unsigned long size;
    struct md_superblock_s sb;

    if (!PyArg_ParseTuple(args, "i", &fd)) return NULL;

    if (ioctl(fd, BLKGETSIZE, &size)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    /* put the size in 1k blocks */
    size >>= 1;

    if (lseek64(fd, ((off64_t) 1024) * (off64_t) MD_NEW_SIZE_BLOCKS(size), SEEK_SET) < 0) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    } 

    if (read(fd, &sb, sizeof(sb)) != sizeof(sb)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    if (sb.md_magic != MD_SB_MAGIC) {
	PyErr_SetString(PyExc_ValueError, "bad md magic on device");
	return NULL;
    }

    return Py_BuildValue("i", sb.chunk_size / 1024);
}

static PyObject * doDevSpaceFree(PyObject * s, PyObject * args) {
    char * path;
    struct statfs sb;

    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;

    if (statfs(path, &sb)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    return Py_BuildValue("l", (long) sb.f_bfree * (sb.f_bsize / 1024) / (1024));
}

static PyObject * doRaidStop(PyObject * s, PyObject * args) {
    int fd;

    if (!PyArg_ParseTuple(args, "i", &fd)) return NULL;

    if (ioctl(fd, STOP_ARRAY, 0)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doLoadFont (PyObject * s, PyObject * args) {
    int ret;

    if (!PyArg_ParseTuple(args, "")) return NULL;

    ret = isysLoadFont ();
    if (ret) {
	errno = -ret;
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }
    
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doLoadKeymap (PyObject * s, PyObject * args) {
    char * keymap;
    int ret;

    if (!PyArg_ParseTuple(args, "s", &keymap)) return NULL;

    ret = isysLoadKeymap (keymap);
    if (ret) {
	errno = -ret;
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }
    
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doRaidStart(PyObject * s, PyObject * args) {
    int fd;
    char * dev;
    struct stat sb;

    if (!PyArg_ParseTuple(args, "is", &fd, &dev)) return NULL;

    if (stat(dev, &sb)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    if (ioctl(fd, START_ARRAY, (unsigned long) sb.st_rdev)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doResetResolv(PyObject * s, PyObject * args) {
    if (!PyArg_ParseTuple(args, "")) return NULL;

    res_init();		/* reinit the resolver so DNS changes take affect */

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doSetResolvRetry(PyObject * s, PyObject * args) {
    int count;

    if (!PyArg_ParseTuple(args, "i", &count)) return NULL;

    _res.retry = count;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doReadE2fsLabel(PyObject * s, PyObject * args) {
    char * device;
    ext2_filsys fsys;
    char buf[50];
    int rc;

    if (!PyArg_ParseTuple(args, "s", &device)) return NULL;

    rc = ext2fs_open(device, EXT2_FLAG_FORCE, 0, 0, unix_io_manager,
		     &fsys);
    if (rc) {
	Py_INCREF(Py_None);
	return Py_None;
    }

    memset(buf, 0, sizeof(buf));
    strncpy(buf, fsys->super->s_volume_name, 
	    sizeof(fsys->super->s_volume_name));

    ext2fs_close(fsys);

    return Py_BuildValue("s", buf); 
}

static PyObject * doExt2Dirty(PyObject * s, PyObject * args) {
    char * device;
    ext2_filsys fsys;
    int rc;
    int clean;

    if (!PyArg_ParseTuple(args, "s", &device)) return NULL;

    rc = ext2fs_open(device, EXT2_FLAG_FORCE, 0, 0, unix_io_manager,
		     &fsys);
    if (rc) {
	Py_INCREF(Py_None);
	return Py_None;
    }

    clean = fsys->super->s_state & EXT2_VALID_FS;

    ext2fs_close(fsys);

    return Py_BuildValue("i", !clean); 
}
static PyObject * doExt2HasJournal(PyObject * s, PyObject * args) {
    char * device;
    ext2_filsys fsys;
    int rc;
    int hasjournal;

    if (!PyArg_ParseTuple(args, "s", &device)) return NULL;
    rc = ext2fs_open(device, EXT2_FLAG_FORCE, 0, 0, unix_io_manager,
		     &fsys);
    if (rc) {
	Py_INCREF(Py_None);
	return Py_None;
    }

    hasjournal = fsys->super->s_feature_compat & EXT3_FEATURE_COMPAT_HAS_JOURNAL;

    ext2fs_close(fsys);

    return Py_BuildValue("i", hasjournal); 
}
/* doIsScsiRemovable()
   Returns:
    -1 on error
     0 if not removable
     0 if removable, but is aacraid driver (should be treated as not removable)
     1 if removable (not to be used by installer)
*/
static PyObject * doIsScsiRemovable(PyObject * s, PyObject * args) {
    char *path;
    int fd;
    int rc;
    typedef struct sdata_t {
	u_int32_t inlen;
	u_int32_t outlen;
	unsigned char cmd[128];
    } sdata;
    sdata inq;
    
    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;

    memset (&inq, 0, sizeof (sdata));
    
    inq.inlen = 0;
    inq.outlen = 96;
    
    inq.cmd[0] = 0x12;          /* INQUIRY */
    inq.cmd[1] = 0x00;          /* lun=0, evpd=0 */
    inq.cmd[2] = 0x00;          /* page code = 0 */
    inq.cmd[3] = 0x00;          /* (reserved) */
    inq.cmd[4] = 96;            /* allocation length */
    inq.cmd[5] = 0x00;          /* control */
    
    fd = open (path, O_RDONLY);
    if (fd == -1) {
	if (errno == ENOMEDIUM)
	    return Py_BuildValue("i", 1); 
	else {
	    return Py_BuildValue("i", -1);
	}
    }

    /* look at byte 1, bit 7 for removable flag */
    if (!(rc = ioctl(fd, SCSI_IOCTL_SEND_COMMAND, &inq))) {
	if (inq.cmd[1] & (1 << 7)) {
	    /* XXX check the vendor, if it's DELL, HP, or ADAPTEC it could be
	       an adaptec perc RAID (aacraid) device */
	    if ((!strncmp (inq.cmd + 8, "DELL", 4))
		|| (!strncmp (inq.cmd + 8, "HP", 2))
		|| (!strncmp (inq.cmd + 8, "ADAPTEC", 7))) {
		rc = 0;
	    } else
		rc = 1;
	} else
	    rc = 0;
    } else {
/*	printf ("ioctl resulted in error %d\n", rc); */
	rc = -1;
    }

    close (fd);
    
    return Py_BuildValue("i", rc); 
}

static PyObject * doIsIdeRemovable(PyObject * s, PyObject * args) {
    char *path;
    char str[100];
    char devpath[250];
    char *t;
    int fd;
    int rc, i;
    DIR * dir;
    
    if (!PyArg_ParseTuple(args, "s", &path)) return NULL;

    if (access("/proc/ide", R_OK))
	return Py_BuildValue("i", -1); 

    if (!(dir = opendir("/proc/ide")))
	return Py_BuildValue("i", -1); 

    t = strrchr(path, '/');
    if (!t)
	return Py_BuildValue("i", -1); 

    /* set errno to 0, so we can tell when readdir() fails */
    snprintf(devpath, sizeof(devpath), "/proc/ide/%s/media", t+1);
    if ((fd = open(devpath, O_RDONLY)) >= 0) {
	i = read(fd, str, sizeof(str));
	close(fd);
	str[i - 1] = '\0';		/* chop off trailing \n */

	if (!strcmp(str, "floppy") || !strcmp(str, "cdrom"))
	    rc = 1;
	else
	    rc = 0;
    } else {
	rc = -1;
    }

    return Py_BuildValue("i", rc); 
}

static PyObject * doEjectCdrom(PyObject * s, PyObject * args) {
    int fd;

    if (!PyArg_ParseTuple(args, "i", &fd)) return NULL;

    if (ioctl(fd, CDROMEJECT, 1)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doVtActivate(PyObject * s, PyObject * args) {
    int vtnum;

    if (!PyArg_ParseTuple(args, "i", &vtnum)) return NULL;

    if (ioctl(0, VT_ACTIVATE, vtnum)) {
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doisPsudoTTY(PyObject * s, PyObject * args) {
    int fd;
    struct stat sb;

    if (!PyArg_ParseTuple(args, "i", &fd)) return NULL;
    fstat(fd, &sb);

    /* XXX close enough for now */
    return Py_BuildValue("i", (major(sb.st_rdev) == 3));
}

static PyObject * doisVioConsole(PyObject * s) {
    return Py_BuildValue("i", isVioConsole());
}

static PyObject * doSync(PyObject * s, PyObject * args) {
    int fd;

    if (!PyArg_ParseTuple(args, "", &fd)) return NULL;
    sync();

    Py_INCREF(Py_None);
    return Py_None;
}

int fileIsIso(const char * file);

static PyObject * doisIsoImage(PyObject * s, PyObject * args) {
    char * fn;
    int rc;

    if (!PyArg_ParseTuple(args, "s", &fn)) return NULL;

    rc = fileIsIso(fn);
    
    return Py_BuildValue("i", rc);
}

static PyObject * dogetGeometry(PyObject * s, PyObject * args) {
    int fd;
    char *dev;
    char cylinders[16], heads[16], sectors[16];
    char errstr[200];
    struct hd_geometry g;
    long numsectors;
    unsigned int numcylinders;

    if (!PyArg_ParseTuple(args, "s", &dev)) return NULL;

    fd = open(dev, O_RDONLY);
    if (fd == -1) {
	snprintf(errstr, sizeof(errstr), "could not open device %s", dev);
	PyErr_SetString(PyExc_ValueError, errstr);
        return NULL;
    }

    if (ioctl(fd, HDIO_GETGEO, &g)) {
        close(fd);
	snprintf(errstr, sizeof(errstr),  "HDTIO_GETGEO ioctl() failed on device %s", dev);
	PyErr_SetString(PyExc_ValueError, errstr);
        return NULL;
    }


    /* never use g.cylinders if all possible - it is truncated */
    if (ioctl(fd, BLKGETSIZE, &numsectors) == 0) {
	int sector_size=1;

#ifdef BLKSSZGET
	/* BLKSSZGET only works with kernel >= 2.3.3. */
	struct utsname buf;

	if (uname (&buf) == 0
	    && strverscmp (buf.release, "2.3.3") >= 0
	    && ioctl(fd, BLKSSZGET, &sector_size) == 0)
	    sector_size /= 512;
	else
#endif
       numcylinders = numsectors / (g.heads * g.sectors);
       numcylinders /= sector_size;
    } else {
       numcylinders = g.cylinders;
    }

    snprintf(cylinders, sizeof(cylinders), "%d", numcylinders);
    snprintf(heads, sizeof(heads), "%d", g.heads);
    snprintf(sectors, sizeof(sectors), "%d", g.sectors);
    
    return Py_BuildValue("(sss)", cylinders, heads, sectors);
}

static PyObject * getFramebufferInfo(PyObject * s, PyObject * args) {
    int fd;
    struct fb_var_screeninfo fb;

    fd = open("/dev/fb0", O_RDONLY);
    if (fd == -1) {
	Py_INCREF(Py_None);
	return Py_None;
    }

    if (ioctl(fd, FBIOGET_VSCREENINFO, &fb)) {
	close(fd);
	PyErr_SetFromErrno(PyExc_SystemError);
	return NULL;
    }

    close(fd);

    return Py_BuildValue("(iii)", fb.xres, fb.yres, fb.bits_per_pixel);
}

static PyObject * doGetPageSize(PyObject * s, PyObject * args) {
    return Py_BuildValue("i", getpagesize());
}

static PyObject * getLinkStatus(PyObject * s, PyObject * args) {
    char *dev;
    int ret;

    if (!PyArg_ParseTuple(args, "s", &dev))
	return NULL;

    ret = get_link_status(dev);
    /* returns 1 for link, 0 for no link, -1 for unknown */
    return Py_BuildValue("i", ret);
}

static PyObject * doGetMacAddress(PyObject * s, PyObject * args) {
    char *dev;
    char *ret;

    if (!PyArg_ParseTuple(args, "s", &dev))
	return NULL;

    ret = getMacAddr(dev);

    return Py_BuildValue("s", ret);
}

static PyObject * doGetIPAddress(PyObject * s, PyObject * args) {
    char *dev;
    char *ret;

    if (!PyArg_ParseTuple(args, "s", &dev))
	return NULL;

    ret = getIPAddr(dev);

    return Py_BuildValue("s", ret);
}

static PyObject * doResetFileContext(PyObject * s, PyObject * args) {
    char *fn, *buf = NULL;
    int ret;

    if (!PyArg_ParseTuple(args, "s", &fn))
        return NULL;

    ret = matchpathcon(fn, 0, &buf);
    /*    fprintf(stderr, "matchpathcon returned %d: set %s to %s\n", ret, fn, buf);*/
    if (ret == 0) {
        ret = lsetfilecon(fn, buf);
    }

    return Py_BuildValue("s", buf);
}

static PyObject * py_getDasdPorts(PyObject * o, PyObject * args) {
    if (!PyArg_ParseTuple(args, "")) return NULL;

    return Py_BuildValue("s", getDasdPorts());
}

static PyObject * py_isUsableDasd(PyObject * o, PyObject * args) {
    char *devname;
    if (!PyArg_ParseTuple(args, "s", &devname))
	return NULL;
    return Py_BuildValue("i", isUsableDasd(devname));
}

static PyObject * py_isLdlDasd(PyObject * o, PyObject * args) {
    char *devname;
    if (!PyArg_ParseTuple(args, "s", &devname))
	return NULL;
    return Py_BuildValue("i", isLdlDasd(devname));
}


static PyObject * printObject (PyObject * o, PyObject * args) {
    PyObject * obj;
    char buf[256];

    if (!PyArg_ParseTuple(args, "O", &obj))
	return NULL;
    
    snprintf(buf, 256, "<%s object at %lx>", obj->ob_type->tp_name,
	     (long) obj);

    return PyString_FromString(buf);
}

static PyObject *
py_bind_textdomain_codeset(PyObject * o, PyObject * args) {
    char *domain, *codeset, *ret;
	
    if (!PyArg_ParseTuple(args, "ss", &domain, &codeset))
	return NULL;

    ret = bind_textdomain_codeset(domain, codeset);

    if (ret)
	return PyString_FromString(ret);

    PyErr_SetFromErrno(PyExc_SystemError);
    return NULL;
}

int pdc_dev_running_raid(int fd);
int hpt_dev_running_raid(int fd);
int silraid_dev_running_raid(int fd);

static PyObject * hasIdeRaidMagic(PyObject * s, PyObject * args) {
#ifndef __i386__
    return Py_None;
#else
    char *dev;
    char * path;
    int ret, fd;

    if (!PyArg_ParseTuple(args, "s", &dev))
	return NULL;

    path = malloc((strlen(dev) + 10) * sizeof(char *));
    sprintf(path, "/tmp/%s", dev);
    if (devMakeInode(dev, path)) return Py_None;

    if ((fd = open(path, O_RDONLY)) == -1) return Py_None;

    ret = pdc_dev_running_raid(fd);
    if (ret == 1) {
        close(fd);
        unlink(path);
        //	fprintf(stderr, "found promise magic\n");
	return Py_BuildValue("s", "pdc");
    }

    /* we can't really sanely do these until we can do matchups between
     * ataraid/dX and hdX devices so that things can be thrown out 
     * appropriately.  the same would be true for pdcraid, except that
     * we've been doing it for a while anyway (#82847)
     */
#if 0
    ret = silraid_dev_running_raid(fd);
    if (ret == 1) {
        close(fd);
        unlink(path);
        //        fprintf(stderr, "found silicon image magic\n");
	return Py_BuildValue("s", "sil");
    }

    ret = hpt_dev_running_raid(fd);
    if (ret == 1) {
        close(fd);
        unlink(path);
        //        fprintf(stderr, "found highpoint magic\n");
	return Py_BuildValue("s", "hpt");
    }
#endif

    close(fd);
    return Py_None;
#endif
}

static PyObject * start_bterm(PyObject * s, PyObject * args) {
    if (!PyArg_ParseTuple(args, "")) return NULL;

    return Py_BuildValue("i", isysStartBterm());
}
