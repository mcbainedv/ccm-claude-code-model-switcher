# ccm — Claude Code model switcher for OpenRouter

`ccm` switches which model the **Claude Code CLI** uses when it is pointed at
**OpenRouter** (for example a DeepSeek-only setup). One short terminal command
changes the default, and named presets make the usual choices instant.

> **New here?** [INSTALL.md](INSTALL.md) walks through setup from scratch:
> Claude Code + OpenRouter + ccm, then your first model switch.

```console
$ ccm use flash
✔ active model: DeepSeek V4 Flash
  primary   deepseek/deepseek-v4-flash-0731[1m]
  fast      deepseek/deepseek-v4-flash-0731[1m]  (haiku alias / background tasks)
  subagent  deepseek/deepseek-v4-flash-0731[1m]
```

Your OpenRouter API key is never read, copied or stored by `ccm`. It stays where
you configure it (for example `ANTHROPIC_AUTH_TOKEN` in
`~/.config/fish/config.fish`).

---

## Quick start

```console
$ git clone https://github.com/mcbainedv/ccm-claude-code-model-switcher.git
$ cd ccm-claude-code-model-switcher
$ ./install.sh              # or: ./bin/ccm install
```

Already running Claude Code through OpenRouter and just want the switcher?
Continue below. Setting up from scratch (OpenRouter key, Claude Code config,
fish/bash/zsh details) is covered in **[INSTALL.md](INSTALL.md)**.

Open a new terminal (or run `source ~/.config/ccm/env.fish`), then:

```console
$ ccm                       # interactive picker → set default
$ ccm use flash             # or switch directly
$ ccm                       # (re-open picker)
$ claude                    # Claude Code starts on the selected model
```

`./install.sh` is idempotent. It copies the CLI to `~/.local/bin/ccm`, writes
`~/.config/ccm/`, installs a fish wrapper + completions, and appends one managed
block to `~/.config/fish/config.fish` (a backup is kept). Remove the shell
integration with `ccm uninstall`; add `--purge` to also delete ccm's presets,
env files and catalog cache.

---

## Everyday commands

| Command | What it does |
| ------- | ------------ |
| `ccm` | Interactive picker (fzf if available): presets + the cached OpenRouter catalog. Sets the default. |
| `ccm use <preset>` | Switch the default model to a preset (`pro`, `flash`, …). |
| `ccm use <provider/model>` | Switch to any OpenRouter model id. `[1m]` is added automatically when the model has a ≥1M context window. |
| `ccm use <model> --no-1m` / `--1m` | Force the 200K / 1M context window suffix. |
| `ccm run [preset\|model] [-- <claude args>]` | Launch Claude Code on that model **for this session only**, without changing the default. If the first argument is not a preset or a model id it is passed to `claude` as an argument, so `ccm run "fix src/main.py"` works. |
| `ccm list` | List presets (`--json`, `--oneline` available). |
| `ccm current` | Show the active model and whether this shell has the right env loaded (`--json` available). |
| `ccm search <query>` | Search the OpenRouter catalog (id, context, price, name). `-i` picks one interactively. |
| `ccm add <name> <model>` | Save a model id as a preset (`--label`, `--small`, `--subagent`, `--description`). |
| `ccm remove <name>` | Delete a preset. |
| `ccm refresh` | Refresh the cached OpenRouter model catalog (470+ models). |
| `ccm env [preset] --shell fish\|sh` | Print ready-to-eval shell exports (for bash/zsh/IDE shells). |
| `ccm picker on\|off\|status` | Add/remove labelled rows in Claude Code's **in-session `/model` picker** (opt-in; edits `~/.claude/settings.json`, previous value restored on `off`). |
| `ccm vision` | Show automatic image/vision routing (`status`, `model <id>`, `auto on\|off`). |
| `ccm doctor` | Health checks (Claude CLI, env, fish hook, catalog, …). `--online` also tests the catalog request. |
| `ccm install` / `ccm uninstall [--purge]` | Wire up / remove the shell integration. |

Shorthand: `ccm flash` is the same as `ccm use flash`; `ccm deepseek/deepseek-v4.1-flash` is the same as `ccm use deepseek/deepseek-v4.1-flash`.

