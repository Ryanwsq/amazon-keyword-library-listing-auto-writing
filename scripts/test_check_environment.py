"""Synthetic deployment probes; no websites, credentials or real business files."""
import subprocess
import unittest
from unittest.mock import patch

from check_environment import probe_version, probe_zip_commands, windows_path_issues


class EnvironmentTests(unittest.TestCase):
    def test_normal_unicode_names_are_allowed(self):
        self.assertEqual(windows_path_issues(['projects/a/知识库.md', 'projects/a/SKILL.md']), [])

    def test_reserved_and_escaping_names_are_rejected(self):
        for name in ['a/CON.md', 'a/Lpt1', '../a', '/a', 'a/name.', 'a/b:c', 'a\\b']:
            with self.subTest(name=name):
                self.assertTrue(windows_path_issues([name]))

    def test_case_collisions_include_directory_names(self):
        self.assertTrue(windows_path_issues(['Folder/a.md', 'folder/b.md']))

    def test_repeated_directory_is_not_a_collision(self):
        self.assertFalse(windows_path_issues(['folder/a.md', 'folder/b.md']))

    @patch('check_environment.shutil.which', return_value=None)
    def test_missing_command_is_not_success(self, _):
        self.assertFalse(probe_version('node', ['--version'])['ok'])

    @patch('check_environment.shutil.which', return_value='available')
    @patch('check_environment.command', return_value='v20.1.0')
    def test_version_floor(self, _, __):
        self.assertTrue(probe_version('node', ['--version'], (20, 0, 0))['ok'])
        self.assertFalse(probe_version('node', ['--version'], (22, 0, 0))['ok'])

    @patch('check_environment.shutil.which', return_value='available')
    @patch('check_environment.command', side_effect=subprocess.TimeoutExpired('probe', 15))
    def test_timeout_does_not_pass(self, _, __):
        self.assertFalse(probe_version('node', ['--version'])['ok'])

    @patch('check_environment.shutil.which', return_value=None)
    def test_missing_zip_is_not_silently_accepted(self, _):
        unzip, zip_cli = probe_zip_commands()
        self.assertFalse(unzip['ok'])
        self.assertFalse(zip_cli['ok'])


if __name__ == '__main__':
    unittest.main()
