# Verification

`ccm` is tested in two layers before changes are published.

## 1. Unit / regression suite

```console
$ python3 -m unittest discover -s tests -v
```

The suite runs each scenario as a subprocess against a throwaway `$HOME`, so a
real user config is never touched. It covers:

* preset seeding, switching, add/remove and shorthand commands,
* generated `env.fish` / `env.sh` contents and fish parsing,
* `[1m]` context auto-detection and explicit overrides,
* `ccm run` argument pass-through and env delivery (mock `claude` binary),
* install idempotency, uninstall reversibility, stray-marker/ref-backed safety,
* the optional `/model` picker rows and their restore-on-uninstall,
* **automatic vision routing** (`VISION_DISABLE` / `VISION_MODEL` per preset),
* `ccm vision`, `ccm doctor`, error handling and secret hygiene.

Current status: **40/40 tests pass** on Python 3.14. A ready-to-enable GitHub
Actions workflow (Python 3.12 + fish) is included at `docs/ci-tests.yml`.

## 2. Independent adversarial verification

The tool was independently verified by a separate agent in throwaway
environments, with no access to the real user config and no billable model
calls:

* **39 scenarios / 544 checks**, including install/uninstall edge cases, fish
  quoting with spaces/quotes/`$`, `XDG_CONFIG_HOME`/`CCM_CONFIG_DIR` overrides,
  concurrent runs, corrupt configs, permissions, model-id variants
  (`:free`, `[1m]`, `[2m]`, `~provider/model`), picker restore, and secret
  hygiene.
* Final result: **39/39 scenarios pass**, 0 blockers, 0 regressions.
* Three major issues were found and fixed before release:
  1. `ccm uninstall` could be blocked by a corrupt `~/.claude/settings.json` —
     picker restore is now best-effort and uninstall always continues.
  2. Untrusted catalog names/labels could inject fish lines into `env.fish` —
     labels are sanitized and model ids strictly validated.
  3. `ccm run "fix src/main.py"` treated a slash-containing prompt as a model id
     — strict model-id detection now passes prose through to `claude`.
* Post-verification hardening added atomic installs, config file locking,
  safer uninstall/restore behaviour and more regression tests.

The detailed internal reports are development artifacts and are not part of this
repository; the reproducible unit suite above is the source of truth.
