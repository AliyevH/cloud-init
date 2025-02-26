# This file is part of cloud-init. See LICENSE file for license information.

import copy
import os

from cloudinit import atomic_helper, safeyaml, stages, util
from cloudinit.config.modules import Modules
from cloudinit.settings import PER_INSTANCE
from cloudinit.sources import NetworkConfigSource
from tests.unittests import helpers


class TestSimpleRun(helpers.FilesystemMockingTestCase):

    with_logs = True

    def setUp(self):
        super(TestSimpleRun, self).setUp()
        self.new_root = self.tmp_dir()
        self.replicateTestRoot("simple_ubuntu", self.new_root)

        # Seed cloud.cfg file for our tests
        self.cfg = {
            "datasource_list": ["None"],
            "runcmd": ["ls /etc"],  # test ALL_DISTROS
            "spacewalk": {},  # test non-ubuntu distros module definition
            "system_info": {
                "paths": {"run_dir": self.new_root},
                "distro": "ubuntu",
            },
            "write_files": [
                {
                    "path": "/etc/blah.ini",
                    "content": "blah",
                    "permissions": 0o755,
                },
            ],
            "cloud_init_modules": ["write_files", "spacewalk", "runcmd"],
        }
        cloud_cfg = safeyaml.dumps(self.cfg)
        util.ensure_dir(os.path.join(self.new_root, "etc", "cloud"))
        util.write_file(
            os.path.join(self.new_root, "etc", "cloud", "cloud.cfg"), cloud_cfg
        )
        self.patchOS(self.new_root)
        self.patchUtils(self.new_root)

    def test_none_ds_populates_var_lib_cloud(self):
        """Init and run_section default behavior creates appropriate dirs."""
        # Now start verifying whats created
        netcfg = {
            "version": 1,
            "config": [{"type": "physical", "name": "eth9"}],
        }

        def fake_network_config():
            return netcfg, NetworkConfigSource.FALLBACK

        self.assertFalse(os.path.exists("/var/lib/cloud"))
        initer = stages.Init()
        initer.read_cfg()
        initer.initialize()
        self.assertTrue(os.path.exists("/var/lib/cloud"))
        for d in ["scripts", "seed", "instances", "handlers", "sem", "data"]:
            self.assertTrue(os.path.isdir(os.path.join("/var/lib/cloud", d)))

        initer.fetch()
        self.assertFalse(os.path.islink("var/lib/cloud/instance"))
        iid = initer.instancify()
        self.assertEqual(iid, "iid-datasource-none")
        initer.update()
        self.assertTrue(os.path.islink("var/lib/cloud/instance"))
        initer._find_networking_config = fake_network_config
        self.assertFalse(
            os.path.exists("/var/lib/cloud/instance/network-config.json")
        )
        initer.apply_network_config(False)
        self.assertEqual(
            f"{atomic_helper.json_dumps(netcfg)}\n",
            util.load_text_file("/var/lib/cloud/instance/network-config.json"),
        )

    def test_none_ds_runs_modules_which_do_not_define_distros(self):
        """Any modules which do not define a distros attribute are run."""
        initer = stages.Init()
        initer.read_cfg()
        initer.initialize()
        initer.fetch()
        initer.instancify()
        initer.update()
        initer.cloudify().run(
            "consume_data",
            initer.consume_data,
            args=[PER_INSTANCE],
            freq=PER_INSTANCE,
        )

        mods = Modules(initer)
        (which_ran, failures) = mods.run_section("cloud_init_modules")
        self.assertFalse(failures)
        self.assertTrue(os.path.exists("/etc/blah.ini"))
        self.assertIn("write_files", which_ran)
        contents = util.load_text_file("/etc/blah.ini")
        self.assertEqual(contents, "blah")
        self.assertNotIn(
            "Skipping modules ['write_files'] because they are not verified on"
            " distro 'ubuntu'",
            self.logs.getvalue(),
        )

    def test_none_ds_skips_modules_which_define_unmatched_distros(self):
        """Skip modules which define distros which don't match the current."""
        initer = stages.Init()
        initer.read_cfg()
        initer.initialize()
        initer.fetch()
        initer.instancify()
        initer.update()
        initer.cloudify().run(
            "consume_data",
            initer.consume_data,
            args=[PER_INSTANCE],
            freq=PER_INSTANCE,
        )

        mods = Modules(initer)
        (which_ran, failures) = mods.run_section("cloud_init_modules")
        self.assertFalse(failures)
        self.assertIn(
            "Skipping modules 'spacewalk' because they are not verified on"
            " distro 'ubuntu'",
            self.logs.getvalue(),
        )
        self.assertNotIn("spacewalk", which_ran)

    def test_none_ds_runs_modules_which_distros_all(self):
        """Skip modules which define distros attribute as supporting 'all'.

        This is done in the module with the declaration:
        distros = [ALL_DISTROS]. runcmd is an example.
        """
        initer = stages.Init()
        initer.read_cfg()
        initer.initialize()
        initer.fetch()
        initer.instancify()
        initer.update()
        initer.cloudify().run(
            "consume_data",
            initer.consume_data,
            args=[PER_INSTANCE],
            freq=PER_INSTANCE,
        )

        mods = Modules(initer)
        (which_ran, failures) = mods.run_section("cloud_init_modules")
        self.assertFalse(failures)
        self.assertIn("runcmd", which_ran)
        self.assertNotIn(
            "Skipping modules 'runcmd' because they are not verified on"
            " distro 'ubuntu'",
            self.logs.getvalue(),
        )

    def test_none_ds_forces_run_via_unverified_modules(self):
        """run_section forced skipped modules by using unverified_modules."""

        # re-write cloud.cfg with unverified_modules override
        cfg = copy.deepcopy(self.cfg)
        cfg["unverified_modules"] = ["spacewalk"]  # Would have skipped
        cloud_cfg = safeyaml.dumps(cfg)
        util.ensure_dir(os.path.join(self.new_root, "etc", "cloud"))
        util.write_file(
            os.path.join(self.new_root, "etc", "cloud", "cloud.cfg"), cloud_cfg
        )

        initer = stages.Init()
        initer.read_cfg()
        initer.initialize()
        initer.fetch()
        initer.instancify()
        initer.update()
        initer.cloudify().run(
            "consume_data",
            initer.consume_data,
            args=[PER_INSTANCE],
            freq=PER_INSTANCE,
        )

        mods = Modules(initer)
        (which_ran, failures) = mods.run_section("cloud_init_modules")
        self.assertFalse(failures)
        self.assertIn("spacewalk", which_ran)
        self.assertIn(
            "running unverified_modules: 'spacewalk'", self.logs.getvalue()
        )

    def test_none_ds_run_with_no_config_modules(self):
        """run_section will report no modules run when none are configured."""

        # re-write cloud.cfg with unverified_modules override
        cfg = copy.deepcopy(self.cfg)
        # Represent empty configuration in /etc/cloud/cloud.cfg
        cfg["cloud_init_modules"] = None
        cloud_cfg = safeyaml.dumps(cfg)
        util.ensure_dir(os.path.join(self.new_root, "etc", "cloud"))
        util.write_file(
            os.path.join(self.new_root, "etc", "cloud", "cloud.cfg"), cloud_cfg
        )

        initer = stages.Init()
        initer.read_cfg()
        initer.initialize()
        initer.fetch()
        initer.instancify()
        initer.update()
        initer.cloudify().run(
            "consume_data",
            initer.consume_data,
            args=[PER_INSTANCE],
            freq=PER_INSTANCE,
        )

        mods = Modules(initer)
        (which_ran, failures) = mods.run_section("cloud_init_modules")
        self.assertFalse(failures)
        self.assertEqual([], which_ran)
