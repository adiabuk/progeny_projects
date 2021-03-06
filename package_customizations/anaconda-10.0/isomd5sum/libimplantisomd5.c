/* Copyright 2001 Red Hat, Inc.                                    */
/* Michael Fulbright msf@redhat.com                                */

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

#include "md5.h"
#include "libimplantisomd5.h"

#define APPDATA_OFFSET 883
#define SIZE_OFFSET 84

/* number of sectors to ignore at end of iso when computing sum */
#define SKIPSECTORS 15

#define MAX(x, y)  ((x > y) ? x : y)
#define MIN(x, y)  ((x < y) ? x : y)

/* finds primary volume descriptor and returns info from it */
/* mediasum must be a preallocated buffer at least 33 bytes long */
static int parsepvd(int isofd, char *mediasum, long long *isosize) {
    unsigned char buf[2048];
    long long offset;
    unsigned char *p __attribute__((unused));

    if (lseek(isofd, 16*2048, SEEK_SET) == -1)
	return ((long long)-1);
    
    offset = (16 * 2048);
    for (;1;) {
        if (read(isofd, buf, 2048L) == -1)
	    return ((long long)-1);

	if (buf[0] == 1)
	    /* found primary volume descriptor */
	    break;
	else if (buf[0] == 255)
	    /* hit end and didn't find primary volume descriptor */
	    return ((long long)-1);
	offset += 2048L;
    }
    
    /* read out md5sum */
#if 0
    memcpy(mediasum, buf + APPDATA_OFFSET + 13, 32);
    mediasum[32] = '\0';

    for (p=mediasum; *p; p++)
	if (*p != ' ')
	    break;

    /* if the md5sum was all spaces, we didn't find md5sum */
    if (!*p)
	return -1;
#endif

    /* get isosize */
    *isosize = (buf[SIZE_OFFSET]*0x1000000+buf[SIZE_OFFSET+1]*0x10000 +
		buf[SIZE_OFFSET+2]*0x100 + buf[SIZE_OFFSET+3]) * 2048LL;

    return offset;
}


static unsigned int writeAppData(unsigned char *appdata, char *valstr, unsigned int loc) {
    if (loc + strlen(valstr) > 511) {
	printf("Attempted to write too much appdata, exiting...\n");
	exit(-1);
    }

    memcpy(appdata + loc, valstr, strlen(valstr));

    return loc+strlen(valstr);
}




int implantISOFile(char *fname, int supported, int forceit, int quiet, char **errstr) {
    int i;
    int isofd;
    int nread;
    int dirty;
    int pvd_offset;
    long long isosize, total;
    unsigned char md5sum[16];
    unsigned int loc;
    unsigned char buf[2048];
    unsigned char orig_appdata[512];
    unsigned char new_appdata[512];
    unsigned char mediasum[33];
    char md5str[40];
    MD5_CTX md5ctx;

    isofd = open(fname, O_RDWR);

    if (isofd < 0) {
	*errstr = "Error - Unable to open file %s\n\n";
	return -1;
    }

    pvd_offset = parsepvd(isofd, mediasum, &isosize);
    if (pvd_offset < 0) {
	*errstr = "Could not find primary volumne!\n\n";
	return -1;
    }

    lseek(isofd, pvd_offset + APPDATA_OFFSET, SEEK_SET);
    nread = read(isofd, orig_appdata, 512);

    if (!forceit) {
	dirty = 0;
	for (i=0; i < 512; i++)
	    if (orig_appdata[i] != ' ')
		dirty = 1;

	if (dirty) {
	    *errstr = "Application data has been used - not implanting md5sum!\n";
	    return -1;
	}
    } else {
	/* write out blanks to erase old app data */
	lseek(isofd, pvd_offset + APPDATA_OFFSET, SEEK_SET);
	memset(new_appdata, ' ', 512);
	i = write(isofd, new_appdata, 512);
	if (i<0) {
	    printf("write failed %d\n", i);
	    perror("");
	}
    }

    /* now do md5sum */
    lseek(isofd, 0L, SEEK_SET);

    MD5_Init(&md5ctx);

    total = 0;
    /* read up to 15 sectors from end, due to problems reading last few */
    /* sectors on burned CDs                                            */
    while (total < isosize - SKIPSECTORS*2048) {
	nread = read(isofd, buf, 2048);
	if (nread <= 0)
	    break;

	MD5_Update(&md5ctx, buf, nread);
	total = total + nread;
    }

    MD5_Final(md5sum, &md5ctx);

    *md5str = '\0';
    for (i=0; i<16; i++) {
	char tmpstr[4];
	snprintf (tmpstr, 4, "%02x", md5sum[i]);
	strcat(md5str, tmpstr);
    }

    if (!quiet) {
	printf("Inserting md5sum into iso image...\n");
	printf("md5 = %s\n", md5str);
    }
    /*    memcpy(new_appdata, orig_appdata, 512); */
    memset(new_appdata, ' ', 512);

    loc = 0;
    loc = writeAppData(new_appdata, "ISO MD5SUM = ", loc);
    loc = writeAppData(new_appdata, md5str, loc);
    loc = writeAppData(new_appdata, ";", loc);
    snprintf(buf, sizeof(buf), "SKIPSECTORS = %d", SKIPSECTORS);
    loc = writeAppData(new_appdata, buf, loc);
    loc = writeAppData(new_appdata, ";", loc);

    if (supported) {
	if (!quiet)
	    printf("Setting supported flag to 1\n");
	loc = writeAppData(new_appdata, "RHLISOSTATUS=1", loc);
    } else {
	if (!quiet)
	    printf("Setting supported flag to 0\n");
	loc = writeAppData(new_appdata, "RHLISOSTATUS=0", loc);
    }
	
    loc = writeAppData(new_appdata, ";", loc);

    loc = writeAppData(new_appdata, "THIS IS NOT THE SAME AS RUNNING MD5SUM ON THIS ISO!!", loc);
    
    i = lseek(isofd, pvd_offset + APPDATA_OFFSET, SEEK_SET);
    if (i<0)
	printf("seek failed\n");

    i = write(isofd, new_appdata, 512);
    if (i<0) {
	printf("write failed %d\n", i);
	perror("");
    }

    close(isofd);
    errstr = NULL;
    return 0;
}
