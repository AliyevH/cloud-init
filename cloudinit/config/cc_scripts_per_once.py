# Copyright (C) 2011 Canonical Ltd.
# Copyright (C) 2012 Hewlett-Packard Development Company, L.P.
#
# Author: Scott Moser <scott.moser@canonical.com>
# Author: Juerg Haefliger <juerg.haefliger@hp.com>
#
# This file is part of cloud-init. See LICENSE file for license information.
"""Scripts Per Once: Run one time scripts"""

import logging
import os

from cloudinit import subp
from cloudinit.cloud import Cloud
from cloudinit.config import Config
from cloudinit.config.schema import MetaSchema
from cloudinit.distros import ALL_DISTROS
from cloudinit.settings import PER_ONCE

meta: MetaSchema = {
    "id": "cc_scripts_per_once",
    "distros": [ALL_DISTROS],
    "frequency": PER_ONCE,
    "activate_by_schema_keys": [],
}

LOG = logging.getLogger(__name__)

SCRIPT_SUBDIR = "per-once"


def handle(name: str, cfg: Config, cloud: Cloud, args: list) -> None:
    # Comes from the following:
    # https://forums.aws.amazon.com/thread.jspa?threadID=96918
    runparts_path = os.path.join(cloud.get_cpath(), "scripts", SCRIPT_SUBDIR)
    try:
        subp.runparts(runparts_path)
    except Exception:
        LOG.warning(
            "Failed to run module %s (%s in %s)",
            name,
            SCRIPT_SUBDIR,
            runparts_path,
        )
        raise
