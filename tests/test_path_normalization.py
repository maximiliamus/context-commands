"""Portable export path checks; these fixtures are not participant responses."""

from pathlib import PurePosixPath, PureWindowsPath
import json
import unittest

from path_normalization import compile_path_replacements, replace_paths


class PathNormalizationTests(unittest.TestCase):
    def test_windows_paths_ignore_case_and_accept_both_separators(self):
        path = PureWindowsPath("D:/Private/User/Run")
        patterns = compile_path_replacements([(path, "<RUN_DIRECTORY>")])
        for spelling in ("d:/private/user/run", "d:\\PRIVATE\\USER\\RUN"):
            with self.subTest(spelling=spelling):
                self.assertEqual(replace_paths(spelling, patterns), "<RUN_DIRECTORY>")

    def test_json_escaping_and_unicode_paths(self):
        path = PureWindowsPath("D:/Private/\u041f\u0440\u043e\u0435\u043a\u0442/Run")
        patterns = compile_path_replacements([(path, "<RUN_DIRECTORY>")])
        for ascii_only in (True, False):
            payload = json.dumps({"path": str(path).replace("D:", "d:")}, ensure_ascii=ascii_only)
            self.assertEqual(json.loads(replace_paths(payload, patterns)), {"path": "<RUN_DIRECTORY>"})

    def test_file_uris_handle_encoded_and_unencoded_spaces(self):
        path = PureWindowsPath("D:/Private/Project with spaces/Run")
        patterns = compile_path_replacements([(path, "<RUN_DIRECTORY>")])
        for uri in ("file:///d:/private/project%20with%20spaces/run", "file:///d:/Private/Project with spaces/Run"):
            self.assertEqual(replace_paths(uri, patterns), "<RUN_DIRECTORY>")

    def test_child_paths_win_and_sibling_prefixes_do_not_match(self):
        root = PureWindowsPath("D:/Private/Run")
        patterns = compile_path_replacements([(root, "<RUN_DIRECTORY>"), (root / "t001", "<TRIAL>")])
        self.assertEqual(replace_paths("d:/private/run/t001/src/file.txt", patterns), "<TRIAL>/src/file.txt")
        self.assertEqual(replace_paths("D:/Private/Run-other", patterns), "D:/Private/Run-other")

    def test_posix_paths_retain_case_sensitivity(self):
        patterns = compile_path_replacements([(PurePosixPath("/private/Run"), "<RUN_DIRECTORY>")])
        self.assertEqual(replace_paths("/private/Run/file", patterns), "<RUN_DIRECTORY>/file")
        self.assertEqual(replace_paths("/private/run/file", patterns), "/private/run/file")


if __name__ == "__main__":
    unittest.main()
