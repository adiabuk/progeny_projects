/*
 * linkdetect.c - simple link detection
 *
 * pulls code from mii-tool.c in net-toools and ethtool so
 * that we can do everything that jgarzik says we should check
 *
 * Copyright 2002,2003 Red Hat, Inc.
 * Portions Copyright 2000 David A. Hinds -- dhinds@pcmcia.sourceforge.org
 *
 * Jeremy Katz <katzj@redhat.com>
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
#include <sys/ioctl.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

#include <sys/socket.h>
#include <sys/types.h>
#include <net/if.h>

#ifdef DIET
typedef void * caddr_t;
#endif

#include <linux/sockios.h>
#include "net.h"
#include "mii.h"
#include "ethtool-copy.h"

static struct ifreq ifr;

static int mdio_read(int skfd, int location)
{
    struct mii_data *mii = (struct mii_data *)&ifr.ifr_data;
    mii->reg_num = location;
    if (ioctl(skfd, SIOCGMIIREG, &ifr) < 0) {
#ifdef STANDALONE
	fprintf(stderr, "SIOCGMIIREG on %s failed: %s\n", ifr.ifr_name,
		strerror(errno));
#endif
	return -1;
    }
    return mii->val_out;
}

/* we don't need writing right now */
#if 0
static void mdio_write(int skfd, int location, int value)
{
    struct mii_data *mii = (struct mii_data *)&ifr.ifr_data;
    mii->reg_num = location;
    mii->val_in = value;
    if (ioctl(skfd, SIOCSMIIREG, &ifr) < 0) {
#ifdef STANDALONE
	fprintf(stderr, "SIOCSMIIREG on %s failed: %s\n", ifr.ifr_name,
		strerror(errno));
#endif
    }
}
#endif



static int get_mii_link_status(int sock) {
    int i, mii_val[32];

    if (ioctl(sock, SIOCGMIIPHY, &ifr) < 0) {
	if (errno != ENODEV)
#ifdef STANDALONE
	    fprintf(stderr, "SIOCGMIIPHY on '%s' failed: %s\n",
		    ifr.ifr_name, strerror(errno));
#endif
	return -1;
    }

    /* Some bits in the BMSR are latched, but we can't rely on being
       the only reader, so only the current values are meaningful */
    mdio_read(sock, MII_BMSR);
    for (i = 0; i < 8; i++)
	mii_val[i] = mdio_read(sock, i);

    if (mii_val[MII_BMCR] == 0xffff) {
#ifdef STANDALONE
	fprintf(stderr, "  No MII transceiver present!.\n");
#endif
	return -1;
    }

    if (mii_val[MII_BMSR] & MII_BMSR_LINK_VALID)
        return 1;
    else
        return 0;
}

static int get_ethtool_link_status(int sock) {
    struct ethtool_value edata;
    int rc;

    edata.cmd = ETHTOOL_GLINK;
    ifr.ifr_data = (caddr_t)&edata;
    rc = ioctl(sock, SIOCETHTOOL, &ifr);
    if (rc == 0) {
        return edata.data;
    } else if (errno != EOPNOTSUPP) {
#ifdef STANDALONE
        fprintf(stderr, "Cannot get link status (%d): %s\n", errno, strerror(errno));
#endif
    }

    return -1;
}



int get_link_status(char * devname) {
    int sock, rc;

    if ((sock = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
#ifdef STANDALONE
        fprintf(stderr, "Error creating socket: %s\n", strerror(errno));
#endif
        return -1;
    }

    /* Setup our control structures. */
    memset(&ifr, 0, sizeof(ifr));
    strcpy(ifr.ifr_name, devname);

    /* check for link with both ethtool and mii registers.  ethtool is
     * supposed to be the One True Way (tm), but it seems to not work
     * with much yet :/ */

    rc = get_ethtool_link_status(sock);
#ifdef STANDALONE
    printf("ethtool link status of %s is: %d\n", devname, rc);
#endif
    if (rc == 1) {
        close(sock);
        return 1;
    }

    rc = get_mii_link_status(sock);
#ifdef STANDALONE
    printf("MII link status of %s is: %d\n", devname, rc);
#endif
    if (rc == 1) {
        close(sock);
        return 1;
    }

    return 0;
}

#ifdef STANDALONE
/* hooray for stupid test programs! */
int main(int argc, char **argv) {
    char * dev;

    if (argc >= 2) 
        dev = argv[1];
    else
        dev = strdup("eth0");

    printf("link status of %s is %d\n", dev, get_link_status(dev));
    return 0;
}
#endif
