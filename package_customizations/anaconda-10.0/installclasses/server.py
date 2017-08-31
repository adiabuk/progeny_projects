from installclass import BaseInstallClass
from rhpl.translate import *
from constants import *
import os
import iutil

class InstallClass(BaseInstallClass):

    # name has underscore used for mnemonics, strip if you dont need it
    id = "server"
    name = N_("_Server")
    pixmap = "server.png"
    description = N_("Select this installation type if you would like to "
		     "set up file sharing, print sharing, and Web services. "
		     "Additional services can also be enabled, and you "
		     "can choose whether or not to install a graphical "
		     "environment.")
    
    sortPriority = 10
    showLoginChoice = 1

    def setSteps(self, dispatch):
	BaseInstallClass.setSteps(self, dispatch);
	dispatch.skipStep("authentication")

    def setGroupSelection(self, grpset, intf):
	BaseInstallClass.__init__(self, grpset)

        grpset.unselectAll()
        grpset.selectGroup("server", asMeta = 1)

    def setInstallData(self, id):
	BaseInstallClass.setInstallData(self, id)
        BaseInstallClass.setDefaultPartitioning(self, id.partitions,
                                                CLEARPART_TYPE_ALL)

    def __init__(self, expert):
	BaseInstallClass.__init__(self, expert)
