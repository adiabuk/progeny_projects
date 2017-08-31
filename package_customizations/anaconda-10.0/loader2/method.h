#ifndef H_METHOD
#define H_METHOD

#include "modules.h"
#include "moduledeps.h"
#include "loader.h"
#include <kudzu/kudzu.h>

struct installMethod {
    char * name;
    char * shortname;
    int network;
    enum deviceClass deviceType;			/* for pcmcia */
    char * (*mountImage)(struct installMethod * method,
                         char * location, struct loaderData_s * loaderData,
                         moduleInfoSet modInfo, moduleList modLoaded,
                         moduleDeps * modDepsPtr, int flags);
};


int umountLoopback(char * mntpoint, char * device);
int mountLoopback(char * fsystem, char * mntpoint, char * device);

char * validIsoImages(char * dirName);
int readStampFileFromIso(char *file, char **descr, char **timestamp);
void queryIsoMediaCheck(char * isoDir, int flags);

int verifyStamp(char * path);

void umountStage2(void);
int mountStage2(char * path);
int copyFileAndLoopbackMount(int fd, char * dest, int flags,
                             char * device, char * mntpoint);
int getFileFromBlockDevice(char *device, char *path, char * dest);

void copyUpdatesImg(char * path);
void copyProductImg(char * path);
int copyDirectory(char * from, char * to);

void setMethodFromCmdline(char * arg, struct loaderData_s * ld);

#endif