One-off examples:

```console
$ ccm run pro --resume            # resume this project's last session on the pro preset
$ ccm run "fix the failing test"  # current default preset, prompt passed to claude
$ ccm run --dry-run flash         # show the model/env/command without launching
```

---

## How it works

Claude Code reads its model from environment variables. `ccm` keeps them in
generated files and makes fish load them:

| Variable | Value set by ccm |
| -------- | ---------------- |
| `ANTHROPIC_MODEL` | the preset's **primary** model |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` / `..._SONNET_MODEL` | also the primary model (main session / plan mode) |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | the preset's **fast** model (background tasks, `/model haiku`) |
| `CLAUDE_CODE_SUBAGENT_MODEL` | the preset's **subagent** model |
| `ANTHROPIC_DEFAULT_*_MODEL_NAME` / `_DESCRIPTION` | friendly labels in the `/model` picker |
| `VISION_DISABLE` | `1` when the selected models see images natively (turns the vision hook off) |
| `VISION_MODEL` | only set when you override the hook's image-description model with `ccm vision model <id>` |

Flow:

```
ccm use flash
   ├─ writes ~/.config/ccm/config.json          (presets + active choice)
   ├─ writes ~/.config/ccm/env.fish  / env.sh   (exports above)
   ├─ fish function wrapper re-sources env.fish → current fish shell updated
   └─ new fish shells source it via one managed block in config.fish
```

Because `ANTHROPIC_MODEL` is set, a new `claude` process picks up the selected
model. Claude Code's own precedence applies (verified against Claude Code
**2.1.303**): `--model` flag → `ANTHROPIC_MODEL` → settings `model` →
`ANTHROPIC_DEFAULT_MODEL`.

### Triggering a model switch inside an already running session

Environment changes don't affect a running process, so inside Claude Code you
have these options:

1. **The built-in slash command** — works for any id, session-only:
   `/model deepseek/deepseek-v4-pro-0813[1m]`
2. **The built-in aliases**, mapped by ccm: `/model sonnet` or `/model opus`
   = main model, `/model haiku` = fast model.
3. **Labelled picker rows** (opt-in): `ccm picker on`, restart Claude Code, then
   `/model` shows "DeepSeek V4 Pro", "DeepSeek V4 Flash", … as selectable rows.
   Picker rows require Claude Code v2.1.242+ and are reverted by `ccm picker off`.
4. **Restart** the session after `ccm use`. `ccm run <preset>` is the quickest
   way to start a fresh session on a specific model.

> In-session `/model` picks are session-only here because `ANTHROPIC_MODEL` is
> set (Claude Code documents that env-var model selection wins at the next
> launch). `ccm use` is what persists your default.

### The `[1m]` suffix

Claude Code strips `[1m]` before sending the id to OpenRouter; the suffix tells
Claude Code to assume a 1M-token window instead of 200K. `ccm` appends it
automatically when the OpenRouter catalog reports `context_length >= 1,000,000`
(DeepSeek V4 Pro/Flash are 1M). Use `--no-1m` to opt out, `--1m` to force it for
a model the catalog doesn't know.

---

## Presets

`ccm install` seeds presets from whatever Claude Code model variables are
already in your environment, so it starts with `pro` and `flash` from your
current fish config. Add more with the catalog:

```console
$ ccm search v4-flash                 # find ids
$ ccm add flash-v41 deepseek/deepseek-v4.1-flash \
      --label "DeepSeek V4.1 Flash" --description "newest cheap flash"
$ ccm use flash-v41
```

A preset stores: primary model, fast/haiku model (defaults to the current fast
model), subagent model, and a label. Edit them with `ccm add ... --force` or in
`~/.config/ccm/config.json`. `ccm remove` deletes one; the last preset can't be
removed.

The OpenRouter catalog is cached for 24 h in
`~/.config/ccm/models-cache.json`; `ccm refresh` forces an update. Only
`refresh`, `search`, `pick` (model half) and `doctor --online` use the network —
plain `ccm use`/`list`/`current`/`run` work offline.

