/*
 * driverdisk.c - driver disk functionality
 *
 * Jeremy Katz <katzj@redhat.com>
 *
 * Copyright 2002-2003 Red Hat, Inc.
 *
 * This software may be freely redistributed under the terms of the GNU
 * General Public License.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 */

#include <fcntl.h>
#include <kudzu/kudzu.h>
#include <newt.h>
#include <popt.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "loader.h"
#include "log.h"
#include "loadermisc.h"
#include "lang.h"
#include "method.h"
#include "modules.h"
#include "moduledeps.h"
#include "moduleinfo.h"
#include "windows.h"
#include "hardware.h"
#include "driverdisk.h"

#include "nfsinstall.h"
#include "urlinstall.h"

#include "../isys/isys.h"
#include "../isys/imount.h"

static char * driverDiskFiles[] = { "modinfo", "modules.dep", "pcitable",
                                    "modules.cgz", NULL };



static int verifyDriverDisk(char *mntpt, int flags) {
    char ** fnPtr;
    char file[200];
    struct stat sb;

    for (fnPtr = driverDiskFiles; *fnPtr; fnPtr++) {
        sprintf(file, "%s/%s", mntpt, *fnPtr);
        if (access(file, R_OK)) {
            logMessage("cannot find %s, bad driver disk", file);
            return LOADER_BACK;
        }
    }

    /* check for both versions */
    sprintf(file, "%s/rhdd", mntpt);
    if (access(file, R_OK)) {
        logMessage("not a new format driver disk, checking for old");
        sprintf(file, "%s/rhdd-6.1", mntpt);
        if (access(file, R_OK)) {
            logMessage("can't find either driver disk identifier, bad "
                       "driver disk");
        }
    }

    /* side effect: file is still mntpt/ddident */
    stat(file, &sb);
    if (!sb.st_size)
        return LOADER_BACK;

    return LOADER_OK;
}

/* this copies the contents of the driver disk to a ramdisk and loads
 * the moduleinfo, etc.  assumes a "valid" driver disk mounted at mntpt */
static int loadDriverDisk(moduleInfoSet modInfo, moduleList modLoaded,
                          moduleDeps * modDepsPtr, char *mntpt, int flags) {
    char file[200], dest[200];
    char * title;
    char ** fnPtr;
    struct moduleBallLocation * location;
    struct stat sb;
    static int disknum = 0;
    int version = 1;
    int fd;

    /* check for both versions */
    sprintf(file, "%s/rhdd", mntpt);
    if (access(file, R_OK)) {
        version = 0;
        sprintf(file, "%s/rhdd-6.1", mntpt);
        if (access(file, R_OK)) {
            /* this can't happen, we already verified it! */
            return LOADER_BACK;
        } 
    }
    stat(file, &sb);
    title = malloc(sb.st_size + 1);

    fd = open(file, O_RDONLY);
    read(fd, title, sb.st_size);
    if (title[sb.st_size - 1] == '\n')
        sb.st_size--;
    title[sb.st_size] = '\0';
    close(fd);

    sprintf(file, "/tmp/ramfs/DD-%d", disknum);
    mkdirChain(file);

    if (!FL_CMDLINE(flags)) {
        startNewt(flags);
        winStatus(40, 3, _("Loading"), _("Reading driver disk..."));
    }

    for (fnPtr = driverDiskFiles; *fnPtr; fnPtr++) {
        sprintf(file, "%s/%s", mntpt, *fnPtr);
        sprintf(dest, "/tmp/ramfs/DD-%d/%s", disknum, *fnPtr);
        copyFile(file, dest);
    }

    location = malloc(sizeof(struct moduleBallLocation));
    location->title = strdup(title);
    location->path = sdupprintf("/tmp/ramfs/DD-%d/modules.cgz", disknum);
    location->version = version;

    sprintf(file, "%s/modinfo", mntpt);
    readModuleInfo(file, modInfo, location, 1);

    sprintf(file, "%s/modules.dep", mntpt);
    mlLoadDeps(modDepsPtr, file);

    sprintf(file, "%s/pcitable", mntpt);
    pciReadDrivers(file);

    if (!FL_CMDLINE(flags))
        newtPopWindow();

    disknum++;
    return 0;
}

