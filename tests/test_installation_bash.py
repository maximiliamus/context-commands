"""Run the shared installation checks against Bash, with local curl fixtures."""

from pathlib import Path
import os
import shutil
import stat
import subprocess
import unittest

from test_installation import InstallationCases, MARKER, REPO, URL


def find_bash():
    if os.name == "nt":
        # Prefer Git Bash; the system32 bash.exe is a WSL launcher, not a shell
        # that can execute scripts directly in this Windows test environment.
        git = shutil.which("git")
        if git:
            candidate = Path(git).resolve().parent.parent / "bin/bash.exe"
            if candidate.is_file():
                return str(candidate)
        candidate = shutil.which("bash")
        if candidate and "system32" not in candidate.lower():
            return candidate
        return None
    return shutil.which("bash")


BASH = find_bash()


@unittest.skipUnless(BASH, "Bash or Git Bash is required for script integration checks")
class BashInstallationTests(InstallationCases, unittest.TestCase):
    shells = [BASH]
    language = "bash"
    extension = ".sh"
    install_script = "scripts/install.sh"
    update_script = "scripts/update.sh"

    def invoke(self, shell, script, folder, *, success=True, fail_download=False,
               via_url=False, fail_replace=False, fail_script_download=False,
               file_umask="022", bsd_stat_only=False):
        before = self.other_project_files(folder)
        source = r"""
set -euo pipefail
umask "$CC_TEST_UMASK"
curl() {
    local url=${!#}
    if [[ $url == "$CC_TEST_SCRIPT_URL" ]]; then
        if [[ $CC_TEST_FAIL_SCRIPT == 1 ]]; then
            printf 'touch unexpected-file\n'
            return 56
        fi
        cat -- "$CC_TEST_SCRIPT"
    elif [[ $url == "$CC_TEST_URL" ]]; then
        if [[ $CC_TEST_FAIL == 1 ]]; then
            # A partial transfer must never replace the local file.
            printf '# Context Commands\nPartial download'
            return 56
        fi
        cat -- "$CC_TEST_DOWNLOAD"
    else
        printf '%s\n' 'Unexpected download URL.' >&2
        return 1
    fi
}
mv() {
    if [[ $CC_TEST_FAIL_REPLACE == 1 ]]; then
        printf '%s\n' 'Simulated replacement failure.' >&2
        return 1
    fi
    command mv "$@"
}
stat() {
    if [[ $CC_TEST_BSD_STAT == 1 ]]; then
        if [[ $1 == -c ]]; then return 1; fi
        if [[ $1 == -f && $2 == %Lp ]]; then
            command stat -c %a "${!#}"
            return
        fi
    fi
    command stat "$@"
}
export -f curl mv stat
if [[ $CC_TEST_VIA_URL == 1 ]]; then
    eval "$CC_TEST_COMMAND"
else
    bash "$CC_TEST_SCRIPT"
fi
"""
        env = dict(os.environ, CC_TEST_URL=URL, CC_TEST_DOWNLOAD=self.download.as_posix(),
                   CC_TEST_SCRIPT=(REPO / script).as_posix(), CC_TEST_FAIL=str(int(fail_download)),
                   CC_TEST_SCRIPT_URL=URL.rsplit("/", 1)[0] + "/" + script,
                   CC_TEST_VIA_URL=str(int(via_url)), CC_TEST_COMMAND=self.commands[script],
                   CC_TEST_FAIL_REPLACE=str(int(fail_replace)),
                   CC_TEST_FAIL_SCRIPT=str(int(fail_script_download)),
                   CC_TEST_UMASK=file_umask, CC_TEST_BSD_STAT=str(int(bsd_stat_only)))
        result = subprocess.run([shell, "--noprofile", "--norc", "-c", source],
                                cwd=folder, env=env, capture_output=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.other_project_files(folder), before,
                         "The script changed files other than CONTEXT_COMMANDS.md or left temporary files")
        return result

    def test_scripts_have_valid_bash_syntax_and_lf_endings(self):
        for script in (self.install_script, self.update_script):
            with self.subTest(script=script):
                path = REPO / script
                self.assertNotIn(b"\r", path.read_bytes())
                result = subprocess.run([BASH, "-n", path.as_posix()], capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipIf(os.name == "nt", "Unix permission semantics are required")
    def test_install_respects_umask(self):
        for mask in ("022", "002", "077"):
            with self.subTest(mask=mask):
                folder = self.project()
                self.invoke(BASH, self.install_script, folder, file_umask=mask)
                self.assertEqual(stat.S_IMODE((folder / "CONTEXT_COMMANDS.md").stat().st_mode),
                                 0o666 & ~int(mask, 8))

    @unittest.skipIf(os.name == "nt", "Unix permission semantics are required")
    def test_update_preserves_file_permissions(self):
        for mode in (0o640, 0o444):
            with self.subTest(mode=oct(mode)):
                folder = self.project()
                target = folder / "CONTEXT_COMMANDS.md"
                target.write_bytes(("# Context Commands\n" + MARKER + "\n").encode("utf-8"))
                target.chmod(mode)
                self.invoke(BASH, self.update_script, folder, file_umask="077")
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), mode)

    def test_update_supports_bsd_stat_fallback(self):
        folder = self.project()
        target = folder / "CONTEXT_COMMANDS.md"
        target.write_bytes(("# Context Commands\n" + MARKER + "\n").encode("utf-8"))
        expected_mode = stat.S_IMODE(target.stat().st_mode)
        self.invoke(BASH, self.update_script, folder, bsd_stat_only=True)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), expected_mode)

    def test_failed_replacement_preserves_original_and_cleans_temporary_file(self):
        folder = self.project()
        original = ("# Context Commands\nOld content.\n" + MARKER +
                    "\n\n`mine`\nKeep my command.\n").encode("utf-8")
        target = folder / "CONTEXT_COMMANDS.md"
        target.write_bytes(original)
        result = self.invoke(BASH, self.update_script, folder, success=False, fail_replace=True)
        self.assertIn(b"Simulated replacement failure", result.stderr)
        self.assertEqual(target.read_bytes(), original)

    def test_readme_does_not_execute_incomplete_script_download(self):
        for script in (self.install_script, self.update_script):
            with self.subTest(script=script):
                folder = self.project(instructions=False)
                target = folder / "CONTEXT_COMMANDS.md"
                original = ("# Context Commands\nOld content.\n" + MARKER + "\n").encode("utf-8")
                if script == self.update_script:
                    target.write_bytes(original)
                self.invoke(BASH, script, folder, success=False, via_url=True, fail_script_download=True)
                if script == self.update_script:
                    self.assertEqual(target.read_bytes(), original)
                else:
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