---

## Images (automatic vision routing)

DeepSeek models are text-only, so your existing vision hook
(`~/.deepseek-vl/config.json`, Gemini via OpenRouter) describes image Reads.
`ccm` now coordinates that hook with the selected model **automatically** — you
don't have to think about the vision model:

* **Text-only main model** (DeepSeek presets): the hook stays enabled and Gemini
  describes images. The hook's own configured model is used
  (`google/gemini-3.8-flash` in your setup); ccm does not override it.
* **Main model *and* subagent model can see images** (e.g. a Gemini preset with a
  vision-capable subagent): `ccm` exports `VISION_DISABLE=1`, Claude reads images
  natively, and the hook is skipped.
* **Capability unknown** (catalog not refreshed yet): the safe default is to
  keep the hook enabled, so image reads never break.

`ccm` stores nothing about the vision API key — the hook keeps using its own
config. Only the `VISION_MODEL` / `VISION_DISABLE` environment variables are
managed (and only when this automation is on).

```console
$ ccm current | grep vision
  vision    Gemini describes images (google/gemini-3.8-flash)

$ ccm use gemini-pro                 # a vision-capable preset
$ ccm current | grep vision
  vision    native (model reads images; vision hook disabled)

$ ccm vision                         # full status: hook config, image capability,
                                     # effective mode, exported env
$ ccm vision model google/gemini-3.8-pro   # optional: override the description model
$ ccm vision auto off                # stop managing VISION_* (hook keeps its own config)
$ ccm vision auto on                 # re-enable automation (default)
```

Per-preset override if you ever need it:
`ccm add <name> <model> --vision auto|native|describe` (also
`ccm use <raw-model> --vision …`). `auto` is the default.

Notes:

* The native/describe decision is made when Claude Code **starts**. Switching
  models inside a running session (`/model`, or the opt-in picker rows) does not
  re-evaluate it; the hook state from launch stays.
* The decision checks both the main model and the subagent model
  (`CLAUDE_CODE_SUBAGENT_MODEL`), because subagents can also read images.
* If you change the hook's config model, `ccm vision` reflects it immediately;
  `ccm refresh` keeps capability detection current.

---

## Files managed by ccm

| Path | Purpose | Removed by `ccm uninstall`? |
| ---- | ------- | --------------------------- |
| `~/.local/bin/ccm` | the CLI itself | yes (unless `--keep-binary`) |
| `~/.config/ccm/config.json` | presets + active choice | only with `--purge` |
| `~/.config/ccm/env.fish` / `env.sh` | generated model env vars | only with `--purge` |
| `~/.config/ccm/models-cache.json` | OpenRouter catalog cache | only with `--purge` |
| `~/.config/fish/functions/ccm.fish` | wrapper that re-sources env.fish | yes |
| `~/.config/fish/completions/ccm.fish` | fish completions | yes |
| `~/.config/fish/config.fish` | one ccm managed `source` block | yes (block only) |
| `~/.claude/settings.json` | `modelPicker` rows, only if `ccm picker on` | yes (restores previous value) |

Safety properties:

* Backups are made before editing: `config.fish.ccm-backup`,
  `settings.json.ccm-backup`. Note that `config.fish.ccm-backup` is a byte copy
  of your fish config, so it contains whatever secrets that file contains
  (e.g. your OpenRouter token). Delete the backup if you don't need it.
* `ccm` never touches `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`,
  `ANTHROPIC_API_KEY`, or any other non-model variable.
* Uninstalling removes only ccm's own block/files; your original model exports
  (if you leave them in `config.fish`) take effect again exactly as before. If
  `ccm install --force` replaced an unrelated `~/.local/bin/ccm`, uninstall puts
  that backup back.
* Concurrent `ccm` invocations are serialised with a file lock, so parallel
  `ccm add`/`ccm use` calls cannot lose presets.
* Labels and descriptions are sanitised before they are written into shell
  files, and model ids must look like `provider/model[:variant][[1m]]`, so a
  hostile model catalog entry cannot inject shell code.
