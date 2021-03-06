include ../Makefile.inc

CFLAGS = -ffunction-sections -I$(PYTHONINCLUDE) -I.. -Wall -Os -g  -DHAVE_NFS -D_LARGEFILE_SOURCE=1 -D_LARGEFILE64_SOURCE=1 -D_FILE_OFFSET_BITS=64 -Werror

OBJECTS = nfsmount.o nfsmount_clnt.o nfsmount_xdr.o imount.o getmacaddr.o \
          smp.o devnodes.o cpio.o uncpio.o dasd.o \
	  lang.o isofs.o dns.o linkdetect.o pdc.o hpt.o silraid.o vio.o \
	  ethtool.o getipaddr.o
SOBJECTS = $(patsubst %.o,%.lo,$(OBJECTS))
SOURCES = $(patsubst %.o,%.c,$(OBJECTS)) isys.c
LOADLIBES = -lresolv -lpci -lpopt -lpump -lext2fs -lz -lbterm -lbogl -lwlite -lkudzu -lpci -lselinux
PYMODULES = _isys.so
SUBDIRS = gzlib
DIET = diet

DOBJECTS = $(patsubst %.o,%.do,$(OBJECTS))

GENERATED = nfs_mountversion.h

ifeq (1, $(USEDIET))
DIETLIB=libisys-diet.a
endif

ifeq ($(ARCH),sparc)
PYMODULES += _silo.so
SOURCES += silo.c
endif

ifeq ($(ARCH),ppc)
OBJECTS += minifind.o
SOURCES += minifind.c
endif

ifeq (.depend,$(wildcard .depend))
TARGET=all
else
TARGET=depend all
endif

everything: $(TARGET)

all: subdirs $(PYMODULES) libisys.a $(DIETLIB)

%.lo: %.c
	$(CC) -c $(CFLAGS) -fPIC -o $@ $<

%.do: %.c
	$(DIET) $(CC) -c $(CFLAGS) -DGZLIB=1 -DDIET=1 "-Du_char=unsigned char" -o $@ $<

_isys.so: isys.lo $(SOBJECTS)
	gcc -shared -g -fPIC -o $@ isys.lo $(SOBJECTS) $(LOADLIBES)

_silo.so: silo.c
	gcc -shared $(CFLAGS) -fpic -o $@ silo.c ../balkan/libbalkan.a

libisys.a: libisys.a($(OBJECTS))

libisys-diet.a: libisys-diet.a($(DOBJECTS))

filtertest: filtertest.o libisys.a

clean:
	rm -f *.o *.so *.lo *.a *.pyc $(TARGET) $(SOBJECTS) $(DOBJECTS) 
	rm -f $(DIETLIBS) $(OBJECTS) $(GENERATED)
	for d in $(SUBDIRS); do make -C $$d clean; done

install: all
	install -s $(PYMODULES) $(DESTDIR)/$(PYTHONLIBDIR)
	install isys.py $(DESTDIR)/$(PYTHONLIBDIR)

subdirs:
	for d in $(SUBDIRS); do make -C $$d; done

nfsmount.o: nfs_mountversion.h

nfsmount.lo: nfs_mountversion.h

nfsmount.do: nfs_mountversion.h

nfs_mountversion.h: /usr/include/linux/nfs_mount.h
	grep NFS_MOUNT_VERSION $< | sed -e 's/NFS/KERNEL_NFS/' > $@

depend: nfs_mountversion.h
	$(CPP) -M $(CFLAGS) $(SOURCES) > .depend

ifeq (.depend,$(wildcard .depend))
include .depend
endif                                           

