#ifndef MEDIACHECK_H
#define MEDIACHECK_H

/* simple program to check implanted md5sum in an iso 9660 image   */
/* Copyright 2001 Red Hat, Inc.                                    */
/* Michael Fulbright msf@redhat.com                                */

int mediaCheckFile(char *file, char *descr);
int parsepvd(int isofd, char *mediasum, int *skipsectors, long long *isosize, int *isostatus);

#endif
