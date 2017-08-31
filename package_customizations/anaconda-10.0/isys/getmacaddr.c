/*
 * getmacaddr.c - get mac address for ethernet interface
 *
 * Copyright 2003 Red Hat, Inc.
 *
 * Michael Fulbright <msf@redhat.com>
 *
 * This software may be freely redistributed under the terms of the GNU
 * general public license.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <net/if.h>

/* returns NULL or allocated string */
char *getMacAddr(char *ifname) {
  int i;
  int sock;
  char *rcstr;
  struct ifreq ifr;

  if ((sock = socket(AF_INET, SOCK_DGRAM, 0)) < 0) 
      return NULL;
 
  /* Setup our control structures. */
  memset(&ifr, 0, sizeof(ifr));
  strcpy(ifr.ifr_name, ifname);

  if (ioctl(sock, SIOCGIFHWADDR, &ifr) < 0)
      return NULL;

  rcstr = (char *) malloc(24);
  *rcstr = '\0';
  for (i=0; i<6; i++) {
      char tmp[4];
      sprintf(tmp, "%02X",(unsigned char)ifr.ifr_hwaddr.sa_data[i]);
      strcat(rcstr,tmp);
      if (i != 5)
	  strcat(rcstr, ":");
  }

  return rcstr;
}

#ifdef TESTING
int main() {

    printf("%s\n", getMacAddr("eth0"));
}
#endif