* `ccm install` warns if your fish config still has old model exports before the
  ccm block. They are harmless (the ccm block is sourced last and overrides
  them), but you can delete them for a single source of truth.

---

## Requirements

* **Python 3.8+** (stdlib only; tested on 3.14)
* **fish** for the automatic shell integration (a fish wrapper function is
  installed). bash/zsh users can still use `ccm use` + `source ~/.config/ccm/env.sh`.
* **Claude Code CLI** on `PATH` (`claude`), with `ANTHROPIC_BASE_URL` pointing at
  `https://openrouter.ai/api` and `ANTHROPIC_AUTH_TOKEN`/`ANTHROPIC_API_KEY` set
  by your shell.
* **fzf** is optional (nicer `ccm` picker; a numbered fallback is built in).
* Network only for catalog refresh/search/pick.

---

## Troubleshooting

| Symptom | Cause / fix |
| ------- | ----------- |
| `[claude-code:unrecognized_model] {"model":"deepseek/..."}` printed at startup | Harmless information message: the model id is not one of Anthropic's built-in models. The request still works through OpenRouter (verified). |
| Context window reported as 200000 | Model id had no `[1m]` suffix. `ccm use <model> --1m` (auto-detection uses the OpenRouter catalog; run `ccm refresh` if the model is new). |
| `There's an issue with the selected model` | Model id is mistyped or not offered by OpenRouter. Find the exact id with `ccm search <name>`. |
| Auth/401 errors | `ANTHROPIC_AUTH_TOKEN`/`ANTHROPIC_API_KEY` missing from the environment that launches `claude`. ccm does not store it. Check with `ccm doctor`. |
| `ccm current` says the shell env is not loaded | Open a new fish terminal, or `source ~/.config/ccm/env.fish`. |
| `ccm: command not found` after install | `~/.local/bin` is not on `PATH`. `ccm install` warns about this; add it to fish's `PATH`. |
| In-session `/model` picker has no custom rows | Rows are opt-in: `ccm picker on`, then restart Claude Code. Requires Claude Code ≥ 2.1.242. |
| `ccm use` inside a running Claude Code session seems to do nothing | The running process keeps its env. Use `/model <id>` for that session, or restart (`ccm run …`). |
| Catalog search looks stale / model missing | `ccm refresh` (cache TTL is 24 h). |
| I want plain bash/zsh switching | `eval "$(ccm env <preset> --shell sh)"` before launching `claude`. |

Run `ccm doctor` for a one-shot diagnosis (exit code 1 only if something is
actually broken).

---

## Development & tests

```console
$ python3 -m unittest discover -s tests -v     # 40 tests, isolated fake $HOME
```

The suite covers seeding, preset switching, env-file generation, fish parsing,
`[1m]` auto-detection, run pass-through, install/idempotency/uninstall,
picker install/restore, automatic vision routing, doctor, error handling, and
the security/robustness regressions found by independent verification (see
[docs/verification.md](docs/verification.md)).

Layout:

```
bin/ccm                 the CLI (single file, stdlib only)
install.sh              convenience installer (calls `ccm install`)
tests/test_ccm.py       automated tests
docs/verification.md    independent verification summary
INSTALL.md              step-by-step install/setup guide
```

A ready-to-enable GitHub Actions workflow is included at
`docs/ci-tests.yml` (GitHub requires the `workflow` token scope to push it).

---

## References

Claude Code documentation used to design this tool:

* Model configuration / model env vars / `[1m]` context:
  <https://code.claude.com/docs/en/model-config>
* `modelPicker` (in-session picker rows):
  <https://code.claude.com/docs/en/settings-reference#modelpicker>
* Environment variables (incl. `ANTHROPIC_CUSTOM_MODEL_OPTION`,
  `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY`):
  <https://code.claude.com/docs/en/env-vars>
* Gateway model discovery (not used: it only keeps ids containing
  `claude`/`anthropic`, so it would hide DeepSeek ids):
  <https://code.claude.com/docs/en/llm-gateway-protocol#model-discovery>
* OpenRouter models API (catalog source): <https://openrouter.ai/api/v1/models>

---

## License

MIT — see [LICENSE](LICENSE).
