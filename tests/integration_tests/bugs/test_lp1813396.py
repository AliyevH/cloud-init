"""Integration test for lp-1813396

Ensure gpg is called with no tty flag.
"""

import pytest

from tests.integration_tests.instances import IntegrationInstance
from tests.integration_tests.util import (
    verify_clean_boot,
    verify_clean_log,
    verify_ordered_items_in_text,
)

USER_DATA = """\
#cloud-config
apt:
  sources:
    cloudinit:
      source: 'deb [arch=amd64] http://ppa.launchpad.net/cloud-init-dev/daily/ubuntu focal main'
      keyserver: keyserver.ubuntu.com
      keyid: E4D304DF
"""  # noqa: E501


@pytest.mark.user_data(USER_DATA)
def test_gpg_no_tty(client: IntegrationInstance):
    log = client.read_from_file("/var/log/cloud-init.log")
    to_verify = [
        "Running command ['gpg', '--no-tty', "
        "'--keyserver=keyserver.ubuntu.com', '--recv-keys', 'E4D304DF'] "
        "with allowed return codes [0] (shell=False, capture=True)",
        "Imported key 'E4D304DF' from keyserver 'keyserver.ubuntu.com'",
    ]
    verify_ordered_items_in_text(to_verify, log)
    verify_clean_log(log)
    verify_clean_boot(client)
    control_groups = client.execute(
        "systemd-cgls -u cloud-config.service 2>/dev/null | wc -l"
    ).stdout
    processes_in_cgroup = len(control_groups.split("\n"))
    assert processes_in_cgroup < 2, (
        "Cloud-init didn't clean up after itself, "
        f"cloud-config has remaining daemons:\n{control_groups}"
    )
