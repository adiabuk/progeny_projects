/* lzw.c -- compress files in LZW format.
 * This is a dummy version avoiding patent problems.
 */

#ifdef RCSID
static char rcsid[] = "$Id: lzw.c,v 1.1 2001/11/13 21:02:32 ewt Exp $";
#endif

#include <config.h>
#include "tailor.h"
#include "gzip.h"
#include "lzw.h"

static int msg_done = 0;

/* Compress in to out with lzw method. */
int lzw(in, out)
    int in, out;
{
    if (msg_done) return ERROR;
    msg_done = 1;
    fprintf(stderr,"output in compress .Z format not supported\n");
    if (in != out) { /* avoid warnings on unused variables */
        exit_code = ERROR;
    }
    return ERROR;
}
