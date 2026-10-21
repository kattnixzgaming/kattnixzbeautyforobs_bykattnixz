import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('kb_installer', Path(__file__).resolve().parents[1]/'installer/install.py')
installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.obs = self.root/'OBS'
        (self.obs/'bin/64bit').mkdir(parents=True)
        (self.obs/'bin/64bit/obs64.exe').write_bytes(b'fake')
        (self.obs/'obs-plugins/64bit').mkdir(parents=True)
        self.source = self.root/installer.DLL; self.source.write_bytes(b'new')
        self.target = self.obs/'obs-plugins/64bit'/installer.DLL
        self.backup = self.root/'backup'
        self.mock = patch.object(installer, 'obs_running', return_value=False); self.mock.start()

    def tearDown(self):
        self.mock.stop(); self.tmp.cleanup()

    def test_reject_wrong_obs_folder(self):
        with self.assertRaises(ValueError): installer.validate_obs(self.root)

    def test_backup_and_migrate_known_plugin(self):
        self.target.write_bytes(b'old')
        legacy = self.target.with_name('plugintemplate-for-obs.dll')
        legacy.write_bytes(b'kattbeauty_studio_filter')
        installer.commit(self.source, self.obs, self.backup)
        self.assertEqual(self.target.read_bytes(), b'new')
        self.assertEqual((self.backup/installer.DLL).read_bytes(), b'old')
        self.assertFalse(legacy.exists())
        self.assertTrue((self.backup/legacy.name).exists())

    def test_unrelated_template_is_untouched(self):
        legacy = self.target.with_name('plugintemplate-for-obs.dll'); legacy.write_bytes(b'unrelated')
        installer.commit(self.source, self.obs, self.backup)
        self.assertEqual(legacy.read_bytes(), b'unrelated')

    def test_failed_copy_restores_old_plugin(self):
        self.target.write_bytes(b'old')
        legacy = self.target.with_name('plugintemplate-for-obs.dll')
        legacy.write_bytes(b'kattbeauty_studio_filter')
        original = installer.shutil.copy2
        def fail_new(src, dest, *args, **kwargs):
        if Path(src).resolve() == self.source.resolve(): raise OSError('simulated copy failure')
            return original(src, dest, *args, **kwargs)
        with patch.object(installer.shutil, 'copy2', side_effect=fail_new):
            with self.assertRaises(OSError): installer.commit(self.source, self.obs, self.backup)
        self.assertEqual(self.target.read_bytes(), b'old')
        self.assertEqual(legacy.read_bytes(), b'kattbeauty_studio_filter')
