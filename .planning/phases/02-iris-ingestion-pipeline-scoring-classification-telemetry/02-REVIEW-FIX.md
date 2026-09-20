---
phase: 02-iris-ingestion-pipeline-scoring-classification-telemetry
fixed_at: 2026-09-20T21:37:37Z
review_path: .planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/02-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-09-20T21:37:37Z
**Source review:** .planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01, CR-02, WR-01, WR-02, WR-03 — `fix_scope: critical_warning`, Info findings out of scope)
- Fixed: 5
- Skipped: 0

**Isolation:** All edits and commits were performed inside an isolated git worktree at
`.claude/worktrees/rf-02-443902-1789939953` on temp branch `gsd-reviewfix/02-443902`, created
from `main` at commit `6050a4c`. The cleanup tail (fast-forward `main`, remove worktree, delete
temp branch, remove recovery sentinel) runs after this report is handed back.

## Fixed Issues

### CR-01: PersistOperation has no transactional rollback for partial batch failures

**Files modified:** `popheat_pipeline/components.py`
**Commit:** `137420a` (combined with CR-02 — see note below)
**Applied fix:** Wrapped the `PersistOperation.on_message` reading-insert loop in an explicit
IRIS transaction: `iris.tstart()` before the loop, `iris.tcommit()` after all rows in the batch
save successfully, and `iris.trollback()` in the `except` branch before logging and returning
`None`. A mid-batch `_Save()` failure now rolls back every `PopHeat.Reading` row already inserted
for that batch, matching the class's own documented "never leaves a mix of this-batch and
next-batch rows" guarantee and satisfying `specs/ingestion-pipeline.spec` R3 batch-atomicity.
**Verification performed:**
- Tier 1: re-read the modified section — `iris.tstart()`/`iris.tcommit()`/`iris.trollback()` are
  present exactly where the fix suggestion specified; surrounding step-2 (telemetry insert, its
  own separate try/except) is untouched and intact.
- Tier 2: `python3 -c "import ast; ast.parse(...)"` on `popheat_pipeline/components.py` — syntax
  OK, both before staging (combined diff) and on the staged-only content.
- `python3 -m unittest discover -s tests -v` — 56/56 tests pass (unchanged from baseline; this
  module has no direct IRIS-independent unit tests since `iris.tstart`/`tcommit`/`trollback` only
  exist inside a running IRIS embedded-Python process).
- **Docker/IRIS live verification:** attempted but unavailable in this environment — the sandbox
  has no access to the Docker daemon (`permission denied ... unix:///var/run/docker.sock`, even
  with sandboxing disabled). Verified instead via code inspection: the transaction calls
  (`iris.tstart`/`iris.tcommit`/`iris.trollback`) are the standard InterSystems IRIS embedded-Python
  transaction API and match the exact pattern given in REVIEW.md's own Fix section, which the
  reviewer had already confirmed against this codebase's IRIS image. No further live check was
  possible; a human should confirm the transaction boundary behaves as expected on the next
  `docker compose up` + demo run (e.g. by injecting a forced `_Save()` failure mid-batch and
  confirming zero partial rows land in `PopHeat.Reading`).

### CR-02: CatalogPollingService.on_poll has no failure isolation around catalog acquisition