/* Get the list of removable devices (floppy/cdrom) available.  Used to
 * find suitable devices for update disk / driver disk source.  
 * Returns the number of devices.  ***devNames will be a NULL-terminated list
 * of device names
 */
int getRemovableDevices(char *** devNames) {
    struct device **devices, **floppies, **cdroms;
    int numDevices = 0;
    int i = 0, j = 0;

    floppies = probeDevices(CLASS_FLOPPY, 
                            BUS_IDE | BUS_SCSI | BUS_MISC, PROBE_LOADED);
    cdroms = probeDevices(CLASS_CDROM, 
                          BUS_IDE | BUS_SCSI | BUS_MISC, PROBE_LOADED);

    /* we should probably take detached into account here, but it just
     * means we use a little bit more memory than we really need to */
    if (floppies)
        for (i = 0; floppies[i]; i++) numDevices++;
    if (cdroms)
        for (i = 0; cdroms[i]; i++) numDevices++;

    /* JKFIXME: better error handling */
    if (!numDevices) {
        logMessage("no devices found to load drivers from");
        return numDevices;
    }

    devices = malloc((numDevices + 1) * sizeof(**devices));

    i = 0;
    if (floppies)
        for (j = 0; floppies[j]; j++) 
            if ((floppies[j]->detached == 0) && (floppies[j]->device != NULL)) 
                devices[i++] = floppies[j];
    if (cdroms)
        for (j = 0; cdroms[j]; j++) 
            if ((cdroms[j]->detached == 0) && (cdroms[j]->device != NULL)) 
                devices[i++] = cdroms[j];

    devices[i] = NULL;
    numDevices = i;

    for (i = 0; devices[i]; i++) {
        logMessage("devices[%d] is %s", i, devices[i]->device);
    }

    *devNames = malloc((numDevices + 1) * sizeof(*devNames));
    for (i = 0; devices[i] && (i < numDevices); i++)
        (*devNames)[i] = strdup(devices[i]->device);
    free(devices);
    (*devNames)[i] = NULL;

    if (i != numDevices)
        logMessage("somehow numDevices != len(devices)");

    return numDevices;
}

/* Prompt for loading a driver from "media"
 *
 * class: type of driver to load.
 * usecancel: if 1, use cancel instead of back
 */
