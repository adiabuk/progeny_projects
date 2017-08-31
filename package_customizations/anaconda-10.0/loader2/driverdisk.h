#ifndef DRIVERDISK_H
#define DRIVERDISK_H

#include "loader.h"
#include "modules.h"
#include "moduledeps.h"
#include "moduleinfo.h"

int loadDriverFromMedia(int class, moduleList modLoaded, 
                        moduleDeps * modDepsPtr, moduleInfoSet modInfo, 
                        int flags, int usecancel, int noprobe);

int loadDriverDisks(int class, moduleList modLoaded, 
                    moduleDeps * modDepsPtr, moduleInfoSet modInfo, int flags);

int getRemovableDevices(char *** devNames);

int chooseManualDriver(int class, moduleList modLoaded, 
                       moduleDeps * modDepsPtr, moduleInfoSet modInfo,
                       int flags);
void useKickstartDD(struct loaderData_s * loaderData, int argc, 
                    char ** argv, int * flagsPtr);

void getDDFromSource(struct loaderData_s * loaderData,
                     char * src, int flags);

#endif
