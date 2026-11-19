"""Q9: ahi-farm-connect takes the farm's connection in OrcaSlicer in the browser."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "convert" / "files" / "farm" / "ahi-farm-connect"
KEY = "ophqk_" + "k" * 43
URL = "http://hub.example.com:8480/apps/farm"
ADDON = '# /// script\n# ///\nVERSION = "0.15.0"\nAGENT_ID = "openprinthq"\n'


class FarmConnect(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.orca = self.root / ".config/OrcaSlicer"
        self.inbox = self.root / "Files/From the farm"
        self.inbox.mkdir(parents=True)
        self.orca.mkdir(parents=True)
        (self.orca / "OrcaSlicer.conf").write_text(json.dumps({"app": {"use_printer_agents": False,
                                                                       "preset_folder": "u123"}}))
        self.addon = self.root / "addon.py"
        self.addon.write_text(ADDON)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_it(self):
        env = dict(os.environ, AHI_CONFIG_ROOT=str(self.root), FILE_MANAGER_PATH=str(self.root / "Files"),
                   AHI_FARM_ADDON=str(self.addon))
        return subprocess.run([sys.executable, "-I", str(SCRIPT), "apply"], env=env, capture_output=True, text=True,
                              check=True)

    def connect(self, **extra):
        data = {"schema": 1, "url": URL, "key": KEY, "scope": "submit", "token_id": "t1", "actor_id": 3,
                "printers": [{"id": 1, "name": "H2D", "preset": "H2D - ArtisanHub Farm",
                              "inherits": "Bambu Lab H2D 0.4 nozzle"},
                             {"id": 3, "name": "MK4S", "preset": "MK4S - ArtisanHub Farm",
                              "inherits": "Prusa MK4S 0.4 nozzle"}],
                "skipped": [{"id": 5, "name": "voron01"}]}
        data.update(extra)
        (self.inbox / ".farm.json").write_text(json.dumps(data))

    def test_takes_a_connection(self):
        self.connect()
        self.run_it()
        self.assertFalse((self.inbox / ".farm.json").exists())          # it held the key
        applied = json.loads((self.inbox / ".farm-applied").read_text())
        self.assertNotIn(KEY, json.dumps(applied))
        self.assertEqual(applied["printers"][0]["preset"], "H2D - ArtisanHub Farm")
        self.assertEqual((applied["token_id"], applied["actor_id"], applied["scope"]), ("t1", 3, "submit"))
        self.assertNotIn("error", applied)
        # The add-on, with the farm's address granted as a person would grant it.
        plug = self.orca / "orca_plugins/openprinthq_print_queue.py"
        self.assertEqual((plug / "openprinthq_print_queue.py").read_text(), ADDON)
        state = json.loads((plug / ".install_state.json").read_text())
        self.assertEqual(state["installed_version"], "0.15.0")
        self.assertTrue(state["enabled"])
        self.assertIn("http://hub.example.com", state["permissions"]["network_http"])
        self.assertTrue(state["permissions"]["threading"])
        # The address and key for the add-on, in OrcaSlicer's environment and nowhere in its settings.
        env = (self.root / ".config/labwc/environment").read_text()
        self.assertIn(f"OPENPRINTHQ_URL={URL}\n", env)
        self.assertIn(f"OPENPRINTHQ_API_KEY={KEY}\n", env)
        self.assertEqual(os.stat(self.root / ".config/ahi-farm/env").st_mode & 0o777, 0o600)
        conf = json.loads((self.orca / "OrcaSlicer.conf").read_text())
        self.assertTrue(conf["app"]["use_printer_agents"])
        self.assertNotIn(KEY, (self.orca / "OrcaSlicer.conf").read_text())
        # One printer per farm printer, in the account's folder, kept out of account sync.
        machine = self.orca / "user/u123/machine"
        h2d = json.loads((machine / "H2D - ArtisanHub Farm.json").read_text())
        self.assertEqual((h2d["inherits"], h2d["printer_agent"], h2d["print_host"]),
                         ("Bambu Lab H2D 0.4 nozzle", "openprinthq", "ArtisanHub Farm"))
        self.assertNotIn("host_type", h2d)
        mk4s = json.loads((machine / "MK4S - ArtisanHub Farm.json").read_text())
        self.assertEqual(mk4s["host_type"], "octoprint")
        self.assertIn("sync_info = hold\n", (machine / "H2D - ArtisanHub Farm.info").read_text())

    def test_never_replaces_what_the_person_has(self):
        machine = self.orca / "user/u123/machine"
        machine.mkdir(parents=True)
        (machine / "H2D - ArtisanHub Farm.json").write_text('{"mine": true}')
        plug = self.orca / "orca_plugins/openprinthq_print_queue.py"
        plug.mkdir(parents=True)
        (plug / "openprinthq_print_queue.py").write_text('VERSION = "0.16.0"\n')
        (plug / ".install_state.json").write_text(json.dumps({"installed_version": "0.16.0", "enabled": False,
                                                              "permissions": {"network_http": ["https://x.org"]}}))
        self.connect()
        self.run_it()
        self.assertEqual((machine / "H2D - ArtisanHub Farm.json").read_text(), '{"mine": true}')
        self.assertEqual((plug / "openprinthq_print_queue.py").read_text(), 'VERSION = "0.16.0"\n')
        state = json.loads((plug / ".install_state.json").read_text())
        self.assertFalse(state["enabled"])                                  # turned off by the person: stays off
        self.assertEqual(state["permissions"]["network_http"],
                         ["https://x.org", "http://hub.example.com", "https://openprinthq.com"])

    def test_leaves_a_cloud_copy_alone(self):
        sub = self.orca / "orca_plugins/_subscribed/u123/abc"
        sub.mkdir(parents=True)
        (sub / "cloud_plugin-1.py").write_text(ADDON)
        self.connect()
        self.run_it()
        self.assertFalse((self.orca / "orca_plugins/openprinthq_print_queue.py").exists())
        self.assertIn("Orca Cloud", json.loads((self.inbox / ".farm-applied").read_text())["addon"])

    def test_printer_agents_are_turned_on_once(self):
        self.connect()
        self.run_it()
        conf = json.loads((self.orca / "OrcaSlicer.conf").read_text())
        conf["app"]["use_printer_agents"] = False                          # the person turns it off
        (self.orca / "OrcaSlicer.conf").write_text(json.dumps(conf))
        self.connect(token_id="t2")
        self.run_it()
        self.assertFalse(json.loads((self.orca / "OrcaSlicer.conf").read_text())["app"]["use_printer_agents"])

    def test_without_a_connection_it_puts_back_what_is_missing(self):
        self.connect()
        self.run_it()
        # The person signs in to another OrcaSlicer account: its folder gets the printers at the next start.
        conf = json.loads((self.orca / "OrcaSlicer.conf").read_text())
        conf["app"]["preset_folder"] = "u456"
        (self.orca / "OrcaSlicer.conf").write_text(json.dumps(conf))
        self.run_it()
        self.assertTrue((self.orca / "user/u456/machine/MK4S - ArtisanHub Farm.json").is_file())

    def test_a_bad_connection_is_dropped_and_reported(self):
        for bad in ({"url": "javascript:x"}, {"key": "nope\nOPENPRINTHQ_URL=evil"}, {"schema": 2}):
            self.connect(**bad)
            self.run_it()
            self.assertFalse((self.inbox / ".farm.json").exists())
            applied = json.loads((self.inbox / ".farm-applied").read_text())
            self.assertIn("error", applied)
            self.assertFalse((self.root / ".config/labwc/environment").exists())

    def test_names_that_are_not_file_names_are_skipped(self):
        self.connect(printers=[{"name": "x", "preset": "../../evil", "inherits": "Bambu Lab H2D 0.4 nozzle"},
                               {"name": "y", "preset": ".hidden", "inherits": "a"},
                               {"name": "z", "preset": "ok - ArtisanHub Farm", "inherits": "b/../c"}])
        self.run_it()
        machine = self.orca / "user/u123/machine"
        self.assertEqual(list(machine.glob("*")) if machine.exists() else [], [])

    def test_a_link_in_place_of_the_connection_is_not_followed(self):
        secret = self.root / "secret.json"
        secret.write_text(json.dumps({"schema": 1, "url": URL, "key": KEY}))
        os.symlink(secret, self.inbox / ".farm.json")
        self.run_it()
        self.assertFalse((self.root / ".config/labwc/environment").exists())
        self.assertIn("error", json.loads((self.inbox / ".farm-applied").read_text()))


if __name__ == "__main__":
    unittest.main()