int loadDriverFromMedia(int class, moduleList modLoaded, 
                        moduleDeps * modDepsPtr, moduleInfoSet modInfo, 
                        int flags, int usecancel, int noprobe) {

    char * device = NULL;
    char ** devNames = NULL;
    enum { DEV_DEVICE, DEV_INSERT, DEV_LOAD, DEV_PROBE, 
           DEV_DONE } stage = DEV_DEVICE;
    int rc, num = 0;
    int dir = 1;

    while (stage != DEV_DONE) {
        switch(stage) {
        case DEV_DEVICE:
            rc = getRemovableDevices(&devNames);
            if (rc == 0)
                return LOADER_BACK;

            /* we don't need to ask which to use if they only have one */
            if (rc == 1) {
                device = strdup(devNames[0]);
                free(devNames);
                if (dir == -1)
                    return LOADER_BACK;
                
                stage = DEV_INSERT;
                break;
            }
            dir = 1;

            startNewt(flags);
            rc = newtWinMenu(_("Driver Disk Source"),
                             _("You have multiple devices which could serve "
                               "as sources for a driver disk.  Which would "
                               "you like to use?"), 40, 10, 10,
                             rc < 6 ? rc : 6, devNames,
                             &num, _("OK"), 
                             (usecancel) ? _("Cancel") : _("Back"), NULL);

            if (rc == 2) {
                free(devNames);
                return LOADER_BACK;
            }
            device = strdup(devNames[num]);
            free(devNames);

            stage = DEV_INSERT;
        case DEV_INSERT: {
            char * buf;

            buf = sdupprintf(_("Insert your driver disk into /dev/%s "
                               "and press \"OK\" to continue."), device);
            rc = newtWinChoice(_("Insert Driver Disk"), _("OK"), _("Back"),
                               buf);
            if (rc == 2) {
                stage = DEV_DEVICE;
                dir = -1;
                break;
            }
            dir = 1;

            devMakeInode(device, "/tmp/dddev");
            logMessage("trying to mount %s", device);
            if (doPwMount("/tmp/dddev", "/tmp/drivers", "vfat", 1, 0, NULL, NULL, 0, 0)) {
              if (doPwMount("/tmp/dddev", "/tmp/drivers", "ext2", 1, 0, NULL, NULL, 0, 0)) {
                if (doPwMount("/tmp/dddev", "/tmp/drivers", "iso9660", 1, 0, NULL, NULL, 0, 0)) {
                    newtWinMessage(_("Error"), _("OK"),
                                   _("Failed to mount driver disk."));
                    stage = DEV_INSERT;
                    break;
                }
              }
            }

            rc = verifyDriverDisk("/tmp/drivers", flags);
            if (rc == LOADER_BACK) {
                umount("/tmp/drivers");
                stage = DEV_INSERT;
                break;
            }

            stage = DEV_LOAD;
            break;
        }
        case DEV_LOAD: {
            int found = 0, before = 0;
            struct device ** devices;

            devices = probeDevices(class, BUS_UNSPEC, PROBE_LOADED);
            if (devices)
                for(; devices[before]; before++);

            rc = loadDriverDisk(modInfo, modLoaded, modDepsPtr, 
                                "/tmp/drivers", flags);
            umount("/tmp/drivers");
            if (rc == LOADER_BACK) {
                stage = DEV_INSERT;
                break;
            }
            /* fall through to probing */
            stage = DEV_PROBE;

        case DEV_PROBE:
            /* if they didn't specify that we should probe, then we should
             * just fall out */
            if (noprobe) {
                stage = DEV_DONE;
                break;
            }

            busProbe(modInfo, modLoaded, *modDepsPtr, 0, flags);

            devices = probeDevices(class, BUS_UNSPEC, PROBE_LOADED);
            if (devices)
                for(; devices[before]; found++);

            if (found > before) {
                stage = DEV_DONE;
                break;
            }

            /* we don't have any more modules of the proper class.  ask
             * them to manually load */
            rc = newtWinTernary(_("Error"), _("Manually choose"), 
                                _("Continue"), _("Load another disk"),
                                _("No devices of the appropriate type were "
                                  "found on this driver disk.  Would you "
                                  "like to manually select the driver, "
                                  "continue anyway, or load another "
                                  "driver disk?"));
            
            if (rc == 2) {
                /* if they choose to continue, just go ahead and continue */
                stage = DEV_DONE;
            } else if (rc == 3) {
                /* if they choose to load another disk, back to the 
                 * beginning with them */
                stage = DEV_DEVICE;
            } else {
                rc = chooseManualDriver(class, modLoaded, modDepsPtr, modInfo,
                                        flags);
                /* if they go back from a manual driver, we'll ask again.
                 * if they load something, assume it's what we need */
                if (rc == LOADER_OK) {
                    stage = DEV_DONE;
                }
            }

            break;
        }
                           

        case DEV_DONE:
            break;
        }
    }

    return LOADER_OK;
}


/* looping way to load driver disks */
int loadDriverDisks(int class, moduleList modLoaded, 
                    moduleDeps * modDepsPtr, moduleInfoSet modInfo, 
                    int flags) {
    int rc;

    rc = newtWinChoice(_("Driver disk"), _("Yes"), _("No"), 
                       _("Do you have a driver disk?"));
    if (rc != 1)
        return LOADER_OK;

    rc = loadDriverFromMedia(CLASS_UNSPEC, modLoaded, modDepsPtr, modInfo, 
                             flags, 1, 0);
    if (rc == LOADER_BACK)
        return LOADER_OK;

    do {
        rc = newtWinChoice(_("More Driver Disks?"), _("Yes"), _("No"),
                           _("Do you wish to load any more driver disks?"));
        if (rc != 1)
            break;
        loadDriverFromMedia(CLASS_UNSPEC, modLoaded, modDepsPtr, modInfo, 
                            flags, 0, 0);
    } while (1);

    return LOADER_OK;
}

static void loadFromLocation(struct loaderData_s * loaderData, 
                             char * dir, int flags) {
    if (verifyDriverDisk(dir, flags) == LOADER_BACK) {
        logMessage("not a valid driver disk");
        return;
    }

    loadDriverDisk(loaderData->modInfo, loaderData->modLoaded, 
                   loaderData->modDepsPtr, dir, flags);
    busProbe(loaderData->modInfo, loaderData->modLoaded, *
             loaderData->modDepsPtr, 0, flags);
}

