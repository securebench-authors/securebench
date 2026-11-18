"""Restore R 4.3.3 in the Evaluation environment, as the reference installs it.

The agent installs R with apt, outside every scope root: apt's links into
/etc/alternatives and /usr/lib/R/etc -> /etc/R are absolute, and capture
rejects absolute link targets, so no candidate can carry an R installation.
r.tar.xz holds what `apt-get install --no-install-recommends
r-base-core=4.3.3-2build2` adds to the baseline (hidden/derive-r.sh). This
setup unpacks it at the paths apt uses, so the candidate's code runs on the R
the reference installs. It reads nothing from the candidate.
"""

import os
import stat
import tarfile

ARCHIVE = "/.securebench/evaluation/r.tar.xz"

with tarfile.open(ARCHIVE, "r:xz") as archive:
    for member in archive:
        target = "/" + member.name
        # Replace a file or link the way dpkg does, never writing through it.
        if os.path.lexists(target) and not stat.S_ISDIR(os.lstat(target).st_mode):
            os.unlink(target)
        archive.extract(member, "/", filter="fully_trusted")
