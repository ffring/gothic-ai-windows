import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

path = Path(__file__).resolve().parents[2] / 'release/bundle-files/scripts/windows/game_profile.py'
spec = importlib.util.spec_from_file_location('game_profile', path)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)

class Profiles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.game = self.root / 'Steam Gothic II'
        (self.game / 'Data').mkdir(parents=True)
        (self.game / '_work').mkdir()
        for name in profile.REQUIRED:
            self.archive(name)

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, name, flags=0x50):
        data = bytearray(296)
        data[256:272] = b'PSVDSC_V2.00\r\n\r\n'
        data[292:296] = flags.to_bytes(4, 'little')
        (self.game/'Data'/name).write_bytes(data)

    def test_clean_install_keeps_original_path(self):
        self.assertEqual(profile.prepare(self.game, self.root/'profiles'), self.game.resolve())

    def test_mods_are_excluded_without_copying_or_changing_sources(self):
        self.archive('Union.vdf', 0xa0)
        self.archive('AB_Scripts.vdf')
        before = {p.name:p.read_bytes() for p in (self.game/'Data').iterdir()}
        result = profile.prepare(self.game, self.root/'profiles')
        self.assertEqual({p.name for p in (result/'Data').iterdir()}, set(profile.REQUIRED))
        for name in profile.REQUIRED:
            self.assertTrue(os.path.samefile(result/'Data'/name, self.game/'Data'/name))
        self.assertEqual((result/'_work').resolve(), (self.game/'_work').resolve())
        self.assertEqual(before, {p.name:p.read_bytes() for p in (self.game/'Data').iterdir()})
        self.assertEqual(profile.prepare(self.game, self.root/'profiles'), result)

    def test_missing_base_does_not_create_profile(self):
        (self.game/'Data'/'Worlds.vdf').unlink()
        with self.assertRaises(ValueError):
            profile.prepare(self.game, self.root/'profiles')
        self.assertFalse((self.root/'profiles').exists())

    def test_compressed_base_is_not_silently_accepted(self):
        self.archive('Worlds.vdf', 0xa0)
        with self.assertRaises(ValueError):
            profile.prepare(self.game, self.root/'profiles')

    def test_set_config_reaches_launcher_entrypoint(self):
        fake = self.root/'fake-launcher'/'gothic_launcher'
        fake.mkdir(parents=True)
        (fake/'__init__.py').write_text('',encoding='utf-8')
        (fake/'cli.py').write_text('import os,json,sys\nfrom pathlib import Path\ndef main():\n    Path(os.environ["GOTHIC_TEST_CONFIG_OUT"]).write_text(json.dumps(sys.argv[1:]),encoding="utf-8")\n',encoding='utf-8')
        output=self.root/'selected-game.json'
        env=dict(os.environ,PYTHONPATH=str(fake.parent),PYTHONUTF8='1',GOTHIC_TEST_CONFIG_OUT=str(output))
        subprocess.run([sys.executable,str(path),str(self.game),'--set-config'],env=env,check=True,capture_output=True)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8')),['config','set','game.dir',str(self.game.resolve())])

if __name__ == '__main__':
    unittest.main()
