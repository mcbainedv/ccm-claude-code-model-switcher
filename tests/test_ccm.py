#!/usr/bin/env python3
"""Tests for the ccm CLI.

Run with:  python3 -m unittest discover -s tests -v
Each test runs ccm as a subprocess against a throwaway $HOME, so the real
user configuration is never touched.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CCM = REPO / "bin" / "ccm"

SEED_ENV = {
    "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
    "ANTHROPIC_AUTH_TOKEN": "sk-or-test-token-not-real",
    "ANTHROPIC_MODEL": "deepseek/deepseek-v4-pro-0813[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek/deepseek-v4-pro-0813[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek/deepseek-v4-pro-0813[1m]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek/deepseek-v4-flash-0731[1m]",
    "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek/deepseek-v4-flash-0731[1m]",
}

FAKE_CLAUDE = """#!/bin/sh
echo "9.9.9 (Claude Code fake)"
"""


class CcmTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ccm-test-"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.claude_config = self.home / ".claude"
        self.claude_config.mkdir()
        self.fakebin = self.tmp / "fakebin"
        self.fakebin.mkdir()
        claude = self.fakebin / "claude"
        claude.write_text(FAKE_CLAUDE)
        claude.chmod(0o755)
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("CCM_") and not key.startswith("ANTHROPIC_")
        }
        self.env.update(SEED_ENV)
        self.env["HOME"] = str(self.home)
        self.env["CLAUDE_CONFIG_DIR"] = str(self.claude_config)
        self.env["PATH"] = (
            str(self.home / ".local/bin") + os.pathsep
            + str(self.fakebin) + os.pathsep + os.environ.get("PATH", "")
        )
        self.env["SHELL"] = "/usr/bin/fish" if shutil.which("fish") else "/bin/sh"
        self.env.pop("XDG_CONFIG_HOME", None)
        self.env.pop("NO_COLOR", None)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- helpers ---------------------------------------------------------
    def run_ccm(self, *args: str, check: bool = True, env_extra: dict | None = None):
        env = dict(self.env)
        if env_extra:
            env.update(env_extra)
        proc = subprocess.run(
            [sys.executable, str(CCM), *args],
            capture_output=True, text=True, env=env, timeout=120,
        )
        if check and proc.returncode != 0:
            self.fail(
                f"ccm {' '.join(args)} failed ({proc.returncode}):\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )
        return proc

    def config(self) -> dict:
        return json.loads((self.home / ".config/ccm/config.json").read_text())

    def write_cache(self, models: list[dict]) -> None:
        (self.home / ".config/ccm").mkdir(parents=True, exist_ok=True)
        (self.home / ".config/ccm/models-cache.json").write_text(json.dumps({
            "fetched_at": time.time(),
            "models": models,
        }))

    def seed_cache(self) -> None:
        self.write_cache([
            {
                "id": "deepseek/deepseek-v4-pro-0813",
                "name": "DeepSeek: DeepSeek V4 Pro 0813",
                "description": "",
                "context_length": 1048576,
                "pricing": {"prompt": 0.00000066, "completion": 0.00000198},
                "supports_tools": True,
                "output_modalities": ["text"],
                "input_modalities": ["text"],
            },
            {
                "id": "deepseek/deepseek-v4-flash-0731",
                "name": "DeepSeek: DeepSeek V4 Flash 0731",
                "description": "",
                "context_length": 1048576,
                "pricing": {"prompt": 0.00000015, "completion": 0.00000015},
                "supports_tools": True,
                "output_modalities": ["text"],
                "input_modalities": ["text"],
            },
            {
                "id": "deepseek/deepseek-v4.1-flash",
                "name": "DeepSeek: DeepSeek V4.1 Flash",
                "description": "",
                "context_length": 1048576,
                "pricing": {"prompt": 0.000000044, "completion": 0.00000008},
                "supports_tools": True,
                "output_modalities": ["text"],
                "input_modalities": ["text"],
            },
            {
                "id": "vendor/vision-model",
                "name": "Vendor: Vision Model",
                "description": "",
                "context_length": 128000,
                "pricing": {"prompt": 0.000001, "completion": 0.000002},
                "supports_tools": True,
                "output_modalities": ["text"],
                "input_modalities": ["text", "image"],
            },
            {
                "id": "vendor/legacy-chat",
                "name": "Vendor: Legacy Chat",
                "description": "",
                "context_length": 163840,
                "pricing": {"prompt": 0.00000025, "completion": 0.00000095},
                "supports_tools": True,
                "output_modalities": ["text"],
                "input_modalities": ["text"],
            },
        ])

    def fish_available(self) -> bool:
        return shutil.which("fish") is not None

    def fish_eval(self, script: str) -> str:
        proc = subprocess.run(
            ["fish", "-c", script], capture_output=True, text=True,
            env=self.env, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        return proc.stdout.strip()

    # -- basics ----------------------------------------------------------
    def test_version_and_help(self) -> None:
        proc = self.run_ccm("--version")
        self.assertIn("ccm 1.1.0", proc.stdout)
        proc = self.run_ccm("--help")
        self.assertIn("Claude Code model switcher", proc.stdout)
        self.assertIn("ccm use flash", proc.stdout)

    def test_list_seeds_from_environment(self) -> None:
        proc = self.run_ccm("list", "--json")
        payload = json.loads(proc.stdout)
        names = [preset["name"] for preset in payload["presets"]]
        self.assertEqual(names, ["pro", "flash"])
        active = payload["current"]
        self.assertEqual(active["preset"], "pro")
        self.assertEqual(active["primary"], SEED_ENV["ANTHROPIC_MODEL"])
        self.assertEqual(payload["presets"][0]["small"], SEED_ENV["ANTHROPIC_DEFAULT_HAIKU_MODEL"])

    def test_use_preset_writes_env_and_state(self) -> None:
        proc = self.run_ccm("use", "flash")
        self.assertIn("DeepSeek V4 Flash", proc.stdout)
        self.assertEqual(self.config()["current"], {"preset": "flash"})
        fish_env = (self.home / ".config/ccm/env.fish").read_text()
        self.assertIn("deepseek/deepseek-v4-flash-0731[1m]", fish_env)
        sh_env = (self.home / ".config/ccm/env.sh").read_text()
        self.assertIn("export ANTHROPIC_MODEL='deepseek/deepseek-v4-flash-0731[1m]'", sh_env)
        if self.fish_available():
            out = self.fish_eval(
                f"source {self.home}/.config/ccm/env.fish; echo $ANTHROPIC_MODEL"
            )
            self.assertEqual(out, "deepseek/deepseek-v4-flash-0731[1m]")

    def test_use_shorthand_and_unknown(self) -> None:
        proc = self.run_ccm("flash")
        self.assertIn("active model", proc.stdout)
        proc = self.run_ccm("does-not-exist", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unknown command or preset", proc.stderr)

    def test_use_model_auto_1m_and_no_1m(self) -> None:
        self.run_ccm("list")  # create config dir
        self.seed_cache()
        self.run_ccm("use", "vendor/legacy-chat")
        self.assertEqual(self.config()["current"]["primary"], "vendor/legacy-chat")
        self.run_ccm("use", "deepseek/deepseek-v4-pro-0813")
        self.assertEqual(
            self.config()["current"]["primary"], "deepseek/deepseek-v4-pro-0813[1m]"
        )
        self.run_ccm("use", "deepseek/deepseek-v4-pro-0813", "--no-1m")
        self.assertEqual(
            self.config()["current"]["primary"], "deepseek/deepseek-v4-pro-0813"
        )
        self.run_ccm("use", "vendor/legacy-chat", "--1m")
        self.assertEqual(self.config()["current"]["primary"], "vendor/legacy-chat[1m]")

    def test_use_rejects_non_model(self) -> None:
        proc = self.run_ccm("use", "not-a-model", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("does not look like an OpenRouter model", proc.stderr)

    def test_add_and_remove_preset(self) -> None:
        self.run_ccm("list")
        self.seed_cache()
        proc = self.run_ccm(
            "add", "cheap", "deepseek/deepseek-v4.1-flash",
            "--label", "DeepSeek V4.1 Flash", "--description", "newest cheap",
        )
        self.assertIn("preset 'cheap' saved", proc.stdout)
        self.assertIn("deepseek/deepseek-v4.1-flash[1m]", proc.stdout)
        payload = json.loads(self.run_ccm("list", "--json").stdout)
        self.assertIn("cheap", [preset["name"] for preset in payload["presets"]])
        self.run_ccm("remove", "cheap")
        payload = json.loads(self.run_ccm("list", "--json").stdout)
        self.assertNotIn("cheap", [preset["name"] for preset in payload["presets"]])
        missing = self.run_ccm("remove", "cheap", check=False)
        self.assertEqual(missing.returncode, 2)

    def test_env_command_outputs(self) -> None:
        proc = self.run_ccm("env", "flash", "--shell", "sh")
        self.assertIn("unset ANTHROPIC_MODEL", proc.stdout)
        self.assertIn("export ANTHROPIC_MODEL='deepseek/deepseek-v4-flash-0731[1m]'", proc.stdout)
        proc = self.run_ccm("env", "--shell", "fish")
        self.assertIn("set -gx ANTHROPIC_MODEL", proc.stdout)

    def test_search_and_refresh_use_cache(self) -> None:
        self.run_ccm("list")
        self.seed_cache()
        proc = self.run_ccm("search", "legacy")
        self.assertIn("vendor/legacy-chat", proc.stdout)
        self.assertIn("163K", proc.stdout)
        payload = json.loads(self.run_ccm("search", "flash", "--json").stdout)
        ids = [item["id"] for item in payload]
        self.assertIn("deepseek/deepseek-v4-flash-0731", ids)
        self.assertIn("deepseek/deepseek-v4.1-flash", ids)

    def test_current_json_reports_env(self) -> None:
        self.run_ccm("use", "flash", check=True)
        payload = json.loads(self.run_ccm("current", "--json").stdout)
        self.assertFalse(payload["env_matches"])  # parent env still has pro
        self.assertEqual(payload["configured"]["preset"], "flash")
        loaded = self.run_ccm(
            "current", "--json",
            env_extra={
                "ANTHROPIC_MODEL": "deepseek/deepseek-v4-flash-0731[1m]",
                "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek/deepseek-v4-flash-0731[1m]",
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek/deepseek-v4-flash-0731[1m]",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek/deepseek-v4-flash-0731[1m]",
                "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek/deepseek-v4-flash-0731[1m]",
            },
        )
        self.assertTrue(json.loads(loaded.stdout)["env_matches"])

    def test_run_dry_run_does_not_exec(self) -> None:
        proc = self.run_ccm("run", "--dry-run", "flash")
        self.assertIn("model: deepseek/deepseek-v4-flash-0731[1m]", proc.stdout)
        self.assertIn("command:", proc.stdout)
        self.assertIn("claude", proc.stdout)
        proc = self.run_ccm("run", "--dry-run", "--", "-p", "hello")
        self.assertIn("'-p' 'hello'", proc.stdout)
        proc = self.run_ccm("run", "--print-env", "flash")
        self.assertIn("export ANTHROPIC_MODEL=", proc.stdout)

    # -- install / uninstall --------------------------------------------
    def write_fish_config(self) -> None:
        fish_config = self.home / ".config/fish/config.fish"
        fish_config.parent.mkdir(parents=True, exist_ok=True)
        fish_config.write_text(
            "# user fish config\n"
            'set -gx ANTHROPIC_BASE_URL "https://openrouter.ai/api"\n'
            'set -gx ANTHROPIC_AUTH_TOKEN "secret-test-token"\n'
            f'set -gx ANTHROPIC_MODEL "{SEED_ENV["ANTHROPIC_MODEL"]}"\n'
        )

    def test_install_is_idempotent_and_uninstall_reverses(self) -> None:
        self.write_fish_config()
        proc = self.run_ccm("install")
        self.assertIn("installed", proc.stdout)
        fish_config = self.home / ".config/fish/config.fish"
        text = fish_config.read_text()
        self.assertEqual(text.count(">>> ccm managed block >>>"), 1)
        self.assertIn("source ", text)
        self.assertTrue((self.home / ".config/fish/functions/ccm.fish").exists())
        self.assertTrue((self.home / ".config/fish/completions/ccm.fish").exists())
        self.assertTrue((self.home / ".local/bin/ccm").exists())
        self.assertTrue((self.home / ".config/fish/config.fish.ccm-backup").exists())
        # install again: still exactly one block
        self.run_ccm("install")
        self.assertEqual(
            fish_config.read_text().count(">>> ccm managed block >>>"), 1
        )
        if self.fish_available():
            out = self.fish_eval(
                f"source {fish_config}; echo $ANTHROPIC_MODEL"
            )
            self.assertEqual(out, SEED_ENV["ANTHROPIC_MODEL"])
            # the fish wrapper re-sources env.fish after `ccm use`
            out = self.fish_eval(
                f"source {self.home}/.config/fish/functions/ccm.fish; "
                f"ccm use flash >/dev/null; echo $ANTHROPIC_MODEL"
            )
            self.assertEqual(out, "deepseek/deepseek-v4-flash-0731[1m]")
        # uninstall removes ccm's block, restores the user's original exports
        self.run_ccm("uninstall")
        text = fish_config.read_text()
        self.assertNotIn(">>> ccm managed block >>>", text)
        self.assertIn("ANTHROPIC_MODEL", text)
        self.assertFalse((self.home / ".config/fish/functions/ccm.fish").exists())
        self.assertFalse((self.home / ".local/bin/ccm").exists())

    def test_install_with_picker_and_off_restores(self) -> None:
        settings = self.claude_config / "settings.json"
        settings.write_text('{"theme": "dark", "modelPicker": {"options": [{"model": "keep/me"}]}}')
        self.run_ccm("install")
        self.run_ccm("picker", "on")
        payload = json.loads(settings.read_text())
        self.assertEqual(payload["theme"], "dark")
        labels = [row["label"] for row in payload["modelPicker"]["options"]]
        self.assertTrue(any(label.startswith("DeepSeek V4 Pro") for label in labels), labels)
        self.assertTrue(payload["modelPicker"]["replaceBuiltInOptions"])
        self.run_ccm("picker", "off")
        restored = json.loads(settings.read_text())
        self.assertEqual(restored["modelPicker"], {"options": [{"model": "keep/me"}]})
        self.assertTrue((self.claude_config / "settings.json.ccm-backup").exists())

    def test_picker_refreshes_after_preset_changes(self) -> None:
        self.run_ccm("install")
        self.run_ccm("picker", "on")
        settings = self.claude_config / "settings.json"
        before = json.loads(settings.read_text())["modelPicker"]["options"]
        self.run_ccm("add", "legacy", "vendor/legacy-chat", "--label", "Legacy Chat")
        after = json.loads(settings.read_text())["modelPicker"]["options"]
        self.assertNotEqual(before, after)
        self.assertTrue(any(row["label"] == "Legacy Chat" for row in after), after)
        self.run_ccm("use", "flash")
        synced = json.loads(settings.read_text())["modelPicker"]["options"]
        self.assertTrue(any(row["model"].startswith("deepseek/deepseek-v4-flash") for row in synced), synced)

    # -- diagnostics -----------------------------------------------------
    def test_doctor_offline(self) -> None:
        self.run_ccm("install")
        proc = self.run_ccm("doctor", check=False)
        self.assertIn("[PASS] ccm config", proc.stdout)
        self.assertIn("[PASS] claude CLI", proc.stdout)
        self.assertNotIn("[FAIL]", proc.stdout)
        self.assertEqual(proc.returncode, 0)

    def test_completions(self) -> None:
        self.run_ccm("list")
        proc = self.run_ccm("completions", "fish")
        self.assertIn("complete -c ccm", proc.stdout)
        proc = self.run_ccm("__presets")
        self.assertEqual(proc.stdout.split(), ["pro", "flash"])

    # -- verifier regression tests --------------------------------------
    def test_run_prose_prompt_is_passed_to_claude(self) -> None:
        proc = self.run_ccm("run", "--dry-run", "please fix src/main.py")
        self.assertNotIn("model: please fix", proc.stdout)
        self.assertIn("model: deepseek/deepseek-v4-pro-0813[1m]", proc.stdout)
        self.assertIn("'please fix src/main.py'", proc.stdout)
        proc = self.run_ccm("run", "--dry-run", "deepseek/deepseek-v4-flash-0731[1m]")
        self.assertIn("model: deepseek/deepseek-v4-flash-0731[1m]", proc.stdout)

    def test_env_labels_cannot_inject_shell_lines(self) -> None:
        self.run_ccm("list")
        evil = "Evil\nset -gx CCM_PWNED 'yes'\n#"
        proc = self.run_ccm(
            "add", "evil", "vendor/legacy-chat",
            "--label", evil, "--description", evil,
        )
        self.assertIn("saved", proc.stdout)
        self.run_ccm("use", "evil")
        fish_env = (self.home / ".config/ccm/env.fish").read_text()
        for line in fish_env.splitlines():
            self.assertFalse(line.strip().startswith("set -gx CCM_PWNED"), fish_env)
        self.assertNotIn("\nset -gx CCM_PWNED", fish_env)
        self.assertEqual(len(fish_env.splitlines()),
                         len([ln for ln in fish_env.splitlines() if ln.startswith(("#", "set "))]))
        if self.fish_available():
            out = self.fish_eval(
                f"source {self.home}/.config/ccm/env.fish; "
                f"set -q CCM_PWNED; and echo pwned; or echo clean"
            )
            self.assertEqual(out, "clean")

    def test_use_rejects_slash_only(self) -> None:
        wrong = self.run_ccm("use", "/", check=False)
        self.assertEqual(wrong.returncode, 2)
        prose = self.run_ccm("use", "please fix src/main.py", check=False)
        self.assertEqual(prose.returncode, 2)

    def test_uninstall_not_blocked_by_corrupt_claude_settings(self) -> None:
        self.run_ccm("install")
        self.run_ccm("picker", "on")
        settings = self.claude_config / "settings.json"
        settings.write_text("{ definitely not json")
        proc = self.run_ccm("uninstall", check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("skipped /model picker restore", proc.stdout)
        fish_config = self.home / ".config/fish/config.fish"
        if fish_config.exists():
            self.assertNotIn(">>> ccm managed block >>>", fish_config.read_text())
        self.assertFalse((self.home / ".config/fish/functions/ccm.fish").exists())
        self.assertFalse((self.home / ".local/bin/ccm").exists())

    def test_add_bootstraps_empty_presets_config(self) -> None:
        path = self.home / ".config/ccm/config.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            "version": 1, "settings": {}, "presets": [], "current": {},
        }))
        proc = self.run_ccm("add", "first", "vendor/legacy-chat")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(self.run_ccm("list", "--json").stdout)
        self.assertIn("first", [preset["name"] for preset in payload["presets"]])

    def test_install_refusal_writes_nothing(self) -> None:
        self.write_fish_config()
        fish_before = (self.home / ".config/fish/config.fish").read_text()
        target = self.home / ".local/bin/ccm"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("#!/bin/sh\necho unrelated\n")
        target.chmod(0o755)
        proc = self.run_ccm("install", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("does not look like ccm", proc.stderr)
        self.assertFalse((self.home / ".config/ccm/config.json").exists())
        self.assertEqual((self.home / ".config/fish/config.fish").read_text(), fish_before)

    def test_uninstall_restores_previous_binary_from_force_backup(self) -> None:
        target = self.home / ".local/bin/ccm"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("#!/bin/sh\necho foreign-binary\n")
        target.chmod(0o755)
        self.run_ccm("install", "--force")
        self.assertIn("ccm-claude-model-switcher", target.read_text())
        self.run_ccm("uninstall")
        self.assertTrue(target.exists())
        self.assertIn("foreign-binary", target.read_text())

    def test_uninstall_removes_config_fish_it_created(self) -> None:
        self.run_ccm("install")
        self.assertTrue((self.home / ".config/fish/config.fish").exists())
        self.run_ccm("uninstall")
        self.assertFalse((self.home / ".config/fish/config.fish").exists())

    def test_concurrent_adds_keep_every_preset(self) -> None:
        self.run_ccm("list")
        procs = [
            subprocess.Popen(
                [sys.executable, str(CCM), "add", f"p{index}", "vendor/legacy-chat"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env,
            )
            for index in range(6)
        ]
        for proc in procs:
            out, err = proc.communicate(timeout=120)
            self.assertEqual(proc.returncode, 0, out + err)
        payload = json.loads(self.run_ccm("list", "--json").stdout)
        names = [preset["name"] for preset in payload["presets"]]
        for index in range(6):
            self.assertIn(f"p{index}", names)

    def test_doctor_online_with_corrupt_config_is_fail(self) -> None:
        path = self.home / ".config/ccm/config.json"
        path.parent.mkdir(parents=True)
        path.write_text("{ broken")
        proc = self.run_ccm("doctor", "--online", check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("[FAIL] network", proc.stdout)
        self.assertIn("config is unavailable", proc.stdout)

    # -- post-verification hardening tests -------------------------------
    def test_run_help_and_dry_run_without_claude_binary(self) -> None:
        empty_bin = self.tmp / "emptybin"
        empty_bin.mkdir(exist_ok=True)
        env_no_claude = {"PATH": str(empty_bin)}
        proc = self.run_ccm("run", "--help")
        self.assertIn("usage: ccm run", proc.stdout)
        self.assertIn("--dry-run", proc.stdout)
        proc = self.run_ccm("run", "--dry-run", env_extra=env_no_claude)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("model:", proc.stdout)
        self.assertIn("command:", proc.stdout)

    def test_install_twice_is_byte_identical(self) -> None:
        self.write_fish_config()
        self.run_ccm("install")
        first = (self.home / ".config/fish/config.fish").read_text()
        self.run_ccm("install")
        second = (self.home / ".config/fish/config.fish").read_text()
        self.assertEqual(first, second)
        self.assertFalse(second.startswith("\n"))

    def test_install_stray_marker_writes_nothing(self) -> None:
        fish_config = self.home / ".config/fish/config.fish"
        fish_config.parent.mkdir(parents=True, exist_ok=True)
        content = "# user config\n# >>> ccm managed block >>>\nset -gx KEEP yes\n"
        fish_config.write_text(content)
        proc = self.run_ccm("install", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("without a matching end marker", proc.stderr)
        self.assertFalse((self.home / ".local/bin/ccm").exists())
        self.assertFalse((self.home / ".config/ccm/config.json").exists())
        self.assertEqual(fish_config.read_text(), content)

    def test_picker_labels_are_sanitised_from_config(self) -> None:
        self.run_ccm("list")
        config_file = self.home / ".config/ccm/config.json"
        payload = json.loads(config_file.read_text())
        payload["presets"][0]["label"] = "Evil\nset -gx CCM_PICKER y #"
        payload["presets"][0]["description"] = "desc\nset -gx CCM_DESC y #"
        config_file.write_text(json.dumps(payload))
        self.run_ccm("install", "--with-picker")
        settings = json.loads((self.claude_config / "settings.json").read_text())
        for row in settings["modelPicker"]["options"]:
            self.assertNotIn("\n", row["label"])
            self.assertNotIn("\n", row.get("description", ""))

    def test_add_with_corrupt_picker_settings_warns_but_saves(self) -> None:
        self.run_ccm("install", "--with-picker")
        (self.claude_config / "settings.json").write_text("{ broken")
        proc = self.run_ccm("add", "partial", "vendor/legacy-chat")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("preset 'partial' saved", proc.stdout)
        self.assertIn("could not update /model picker settings", proc.stdout)
        payload = json.loads(self.run_ccm("list", "--json").stdout)
        self.assertIn("partial", [preset["name"] for preset in payload["presets"]])

    # -- automatic vision routing ----------------------------------------
    def test_vision_auto_describe_for_text_only_models(self) -> None:
        self.run_ccm("list")
        self.seed_cache()
        self.run_ccm("use", "flash")
        fish_env = (self.home / ".config/ccm/env.fish").read_text()
        self.assertIn("# vision: Gemini describes images", fish_env)
        self.assertNotIn("set -gx VISION_DISABLE", fish_env)
        self.assertNotIn("set -gx VISION_MODEL", fish_env)  # hook config is respected
        payload = json.loads(self.run_ccm("current", "--json").stdout)
        vision = payload["vision"]
        self.assertTrue(vision["managed"])
        self.assertEqual(vision["mode"], "describe")
        self.assertIs(vision["primary_supports_images"], False)
        self.assertIn("vision    Gemini describes images", self.run_ccm("current").stdout)

    def test_vision_auto_native_for_vision_capable_models(self) -> None:
        self.run_ccm("list")
        self.seed_cache()
        self.run_ccm(
            "add", "vis", "vendor/vision-model",
            "--subagent", "vendor/vision-model",
        )
        self.run_ccm("use", "vis")
        fish_env = (self.home / ".config/ccm/env.fish").read_text()
        self.assertIn("set -gx VISION_DISABLE '1'", fish_env)
        self.assertNotIn("set -gx VISION_MODEL", fish_env)
        payload = json.loads(self.run_ccm("current", "--json").stdout)
        self.assertEqual(payload["vision"]["mode"], "native")
        self.assertIs(payload["vision"]["primary_supports_images"], True)
        self.assertIn("native", self.run_ccm("current").stdout)

    def test_vision_explicit_describe_override(self) -> None:
        self.run_ccm("list")
        self.seed_cache()
        self.run_ccm(
            "add", "vis2", "vendor/vision-model",
            "--subagent", "vendor/vision-model", "--vision", "describe",
        )
        self.run_ccm("use", "vis2")
        fish_env = (self.home / ".config/ccm/env.fish").read_text()
        self.assertNotIn("set -gx VISION_DISABLE", fish_env)
        payload = json.loads(self.run_ccm("current", "--json").stdout)
        self.assertEqual(payload["vision"]["mode"], "describe")

    def test_vision_model_override_and_hook_detection(self) -> None:
        hook_cfg = self.home / ".deepseek-vl/config.json"
        hook_cfg.parent.mkdir(parents=True)
        hook_cfg.write_text(json.dumps({"model": "google/gemini-3.8-flash"}))
        self.run_ccm("list")
        self.seed_cache()
        payload = json.loads(self.run_ccm("current", "--json").stdout)
        self.assertEqual(payload["vision"]["vision_model"], "google/gemini-3.8-flash")
        self.assertTrue(str(payload["vision"]["hook_config"]).endswith(".deepseek-vl/config.json"))
        self.run_ccm("use", "flash")
        fish_env = (self.home / ".config/ccm/env.fish").read_text()
        self.assertNotIn("set -gx VISION_MODEL", fish_env)  # hook's own config wins by default
        proc = self.run_ccm("vision", "model", "google/gemini-3.8-pro")
        self.assertIn("vision model set", proc.stdout)
        fish_env = (self.home / ".config/ccm/env.fish").read_text()
        self.assertIn("set -gx VISION_MODEL 'google/gemini-3.8-pro'", fish_env)
        payload = json.loads(self.run_ccm("current", "--json").stdout)
        self.assertEqual(payload["vision"]["vision_model"], "google/gemini-3.8-pro")

    def test_vision_auto_off_leaves_variables_alone(self) -> None:
        self.run_ccm("list")
        self.seed_cache()
        self.run_ccm("vision", "auto", "off")
        fish_env = (self.home / ".config/ccm/env.fish").read_text()
        self.assertNotIn("set -gx VISION_MODEL", fish_env)
        self.assertNotIn("set -gx VISION_DISABLE", fish_env)
        payload = json.loads(self.run_ccm("current", "--json").stdout)
        self.assertFalse(payload["vision"]["managed"])
        self.run_ccm("vision", "auto", "on")
        payload = json.loads(self.run_ccm("current", "--json").stdout)
        self.assertTrue(payload["vision"]["managed"])

    def test_vision_status_command(self) -> None:
        self.run_ccm("list")
        self.seed_cache()
        proc = self.run_ccm("vision")
        self.assertIn("Vision handling", proc.stdout)
        self.assertIn("managed by ccm  yes", proc.stdout)
        self.assertIn("hook config", proc.stdout)
        self.assertIn("active preset", proc.stdout)

    def test_use_vision_flag_for_raw_model(self) -> None:
        self.run_ccm("list")
        self.seed_cache()
        self.run_ccm(
            "use", "vendor/vision-model",
            "--subagent", "vendor/vision-model", "--vision", "native",
        )
        fish_env = (self.home / ".config/ccm/env.fish").read_text()
        self.assertIn("set -gx VISION_DISABLE '1'", fish_env)
        payload = json.loads(self.run_ccm("current", "--json").stdout)
        self.assertEqual(payload["vision"]["mode"], "native")

    def test_run_env_includes_vision_routing(self) -> None:
        self.run_ccm("list")
        self.seed_cache()
        proc = self.run_ccm("run", "--print-env", "flash")
        self.assertIn("# vision: Gemini describes images", proc.stdout)
        self.assertNotIn("export VISION_DISABLE", proc.stdout)
        dry = self.run_ccm("run", "--dry-run", "flash")
        self.assertIn("vision: Gemini describes images", dry.stdout)

    def test_corrupt_config_is_friendly(self) -> None:
        path = self.home / ".config/ccm/config.json"
        path.parent.mkdir(parents=True)
        path.write_text("{ not json")
        proc = self.run_ccm("list", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("cannot parse", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