void getDDFromSource(struct loaderData_s * loaderData,
                     char * src, int flags) {
    char *path = "/tmp/dd.img";
    int unlinkf = 0;

    if (!strncmp(src, "nfs:", 4)) {
        unlinkf = 1;
        if (getFileFromNfs(src + 4, "/tmp/dd.img", loaderData, 
                           flags)) {
            logMessage("unable to retrieve driver disk: %s", src);
            return;
        }
    } else if (!strncmp(src, "ftp://", 6) || !strncmp(src, "http://", 7)) {
        unlinkf = 1;
        if (getFileFromUrl(src, "/tmp/dd.img", loaderData, flags)) {
            logMessage("unable to retrieve driver disk: %s", src);
            return;
        }
    /* FIXME: this is a hack so that you can load a driver disk from, eg, 
     * scsi cdrom drives */
#if !defined(__s390__) && !defined(__s390x__)
    } else if (!strncmp(src, "cdrom", 5)) {
        loadDriverDisks(CLASS_UNSPEC, loaderData->modLoaded, 
                        loaderData->modDepsPtr, loaderData->modInfo, flags);
        return;
#endif
    } else if (!strncmp(src, "path:", 5)) {
	path = src + 5;
    } else {
        newtWinMessage(_("Kickstart Error"), _("OK"),
                       _("Unknown driver disk kickstart source: %s"), src);
        return;
    }

    if (!mountLoopback(path, "/tmp/drivers", "loop6")) {
        loadFromLocation(loaderData, "/tmp/drivers", flags);
        umountLoopback("/tmp/drivers", "loop6");
        unlink("/tmp/drivers");
        if (unlinkf) unlink(path);
    }

}

static void getDDFromDev(struct loaderData_s * loaderData, char * dev, 
                         char * fstype, int flags);

void useKickstartDD(struct loaderData_s * loaderData,
                    int argc, char ** argv, int * flagsPtr) {
    char * fstype = NULL;
    char * dev = NULL;
    char * src;
    poptContext optCon;
    int rc;
    int flags = *flagsPtr;
    struct poptOption ksDDOptions[] = {
        { "type", '\0', POPT_ARG_STRING, &fstype, 0 },
        { "source", '\0', POPT_ARG_STRING, &src, 0 },
        { 0, 0, 0, 0, 0 }
    };
    
    optCon = poptGetContext(NULL, argc, (const char **) argv, ksDDOptions, 0);
    if ((rc = poptGetNextOpt(optCon)) < -1) {
        newtWinMessage(_("Kickstart Error"), _("OK"),
                       _("The following invalid argument was specified for "
                         "the kickstart driver disk command: %s:%s"),
                       poptBadOption(optCon, POPT_BADOPTION_NOALIAS), 
                       poptStrerror(rc));
        return;
    }

    dev = (char *) poptGetArg(optCon);

    if (!dev && !src) {
        logMessage("bad arguments to kickstart driver disk command");
        return;
    }

    if (dev) {
        return getDDFromDev(loaderData, dev, fstype, flags);
    } else {
        return getDDFromSource(loaderData, src, flags);
    }
}

static void getDDFromDev(struct loaderData_s * loaderData, char * dev, 
                        char * fstype, int flags) {
    devMakeInode(dev, "/tmp/dddev");
    if (fstype) {
        if (doPwMount("/tmp/dddev", "/tmp/drivers", fstype, 1, 0, 
                       NULL, NULL, 0, 0)) {
            logMessage("unable to mount %s as %s", dev, fstype);
            return;
        }
    } else if (doPwMount("/tmp/dddev", "/tmp/drivers", "vfat", 1, 0, NULL, NULL, 0, 0)) {
        if (doPwMount("/tmp/dddev", "/tmp/drivers", "ext2", 1, 0, NULL, NULL, 0, 0)) {
            if (doPwMount("/tmp/dddev", "/tmp/drivers", "iso9660", 1, 0, NULL, NULL, 0, 0)) {
                logMessage("unable to mount driver disk %s", dev);
                return;
            }
        }
    }

    loadFromLocation(loaderData, "/tmp/drivers", flags);
    umount("/tmp/drivers");
    unlink("/tmp/drivers");
    unlink("/tmp/dddev");
}
