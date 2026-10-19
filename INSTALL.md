# Installing ccm

`ccm` is a small CLI that switches which model the **Claude Code CLI** uses
when it is pointed at **OpenRouter** (DeepSeek, Gemini, Qwen, … any model). It
also keeps the model aliases and subagent/background models in sync, and wires
up automatic image handling for text-only main models.

This guide takes you from zero to your first model switch.

---

## Requirements

| Requirement | Why |
|---|---|
| **Python 3.8+** | `ccm` is a single stdlib-only Python script; no pip packages. |
| **Claude Code CLI** (`claude` on `PATH`) | The thing ccm configures. Install per <https://code.claude.com/docs/en/setup> and check `claude --version`. |
| **OpenRouter API key** | Create one at <https://openrouter.ai/keys>. |
| **fish** (optional) | Gives automatic shell integration. bash/zsh work too, with one manual `source` line. |
| **fzf** (optional) | Nicer interactive picker; a numbered fallback is built in. |
| Network | Only for browsing/refreshing the OpenRouter model catalog. `ccm use`/`run` work offline. |

No `sudo` is needed and ccm never asks for or stores your API key.

---

## Step 1 — Point Claude Code at OpenRouter

Claude Code reads its API endpoint and credentials from environment variables.
Add these to your shell config:

**fish** (`~/.config/fish/config.fish`):

```fish
set -gx ANTHROPIC_BASE_URL "https://openrouter.ai/api"
set -gx ANTHROPIC_AUTH_TOKEN "sk-or-v1-..."
```

**bash** (`~/.bashrc`) or **zsh** (`~/.zshrc`):

```bash
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="sk-or-v1-..."
```

Open a new terminal afterwards and verify:

```console
$ echo $ANTHROPIC_BASE_URL
https://openrouter.ai/api
```

> **Already using Claude Code with OpenRouter?** Skip this step — ccm detects
> your current model environment and seeds presets from it.
>
> **Important:** use the same shell that launches `claude` for the install step
> below, so ccm can see your current model variables.

Optional: you may pre-set `ANTHROPIC_MODEL` (e.g.
`deepseek/deepseek-v4-pro-0813[1m]`). If you don't, ccm starts with sensible
DeepSeek presets and you can pick anything from the catalog with `ccm`.

---

## Step 2 — Clone and install

```console
$ git clone https://github.com/mcbainedv/ccm-claude-code-model-switcher.git
$ cd ccm-claude-code-model-switcher
$ ./install.sh
```

`install.sh` is a thin wrapper around `ccm install`. It:

* copies the CLI to `~/.local/bin/ccm` (no sudo),
* writes presets/config/env files under `~/.config/ccm/`,
* installs a fish wrapper + completions and appends one managed block to
  `~/.config/fish/config.fish` (a `config.fish.ccm-backup` is kept),
* seeds presets from your current Claude Code model variables.

It is **idempotent** — safe to run again to update. Optional flags:

```console
$ ./install.sh --refresh        # also refresh the OpenRouter model catalog
$ ./install.sh --with-picker    # labelled rows in Claude Code's in-session /model picker
$ ./bin/ccm install --help      # all install options
```

### Non-fish users (bash / zsh)

Install still works; the fish integration is skipped (or installed if fish is
present). Add one line to `~/.bashrc` / `~/.zshrc` so new shells get the model:

```bash
source ~/.config/ccm/env.sh
```

Then reload: `exec bash` / `exec zsh`. For a running shell, use
`eval "$(ccm env --shell sh)"`.

### Manual install (no installer script)

```console
$ install -Dm755 bin/ccm ~/.local/bin/ccm
$ ccm install --no-binary        # writes config/env/fish integration only
```

or run `ccm` straight from the checkout: `./bin/ccm --help`.

Make sure `~/.local/bin` is on your `PATH`.

---

## Step 3 — First run

Open a new terminal (the fish wrapper also updates the current shell after each
`ccm` command), then:

```console
$ ccm doctor        # health checks: claude CLI, env, shell integration, catalog
$ ccm               # interactive picker — choose a model, Enter sets the default
$ ccm use flash     # or switch directly (presets are seeded for you)
$ ccm list          # see presets
$ claude            # Claude Code starts on the selected model
```

If you have no presets yet (`ccm: config has no presets`):

```console
$ ccm search deepseek        # browse the OpenRouter catalog
$ ccm add pro deepseek/deepseek-v4-pro-0813 --label "DeepSeek V4 Pro"
$ ccm use pro
```

`ccm` appends the `[1m]` context suffix automatically for models with a 1M-token
window.

---

## Step 4 (optional) — Automatic image / vision handling

If you use a vision hook for a text-only main model (for example a
`~/.deepseek-vl/config.json` hook that describes images with Gemini via
OpenRouter), ccm detects it and routes images automatically:

* text-only main model → the hook stays enabled (Gemini describes images),
* main **and** subagent models accept images → `VISION_DISABLE=1`, hook skipped,
  images read natively,
* override the hook's model with `ccm vision model <id>`; check status with
  `ccm vision`; disable automation with `ccm vision auto off`.

Nothing else to configure — the hook keeps using its own API key/config.

---

## Updating

```console
$ cd ccm-claude-code-model-switcher
$ git pull
$ ./install.sh
```

Your presets and OpenRouter key are untouched. Run `ccm refresh` after updating
to pick up new models or image-capability data.

---

## Uninstalling

```console
$ ccm uninstall            # removes the CLI, fish wrapper/completions and config block
$ ccm uninstall --purge    # also deletes ~/.config/ccm (presets, env files, catalog cache)
```

`ccm uninstall` does not touch your shell config's API key/URL lines (ccm never
wrote them), and re-installing is easy.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ccm: command not found` | `~/.local/bin` is not on `PATH`. Add `set -gx PATH ~/.local/bin $PATH` (fish) or `export PATH="$HOME/.local/bin:$PATH"` (bash/zsh), or open a new terminal. |
| `ANTHROPIC_AUTH_TOKEN` / 401 errors | The env var is missing in the shell that launches `claude`. Add it per Step 1 and open a new terminal; check with `ccm doctor`. The key is never stored by ccm. |
| `claude: command not found` | Install Claude Code first (<https://code.claude.com/docs/en/setup>) or fix `PATH`. |
| Model didn't change | Environment is read when `claude` starts. Run `ccm use …` before launching, or use `/model <id>` inside a running session; `ccm current` shows whether this shell is in sync. |
| `ccm doctor` complains the shell env isn't loaded | New terminal, or `source ~/.config/ccm/env.fish` (fish) / `eval "$(ccm env --shell sh)"` (bash/zsh). |
| Model id not found / catalog stale | `ccm refresh`, then `ccm search <name>`; copy the exact id. |
| `[claude-code:unrecognized_model]` warning | Harmless: the OpenRouter model isn't an Anthropic built-in; requests still work. |
| Windows | Not supported natively; use WSL2. |

Run `ccm doctor` for a one-shot diagnosis. For usage details see
[README.md](README.md).
