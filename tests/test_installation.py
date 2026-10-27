"""Shared installation checks and PowerShell execution with local downloads."""

from pathlib import Path
import base64
import os
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent
MARKER = "<!-- custom-context-commands -->"
URL = "https://raw.githubusercontent.com/maximiliamus/context-commands/master/CONTEXT_COMMANDS.md"
SHELLS = [path for name in ("pwsh", "powershell") if (path := shutil.which(name))]


class InstallationCases:
    def setUp(self):
        self.scratch = (REPO / ".benchmark").resolve()
        self.scratch.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="installation-", dir=self.scratch)
        self.root = Path(self.temporary.name).resolve()
        self.download = self.root / "download.md"
        self.download.write_bytes((REPO / "CONTEXT_COMMANDS.md").read_bytes())
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        commands = re.findall(r"## (Install|Update)\n.*?```" + self.language + r"\n(.*?)\n```", readme, re.S)
        self.assertEqual([name for name, _ in commands], ["Install", "Update"])
        self.commands = {"scripts/" + name.lower() + self.extension: command for name, command in commands}

    def tearDown(self):
        self.assertEqual(self.root.parent, self.scratch)
        self.temporary.cleanup()

    def project(self, *, instructions=True):
        folder = self.root / f"project with spaces {len(list(self.root.iterdir()))}"
        folder.mkdir()
        if instructions:
            (folder / "AGENTS.md").write_bytes(b"Existing instructions.\r\n")
        return folder

    def other_project_files(self, folder):
        # Include directories so even an empty configuration directory is detected.
        return {path.relative_to(folder).as_posix(): path.read_bytes() if path.is_file() else None
                for path in folder.rglob("*")
                if path != folder / "CONTEXT_COMMANDS.md" or not path.is_file()}

    def invoke(self, shell, script, folder, *, success=True, fail_download=False, via_url=False,
               lock_target=False):
        before = self.other_project_files(folder)
        # Only transport is mocked. File IO and the full shipped scripts run normally.
        source = r"""
$ErrorActionPreference = 'Stop'
function Invoke-RestMethod {
    param([string]$Uri)
    if ($Uri -eq $env:CC_TEST_SCRIPT_URL) {
        return [IO.File]::ReadAllText($env:CC_TEST_SCRIPT)
    }
    if ($Uri -ne $env:CC_TEST_URL) { throw 'Unexpected download URL.' }
    if ($env:CC_TEST_FAIL -eq '1') { throw 'Simulated download failure.' }
    return [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($env:CC_TEST_DOWNLOAD))
}
$fileLock = $null
try {
    if ($env:CC_TEST_LOCK -eq '1') {
        $fileLock = [IO.File]::Open($env:CC_TEST_TARGET, [IO.FileMode]::Open,
                                  [IO.FileAccess]::Read, [IO.FileShare]::Read)
    }
    if ($env:CC_TEST_VIA_URL -eq '1') {
        & ([scriptblock]::Create($env:CC_TEST_COMMAND))
    } else {
        & $env:CC_TEST_SCRIPT
    }
} finally {
    if ($null -ne $fileLock) { $fileLock.Dispose() }
}
"""
        encoded = base64.b64encode(source.encode("utf-16le")).decode("ascii")
        env = dict(os.environ, CC_TEST_URL=URL, CC_TEST_DOWNLOAD=str(self.download),
                   CC_TEST_SCRIPT=str(REPO / script), CC_TEST_FAIL=str(int(fail_download)),
                   CC_TEST_SCRIPT_URL=URL.rsplit("/", 1)[0] + "/" + script,
                   CC_TEST_VIA_URL=str(int(via_url)), CC_TEST_COMMAND=self.commands[script],
                   CC_TEST_LOCK=str(int(lock_target)), CC_TEST_TARGET=str(folder / "CONTEXT_COMMANDS.md"))
        result = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
            cwd=folder, env=env, capture_output=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.other_project_files(folder), before,
                         "The script changed files other than CONTEXT_COMMANDS.md or left temporary files")
        return result

    def test_install_in_empty_project_creates_only_commands_file(self):
        for shell in self.shells:
            with self.subTest(shell=shell):
                folder = self.project(instructions=False)
                self.invoke(shell, self.install_script, folder, via_url=True)
                self.assertEqual((folder / "CONTEXT_COMMANDS.md").read_bytes(), self.download.read_bytes())
                self.assertEqual({path.name for path in folder.iterdir()}, {"CONTEXT_COMMANDS.md"})

    def test_update_without_agent_instruction_files(self):
        for shell in self.shells:
            with self.subTest(shell=shell):
                folder = self.project(instructions=False)
                tail = "\n\n`mine`\nKeep my local command.\n"
                target = folder / "CONTEXT_COMMANDS.md"
                target.write_text("# Context Commands\nOld main content.\n" + MARKER + tail,
                                  encoding="utf-8", newline="\n")
                upstream = self.download.read_text(encoding="utf-8").partition(MARKER)[0] + MARKER
                self.invoke(shell, self.update_script, folder, via_url=True)
                self.assertEqual(target.read_bytes(), (upstream + tail).encode("utf-8"))
                self.assertEqual({path.name for path in folder.iterdir()}, {"CONTEXT_COMMANDS.md"})

    def test_full_lifecycle_preserves_other_project_files(self):
        for shell in self.shells:
            with self.subTest(shell=shell):
                folder = self.project()
                other_files = {
                    "AGENTS.md": b"Read @CONTEXT_COMMANDS.md and follow it.\r\nKeep existing rules.\r\n",
                    "CLAUDE.md": b"Existing configuration.\n",
                    ".github/copilot-instructions.md": b"Preserve instructions.\n",
                    "src/data.bin": bytes(range(256)),
                    "notes/custom-commands.txt": b"Unrelated legacy file. Do not load or modify.\n",
                }
                for name, content in other_files.items():
                    path = folder / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
                (folder / "empty-directory").mkdir()
                original_files = self.other_project_files(folder)
                self.invoke(shell, self.install_script, folder, via_url=True)
                target = folder / "CONTEXT_COMMANDS.md"
                main = target.read_bytes().split(MARKER.encode("utf-8"))[0]
                tail = "\r\n\r\n`mine`\r\nСохрани мою команду.\r\n"
                target.write_bytes(main + (MARKER + tail).encode("utf-8"))
                for version in (2, 3):
                    upstream = f"# Context Commands\n\nNew main content v{version}.\n\n" + MARKER
                    self.download.write_bytes((upstream + "\n").encode("utf-8"))
                    self.invoke(shell, self.update_script, folder, via_url=True)
                    self.assertEqual(target.read_bytes(), (upstream + tail).encode("utf-8"))
                    self.assertEqual(self.other_project_files(folder), original_files)

    def test_directory_at_target_is_untouched(self):
        for shell in self.shells:
            with self.subTest(shell=shell):
                folder = self.project()
                target = folder / "CONTEXT_COMMANDS.md"
                target.mkdir()
                (target / "keep.txt").write_bytes(b"Do not replace this directory.\n")
                for script in (self.install_script, self.update_script):
                    self.invoke(shell, script, folder, success=False)
                    self.assertTrue(target.is_dir())

    def test_install_from_url_and_refuse_overwrite(self):
        for shell in self.shells:
            with self.subTest(shell=shell):
                folder = self.project()
                target = folder / "CONTEXT_COMMANDS.md"
                self.invoke(shell, self.install_script, folder, via_url=True)
                expected = self.download.read_bytes()
                self.assertEqual(target.read_bytes(), expected)
                self.invoke(shell, self.install_script, folder, success=False)
                self.assertEqual(target.read_bytes(), expected)

    def test_update_preserves_exact_tail_and_is_repeatable(self):
        for shell in self.shells:
            for ending in ("\n", "\r\n"):
                with self.subTest(shell=shell, ending=repr(ending)):
                    folder = self.project()
                    tail = ending + ending + ending.join([
                        "`-->`", "`rnm`", "", "`aaa`", "После блока: назови допущение. 🧭  ",
                        "", "`cash`", "Keep $1, $&, backticks `x` and trailing spaces.  "])
                    current = ("# Context Commands\n\nOld built-in content.\n\n" + MARKER + tail).encode("utf-8")
                    target = folder / "CONTEXT_COMMANDS.md"
                    target.write_bytes(current)
                    upstream = "# Context Commands\n\nNew built-in content.\n\n" + MARKER
                    self.download.write_bytes((upstream + "\n\n`remote-only`\nDo not inherit.\n").encode("utf-8"))
                    expected = (upstream + tail).encode("utf-8")
                    self.invoke(shell, self.update_script, folder, via_url=True)
                    self.assertEqual(target.read_bytes(), expected)
                    self.invoke(shell, self.update_script, folder)
                    self.assertEqual(target.read_bytes(), expected)

    def test_update_empty_custom_section(self):
        for shell in self.shells:
            for tail in ("", "\n", "\r\n\r\n"):
                with self.subTest(shell=shell, tail=repr(tail)):
                    folder = self.project()
                    target = folder / "CONTEXT_COMMANDS.md"
                    target.write_bytes(("# Context Commands\nOld\n" + MARKER + tail).encode("utf-8"))
                    upstream = self.download.read_text(encoding="utf-8").partition(MARKER)[0] + MARKER
                    self.invoke(shell, self.update_script, folder)
                    self.assertEqual(target.read_bytes(), (upstream + tail).encode("utf-8"))

    def test_download_failure_does_not_create_or_change_file(self):
        for shell in self.shells:
            with self.subTest(shell=shell):
                folder = self.project()
                target = folder / "CONTEXT_COMMANDS.md"
                self.invoke(shell, self.install_script, folder, success=False, fail_download=True)
                self.assertFalse(target.exists())
                original = ("# Context Commands\n" + MARKER + "\n\n`aaa`\nMy command.\n").encode("utf-8")
                target.write_bytes(original)
                self.invoke(shell, self.update_script, folder, success=False, fail_download=True)
                self.assertEqual(target.read_bytes(), original)

    def test_install_accepts_utf8_bom_download(self):
        self.download.write_bytes(b"\xef\xbb\xbf" + self.download.read_bytes())
        for shell in self.shells:
            with self.subTest(shell=shell):
                folder = self.project()
                self.invoke(shell, self.install_script, folder, via_url=True)
                self.assertEqual((folder / "CONTEXT_COMMANDS.md").read_bytes(), self.download.read_bytes())

    def test_update_accepts_bom_and_preserves_custom_tail(self):
        tail = "\r\n\r\n`mine`\r\nKeep my Unicode rule: \u2713.\r\n"
        upstream = b"\xef\xbb\xbf" + ("# Context Commands\nNew reference.\n" + MARKER).encode("utf-8")
        self.download.write_bytes(upstream + b"\n")
        for shell in self.shells:
            for prefix in ("# Context Commands\nOld reference.\n", ""):
                with self.subTest(shell=shell, prefix=prefix):
                    folder = self.project()
                    target = folder / "CONTEXT_COMMANDS.md"
                    target.write_bytes(b"\xef\xbb\xbf" + (prefix + MARKER + tail).encode("utf-8"))
                    self.invoke(shell, self.update_script, folder)
                    self.assertEqual(target.read_bytes(), upstream + tail.encode("utf-8"))

    def test_symlinks_are_not_replaced_or_followed(self):
        for shell in self.shells:
            for broken in (False, True):
                with self.subTest(shell=shell, broken=broken):
                    folder = self.project()
                    original = folder / "original.md"
                    if not broken:
                        original.write_bytes(b"Do not overwrite the link target.\n")
                    target = folder / "CONTEXT_COMMANDS.md"
                    try:
                        target.symlink_to(original)
                    except (OSError, NotImplementedError) as error:
                        self.skipTest("Creating symlinks is unavailable: " + str(error))
                    for script in (self.install_script, self.update_script):
                        self.invoke(shell, script, folder, success=False)
                        self.assertTrue(target.is_symlink())
                        self.assertEqual(target.readlink(), original)
                        if not broken:
                            self.assertEqual(original.read_bytes(), b"Do not overwrite the link target.\n")

    def test_invalid_download_does_not_create_or_change_file(self):
        for shell in self.shells:
            for content in ("", "<html>Error page</html>\n", "# Context Commands\nMissing marker\n",
                            "# Context Commands\n" + MARKER + "\n" + MARKER + "\n"):
                with self.subTest(shell=shell, content=content):
                    self.download.write_text(content, encoding="utf-8")
                    folder = self.project()
                    target = folder / "CONTEXT_COMMANDS.md"
                    self.invoke(shell, self.install_script, folder, success=False)
                    self.assertFalse(target.exists())
                    original = ("# Context Commands\n" + MARKER + "\n`custom`\nPreserve.\n").encode("utf-8")
                    target.write_bytes(original)
                    self.invoke(shell, self.update_script, folder, success=False)
                    self.assertEqual(target.read_bytes(), original)

    def test_missing_file_or_invalid_local_marker_is_rejected(self):
        for shell in self.shells:
            with self.subTest(shell=shell):
                folder = self.project()
                target = folder / "CONTEXT_COMMANDS.md"
                self.invoke(shell, self.update_script, folder, success=False)
                self.assertFalse(target.exists())
                for content in ("# Context Commands\nOld version without marker.\n",
                                "# Context Commands\n" + MARKER + "\n" + MARKER + "\n"):
                    original = content.encode("utf-8")
                    target.write_bytes(original)
                    result = self.invoke(shell, self.update_script, folder, success=False)
                    self.assertIn(b"exactly one", result.stderr)
                    self.assertEqual(target.read_bytes(), original)


@unittest.skipUnless(SHELLS, "PowerShell is required for script integration checks")
class InstallationTests(InstallationCases, unittest.TestCase):
    shells = SHELLS
    language = "powershell"
    extension = ".ps1"
    install_script = "scripts/install.ps1"
    update_script = "scripts/update.ps1"

    @unittest.skipUnless(os.name == "nt", "Windows file sharing semantics are required")
    def test_locked_target_update_preserves_original_and_cleans_temporary_file(self):
        for shell in self.shells:
            with self.subTest(shell=shell):
                folder = self.project()
                original = ("# Context Commands\nOld main content.\n" + MARKER +
                            "\n\n`mine`\nKeep this command even when saving fails.\n").encode("utf-8")
                target = folder / "CONTEXT_COMMANDS.md"
                target.write_bytes(original)
                result = self.invoke(shell, self.update_script, folder, success=False, lock_target=True)
                self.assertIn(b"Replace", result.stderr, "The failure must occur during file replacement")
                self.assertEqual(target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
