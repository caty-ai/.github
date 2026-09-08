# Supporter loop

The reusable workflow implements the frozen [Supporter Reward Loop contract](https://github.com/caty-ai/x-collector/blob/epic/119/docs/supporter-loop/CONTRACT.md) (moves to `main` when the epic merges), v2.0. The caller initially selects `record-only`; enabling live delivery and approving the placeholder Japanese/English comment templates belong to owner checkpoint #4. The retired `backfill` input is absent; historical `ok-backfill` lines remain successful deliveries.

- `check-contents-decode.sh <workflow.yml> <fixtures-dir>` requires CR/LF stripping at every base64 decode, byte-compares wrapped Contents API fixtures, and verifies that plain decoding fails.
- `check-ledger.sh <ndjson files...>` prints the number of mode/action violations and succeeds only at zero.
- `check-decide-static.sh <workflow.yml>` checks the entire `decide` job for forbidden credentials, Telegram, and delivery writes, including implicit HTTP methods and Contents paths assembled from literals. Unresolved methods fail closed; folded YAML scalars in `decide` are rejected with rule `d` (use literal `|` blocks).
- Rule `b` also rejects unresolved positional/array argument bundles and curl multipart (`-F`/`--form`/`--form-string`) or configuration (`-K`/`--config`) options, even with an explicit GET or ledger target. A narrowly proven function-local empty argument vector followed only by quoted `-f`/`-F` field-pair appends is treated as gh field input; other builders fail closed. HTTP method matching is case-insensitive for the existing write and ledger rules.
- Rule `a-prime` resolves `env` keys including `name` independently of step metadata, so a literal traversal value cannot hide in a ledger filename. Existing variable-tail restrictions still apply.
- Rule `d` also rejects tagged `run` scalars and double-quoted `run` scalars containing hexadecimal/Unicode/NEL escapes or escaped quotes that can hide shell flags. Non-`run` block sequences and the `defaults.run.shell` mapping are accepted; executable `run` values retain the scalar checks.
- Rule `b` includes proven field-builder append values in the invocation before checking GraphQL mutations and write signals. Read-query field appends remain accepted. Curl short-option clusters containing uppercase `F` or `K` also fail closed; lowercase `-sfk` keeps its read semantics.
- Rule `d` rejects any backslash in a double-quoted `run` scalar, including YAML whitespace/control escapes. Single-quoted scalars retain literal backslashes and the existing shell checks.
- Curl short options are parsed left to right, including digit and `#` boolean flags. The first value-taking option consumes the cluster suffix or next word; `X` selects the case-insensitive method, `d`/`T` signal upload, and `F`/`K` remain fail-closed. Unknown short flags and unclassifiable methods fail closed under rule `b`; read clusters such as `-sSL4` and `-sfkL` stay clean. `gh api` retains its separate short-flag grammar.
- Rule `d` follows backslash escapes in collected double-quoted YAML values into executable statements, including workflow/job/step `env` and expanded `with` values. Unused escaped values and literal backslashes in single-quoted values remain accepted. File-backed GraphQL `query=@...` values fail closed under rule `b`, including field-builder appends combined with a visible read query.
- Rule `b` follows the explicit `xargs`, `parallel`, `env`, `command`, `exec`, `nice`, `nohup`, `timeout`, `sudo`, and `time` dispatcher grammar, including option arguments and nested prefixes. Shell `sh`/`bash -c` strings and `eval` arguments are unquoted and scanned again as command lists; `-c` supports combined flags (`-ec`, `-lc`, `-xc`), preceding `-o`/`-O` option operands, and a literal `--` before the body. Pipeline segments are inspected independently. Input-feeding dispatchers propagate argument provenance into nested shell/eval bodies: a write method or implicit write with a missing/placeholder target fails closed under `b` as an unresolvable target, regardless of producer text. Explicit GET controls remain read-only subject to the existing unresolved-bundle/configuration restrictions. Upstream `gh`/`curl` text passed into shell or xargs stdin still fails closed with reason `dispatch`. Unknown wrappers carrying `gh`/`curl` also fail closed. Literal `echo`/`printf` output remains data; shell substitutions retain conservative inspection.
- Every direct scalar value under a step’s `with:` is scanned as executable input, regardless of action name or input key (`command`, `args`, `inlineScript`, `cmd`, and unknown keys included), retaining rules `a`, `a-prime`, `b`, `c`, and existing `d` restrictions. Plain shell text in literal/folded scalar inputs remains executable; folded scalars also retain rule `d`. Only nested YAML sequences/mappings are treated as inert command data, including literal blocks whose contents form a YAML sequence/mapping. Block-data recognition checks every root entry; a root shell statement prevents suppression for the whole scalar. Nested data retains credential, Contents-path and collected escape-provenance checks, but does not trigger command rule `b`. Unsupported flow YAML and other existing structural restrictions still fail closed under `d`. Collected double-quoted input escapes retain their existing use-site checks.
- Backslash-newline continuations inside a shell word join without an inserted space, preserving curl option clusters, methods and endpoint/path words. An odd trailing backslash count escapes the newline; an even count leaves literal backslashes and a real statement boundary. Shell single quotes do not enable continuation. Whitespace before the continuation backslash keeps the word separator. Unsupported multiline/folded YAML and escaped double-quoted run scalars still fail closed under rule `d`; use literal `|` blocks for executable multiline scripts.
- `reconcile-audit.sh --mode record-only|live` reads JSON state from stdin and reports divergence. Its header documents the fixture schema and `--live-gh` collection interface. Missing or incomplete evidence fails closed. Record-only checks the reduced audit; live checks access, strangers, and both marker directions, including the manual allowlists. The owner-only checkpoint #4 zero-send audit uses `checkpoint4: true` in the stdin JSON to compare the baseline invitation set too; with `--live-gh` this additionally requires the invitation credential and still checks that the ledger credential receives 403.

`supporter-loop-selftest.yml` runs these scripts against clean and deliberately violating fixtures on pull requests touching this directory or either supporter-loop workflow. Fixtures are offline: no real credentials or GitHub writes are needed. The reusable workflow executes inline trusted code and never checks out the triggering ref. Additional fixture tests extract its actual jq transition, audit and SUPPORTERS.md models, verify the frozen interface, and execute decision/sweep code and extracted live helpers with fail-closed local API doubles. These tests never contact GitHub or use real credentials; they do not prove live API permissions.

The family roster is copied from `external-input-watch.yml`: **case-insensitive; identical token set**. The twin reference is in the new workflow only because issue #75 forbids changing existing workflows. Keep these copies synchronized in a separately authorized change.

Caller concurrency, caller secrets registration, baseline creation, Contributors wall and release notes belong to child #3/the owner. Baselines and manual allowlists live under `ledger/` in the reward repository; this change does not create them. Live API permissions, owner baselines, checkpoint approvals and actual zero-send evidence require owner verification outside fixture CI.

The append-only schema has no comment ID. Live collection cannot prove that an absent marker was removed by moderation rather than edited. For a still-readable thread it conservatively blocks cleanup until the owner records the accepted exception in `manual-markers-allowlist.json`; fixture audits also accept explicit `marker_deleted` evidence. Deleted/unreadable threads self-exempt. The Actions API 1,000-result cap also blocks cleanup conservatively, using only the per-workflow supporter-loop listing; unrelated workflows do not consume that cap.

Regeneration prepends the reward repository’s `SUPPORTERS.header.md` (owned by child #1) and fails closed if that header is missing or malformed.

## Contract v2.0

Every live sweep repairs stranded tier-1 projections first, then invites undelivered
stargazers in page order (never-invited before re-armed). All current-generation
`excluded-*` skips count regardless of key; `deferred-quota` never excludes.
Catch-up requires tier 1 enabled. Delivery lines use `<repo>:1:<id>` even on a
sweep; closures and sweep skips use `<repo>:sweep:<id>` with tier 0. Two expired
invitation cycles yield one `excluded-unresponsive` sweep skip. The actor's next
tier event can still re-invite normally.

The rolling quota counts actual successful invitation PUTs (`ok`, `ok-backfill`,
`ok-catchup`) plus recent pending invitations not represented by such a line.
`already-1` does not count. The window is `(now - 24 h, now]`, and `Q = max(0,
45 - B)` is re-evaluated before every sweep PUT. Waiting is limited to three
minutes cumulatively, with five-minute age-out lookahead. Event runs use the
platform quota directly. Record-only predicts the same batch using ledger-only B
(the unledgered pending term needs Administration and is unavailable).

Catch-up stops taking work at six minutes elapsed or 150 attempted/reserved
writes; queue entries reserve their closing ledger writes immediately. Audit,
marker and revoke loops also honor the elapsed deadline. Rotation, unconditional
regeneration, reminders and state/summary still run. All act content writes are
paced at least one second apart. Regeneration retries GET sha → fresh ledger read
→ render → PUT after each CAS conflict. Queued append lines follow that PUT;
a failed projection records errors and keeps those actors in backlog. An expired
tier-1 invitation disappears from the projection until re-invited; tier-2/3
recognition stays.

`ledger/<source_owner>--<source_repo>.sweep-state.json` is a derived owner latch:

```json
{"schema":1,"last_sweep_ts":"2026-09-08T00:00:00Z","backlog":0,
 "cancelled_runs":{"event":0,"schedule":0},
 "capacity_pct":{"stars":0,"supporters_md":0,"invitations":0},
 "alarm_state":{"stars_70":false,"supporters_md_70":false,
 "invitations_backlog":false,"red_run":false,"deferred_quota":false}}
```

Capacity values are fractions (0.7 = 70%): stars / 40000, published bytes / 1048576,
and B / 45. The watermark includes successful scheduled and manual sweeps.
Cancelled counts are informational and never gate delivery. Live sweeps send one
summary with delivered/backlog/cancelled/capacity/revoked counts and alarm
transitions only; missing/corrupt state starts from false. Record-only never
reads or writes this latch and never sends Telegram.

**422 launch gate:** `INVITE_LIMIT_PATTERN` is defined once in the reusable
workflow and is provisional: `invit.*(limit|exceed|too many|24 ?h|per day)|too many invit`.
Precondition: the reward repository must contain a valid `SUPPORTERS.header.md`; missing or malformed headers fail regeneration and the live sweep closed.

Before merge, the owner must capture a real invitation-limit response from the
approved probe, remove sensitive data, replace
`fixtures/workflow/invitation-limit-422.json` with that body, and pin the pattern
to its exact `.message`/`.errors[].message`/`.errors[].code` wording. Rerun
`python3 -B supporter-loop/fixtures/workflow/test-live-contract.py`; the real
limit body must match while `sha does not match` and generic `Validation Failed`
422 bodies remain errors. Events defer the entire invitation/comment/projection
bundle, while sweeps write one deferred skip and retain a green backlog.

New v2 fixtures: `test-catchup-model.py` covers candidate ordering, namespaces,
quota window edges, historical values, mode parity and projection re-arm;
`test-live-contract.py` runs actual catch-up/event/regeneration/quota/state helpers
for 422 bundles, exclusions, queue ordering, CAS re-read, pacing, budget and
alarm transitions. `test-decide.py`, `test-model.py`, and `test-interface.py`
retain the existing execution/model/interface checks. The four `clean-*` ledger
fixtures cover the new results and tier-1 sweep deliveries; the vocabulary
checker already accepts these values, so its implementation needs no change.
The stars scanner reuses rule `a` for PAT/secret references, rule `b` for a second
step, noncanonical GET or write, and rule `d` for nonliteral run blocks. The three
`violating-*-stars-*.yml` fixtures pin those boundaries. The 400000-character
handoff guard is unchanged; stars now has a ten-minute timeout. A local jq
`stable_unique_by` definition preserves page order because jq's builtin sorts.
