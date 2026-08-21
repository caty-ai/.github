# CI exceptions for this repository

Every family repository is expected to run the shared gate set, including a macOS
test leg, so that shell logic is exercised against both GNU and BSD tooling. Where
this repository departs from that expectation, the departure is recorded here with
its reason. A recorded exception is auditable; an unrecorded gap is indistinguishable
from an oversight.

## No macOS test leg

**Status:** accepted, owner decision 2026-08-21.

**What is missing.** This repository requires three status checks on `main`, and none
of them is a macOS leg. The other ten family repositories require one.

**Why it is accepted.** The exception exists because there is no shell logic here for
a macOS leg to exercise. The full inventory of executable content in this repository is:

- `tools/check_publication_gate.py`
- `tools/gen_readme_svg.py`
- `tools/translate/translate_docs.py`

All three are Python. Everything else is Markdown documentation in four languages,
issue and pull-request templates, SVG assets, and `workflow-templates/` — files that
are *published for other repositories to copy*, not executed here.

The macOS leg earns its cost elsewhere in the family by catching GNU/BSD divergence
in shell: `sed -i`, `awk` regex dialect, `grep` flags, `date`, `stat`, locale and
collation behaviour. None of those surfaces exist in this repository, so a macOS leg
here would test the Python interpreter's portability rather than ours, at the cost of
a second runner on every pull request.

**What would end this exception.** Any of the following, at which point the macOS leg
should be added rather than argued about:

- A shell script (`.sh`, or any file whose shebang is a shell) enters this repository
  outside `workflow-templates/`.
- A workflow in `.github/workflows/` gains a `run:` block containing non-trivial shell
  logic — anything past a linear sequence of command invocations, i.e. any use of
  `sed`, `awk`, parameter expansion with defaults, or conditional/loop constructs.
- The Python tools begin shelling out to platform utilities rather than using the
  standard library.

**What this exception does not cover.** It is scoped to the macOS leg alone. The
gitleaks, history-check and publication-gate requirements apply here exactly as they
do everywhere else, and `workflow-templates/` — which other repositories adopt
verbatim — is not exempt from review because it is not executed here. A template that
ships broken BSD-incompatible shell to ten repositories is this repository's defect
even though this repository never runs it.
