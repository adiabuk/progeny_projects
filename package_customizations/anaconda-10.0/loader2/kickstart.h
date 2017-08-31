#ifndef H_KICKSTART

#include "loader.h"

#define KS_CMD_NONE	    0
#define KS_CMD_NFS	    1
#define KS_CMD_CDROM	    2
#define KS_CMD_HD	    3
#define KS_CMD_URL	    4
#define KS_CMD_NETWORK      5
#define KS_CMD_TEXT         6
#define KS_CMD_KEYBOARD     7
#define KS_CMD_LANG         8
#define KS_CMD_DD           9
#define KS_CMD_DEVICE      10
#define KS_CMD_CMDLINE     11
#define KS_CMD_GRAPHICAL   12
#define KS_CMD_SELINUX     13

int ksReadCommands(char * cmdFile, int flags);
int ksGetCommand(int cmd, char ** last, int * argc, char *** argv);
int ksHasCommand(int cmd);

void getKickstartFile(struct loaderData_s * loaderData, int * flagsPtr);
void runKickstart(struct loaderData_s * loaderData, int * flagsPtr);
int getKickstartFromBlockDevice(char *device, char *path);
void getHostandPath(char * ksSource, char **host, char ** file, char * ip);

#endif