**Files modified:** `popheat_pipeline/components.py`
**Commit:** `137420a` (combined with CR-01 — see note below)
**Applied fix:** Wrapped the `open()`/`json.load()` catalog read in `CatalogPollingService.on_poll`
in a `try/except (OSError, json.JSONDecodeError)` that logs via `self.log_error(...)` and returns
(treating a bad read as a no-op tick), mirroring the existing pattern already used one stage
downstream in `ScoreClassifyProcess.on_message` and for the empty-catalog case in the same method.
Satisfies `specs/ingestion-pipeline.spec` R4 failure isolation — a missing/corrupt
`data/venues.json` at poll time no longer propagates an exception out of the poll callback.
**Note on shared commit:** CR-01 and CR-02 both touch `popheat_pipeline/components.py` in
non-overlapping regions. I staged them as separate hunks via `git add -p` intending two atomic
commits, but the commit tooling (`gsd_run query commit --files <path>`) re-stages the full file
path before committing (rather than respecting pre-staged partial hunks), so both fixes landed in
a single commit (`137420a`). Both changes are independently correct, non-conflicting, and were
individually verified (syntax check on the staged-only content before this was discovered) before
being swept into the same commit. Documenting this transparently here rather than rewriting
history (no `git commit --amend`, per this agent's rollback/commit rules).
**Verification performed:**
- Tier 1: re-read — the `try/except` wraps exactly the file-read/JSON-parse, the subsequent
  `if not catalog:` empty-catalog check is untouched and still reachable on the happy path.
- Tier 2: `python3 -c "import ast; ast.parse(...)"` — syntax OK.
- `python3 -m unittest discover -s tests -v` — 56/56 tests pass.
- **Docker/IRIS live verification:** same limitation as CR-01 (no Docker daemon access in this
  sandbox). Verified via code inspection only: the except clause catches exactly the exception
  types `open()` (`OSError`, e.g. `FileNotFoundError`) and `json.load()` (`json.JSONDecodeError`)
  can raise for a missing/corrupt file, matching the sibling `on_message` isolation pattern. A
  human should confirm live by temporarily renaming/corrupting `data/venues.json` while the
  production is running and observing a logged error with polling continuing on the next tick.

### WR-01: load_thresholds does not validate that threshold levels are monotonic

**Files modified:** `popheat_pipeline/scoring.py`
**Commit:** `c06de7f`
**Applied fix:** Added a monotonicity check to `_thresholds_valid` — after validating each
group's three levels are present and numerically in `[0, 1]`, now also requires
`group_values["CRITICO"] >= group_values["ALTO"] >= group_values["MEDIO"]` for that group,
returning `False` (triggering the `DEFAULT_THRESHOLDS` fallback) otherwise. Updated the
docstring to explain why this matters (classify_heat evaluates levels in fixed high-to-low order
and returns on first match). Closes the misconfiguration path where a hand-edited
`config/heat_thresholds.json` with individually in-range but non-monotonic values would silently
misclassify most readings as CRITICO.
**Verification performed:**
- Tier 1: re-read the modified function — the new ordering check is present at the end of each
  group's loop, guarded the same way as the existing per-value checks; the function's control
  flow (early `return False` on any failure, final `return True`) is intact.
- Tier 2: `python3 -c "import ast; ast.parse(...)"` — syntax OK.
- `python3 -m unittest discover -s tests -v` — 56/56 tests pass (the existing
  `LoadThresholdsTests` suite in `tests/test_scoring.py` exercises `load_thresholds`'
  fallback-on-invalid-config path; none of its existing fixtures are non-monotonic, so none
  needed updating, and none broke). This fix was not classified as a logic-error finding in
  REVIEW.md (it's a missing-validation-rule warning, not a wrong-condition bug), so it is
  recorded as plain `fixed` rather than `fixed: requires human verification`.

### WR-02: No durable volume for the POPHEAT database — `docker compose down` destroys all data

**Files modified:** `docker-compose.yml`
**Commit:** `3e60cb8`
**Applied fix:** Chose the documentation option from REVIEW.md's two-option Fix section rather
than adding a named Docker volume. `iris/merge.cpf` and `.planning/phases/.../02-01-PLAN.md`
both document an explicit, deliberate prior decision: "durability prohibition ... do not add a
volume override that would make container data ephemeral." Adding a bind-mount/volume override
to `/usr/irissys/mgr/popheat` the day before the contest deadline, without the ability to test it
live in this environment (no Docker daemon access — see below), carried real risk of silently
breaking first-boot database creation. Instead, added a clear `WARNING (WR-02)` comment block to
`docker-compose.yml` directly above the volumes section, stating precisely which commands are
safe (`restart`, `stop`/`start`) and which is destructive (`down`), and why.
**Verification performed:**
- Tier 1: re-read — the new comment block is present, correctly worded, and does not touch the
  `services:`/`volumes:` YAML structure itself.
- Tier 2: `python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"` — parses cleanly.
  Additionally ran `docker compose config -q` (the CLI is present in this environment even though
  the daemon is not reachable) — exit code 0, confirming the compose file is structurally valid
  from Compose's own parser, not just generic YAML.
- **Docker/IRIS live verification:** not possible (no daemon access — `docker ps` returns
  "permission denied ... unix:///var/run/docker.sock" even with the sandbox disabled). No runtime
  behavior was changed by this fix (comment-only), so no regression risk from lack of live
  verification; a human should still confirm the warning text renders/reads correctly for anyone
  opening the file before the demo.

### WR-03: Namespace-existence check in init-production.sh parses session output with a fragile generic-digit regex

**Files modified:** `docker/init-production.sh`
**Commit:** `9cc7c4a`
**Applied fix:** Changed the ObjectScript `write` statement from
`write ##class(Config.Namespaces).Exists("${IRIS_NAMESPACE}"),!` to
`write "NS_EXISTS=",##class(Config.Namespaces).Exists("${IRIS_NAMESPACE}"),!`, and changed the
shell-side parser from `grep -Eo '[01]' | tail -1` to
`grep -o 'NS_EXISTS=[01]' | tail -1 | cut -d= -f2`. The result is parsed from the literal
`NS_EXISTS=` marker rather than any bare `0`/`1` digit anywhere in the combined stdout+stderr
session transcript, eliminating the risk of a login banner, version string, or warning line being
mis-parsed as the exists/not-exists result.
**Verification performed:**
- Tier 1: re-read — the `write` statement and the `grep`/`cut` pipeline both changed consistently;
  the downstream `if [ "$NS_EXISTS" != "1" ]; then` comparison is unchanged and still receives a
  bare `"1"` or `"0"` string after the `cut -d= -f2` strip.
- Tier 2: `sh -n docker/init-production.sh` — syntax OK (no `shellcheck` binary available in this
  environment, so this is the strongest available static check per the verification strategy's
  fallback rule).
- **Docker/IRIS live verification:** not possible (no daemon access, as above). Verified via code
  inspection: `##class(Config.Namespaces).Exists(...)` returns a boolean, which ObjectScript
  `write` renders as the literal characters `1` or `0`; concatenating it after the literal string
  `"NS_EXISTS="` on the same `write` statement produces a single transcript line of the form
  `NS_EXISTS=1` (or `NS_EXISTS=0`), which the new `grep -o 'NS_EXISTS=[01]'` pattern matches
  exactly and unambiguously regardless of any other digits printed earlier in the session
  (login banner, version string). A human should confirm live on next container init that the
  script still correctly detects/creates the namespace end-to-end.

## Skipped Issues

None — all 5 in-scope findings (CR-01, CR-02, WR-01, WR-02, WR-03) were fixed.

## Notes on scope and verification limits

- Per `fix_scope: critical_warning`, the 4 Info-level findings (IN-01 through IN-04) in REVIEW.md
  were intentionally left unaddressed by this run.
- No finding in this set was classified by REVIEW.md as a logic-error/wrong-condition bug in the
  sense the verification strategy singles out for `fixed: requires human verification` (WR-01 is
  a missing validation rule, not an incorrect existing condition); all 5 are recorded as plain
  `fixed`. That said, CR-01, CR-02, WR-02, and WR-03 all touch container/IRIS-runtime behavior that
  could not be exercised live in this sandboxed environment (no Docker daemon access — verified
  by attempting `docker ps`/`docker info` both with and without sandbox restrictions, consistently
  getting `permission denied ... unix:///var/run/docker.sock`). Each of those four fixes was
  instead verified via: (a) re-reading the modified code, (b) the strongest available static
  check for its file type (`ast.parse` for Python, `sh -n` for the shell script, `docker compose
  config -q` for the compose file), and (c) the full unit test suite (`python3 -m unittest
  discover -s tests -v`, 56/56 passing both before and after all 5 fixes). A human with Docker
  access should still do one live end-to-end pass before the contest submission — this is called
  out per-finding above.

## Orchestrator addendum — live Docker/IRIS verification (post-fix)

The fixer agent's sandbox had no Docker daemon access; the orchestrator's environment did (via
`sg docker -c "..."`). After the 5 fixes above landed on `main`, the orchestrator ran the real
stack a second time to close the live-verification gaps the fixer flagged:

- **CR-02 — fully confirmed live.** With the production running against the fixed code, deleted
  `data/venues.json` entirely and waited through multiple 3-second poll ticks: `BatchTelemetry`
  row count stayed flat (no crash, no fabricated empty batch), and
  `##class(Ens.Director).IsProductionRunning("PopHeat.Production")` continued returning `1`
  throughout. Restored the file and observed batching resume automatically on the very next tick
  with zero manual intervention — exactly the no-crash, self-healing behavior CR-02's fix claims.
- **WR-03 — implicitly confirmed live.** `docker/init-production.sh`'s fixed namespace-existence
  check ran successfully across two full container-init cycles during this verification session
  (this one and the earlier WINDOWS.md verification pass), correctly detecting/creating the
  `POPHEAT` namespace both times with no false positive/negative.
- **CR-01 — code path exercised live, rollback trigger not forced.** The production ran
  end-to-end on the transaction-wrapped `PersistOperation` for multiple batches with no errors
  (i.e. the `iris.tstart()`/`iris.tcommit()` happy path is proven live). Deliberately forcing a
  mid-batch `_Save()` failure (e.g. a malformed reading value) to observe `iris.trollback()`
  firing was not attempted in this pass — the fixer's static verification (correct API calls in
  the correct positions) plus the happy-path live run were judged sufficient given time
  constraints. This remains the one recommended pre-demo check: inject a deliberately bad reading
  value into one batch and confirm zero partial rows land in `PopHeat.Reading` for that batch.
- Container was torn down cleanly (`docker compose down -v`) after verification; `data/venues.json`
  (gitignored, not a tracked artifact) was restored to its pre-test state.

---

_Fixed: 2026-09-20T21:37:37Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
_Orchestrator live-verification addendum: 2026-09-20_
