#!/usr/bin/env python3
"""Regression tests for the publication gate."""

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import shutil
import tempfile


GATE_PATH = Path(__file__).with_name("check_publication_gate.py")
SPEC = importlib.util.spec_from_file_location("publication_gate_under_test", GATE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load publication gate from {GATE_PATH}")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

CLEAN_README = "# Public project\n"


def run_fixture(files):
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        for relative_path, content in files.items():
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        output = io.StringIO()
        with redirect_stdout(output):
            status = gate.main(root)
        return status, output.getvalue()


def assert_failure(label, files, expected_files=(), expected_message=None):
    status, output = run_fixture(files)
    assert status == 1, f"{label}: expected exit 1, got {status}: {output!r}"
    for expected_file in expected_files:
        marker = f"{expected_file}:1:"
        assert marker in output, f"{label}: missing {marker!r}: {output!r}"
    if expected_message is not None:
        assert expected_message in output, (
            f"{label}: missing {expected_message!r}: {output!r}"
        )


def assert_toxic_markdown(label, content):
    assert_failure(
        label,
        {"README.md": CLEAN_README, "toxic.md": content + "\n"},
        expected_files=("toxic.md",),
    )


def main():
    toxic_markdown_cases = (
        ("real name EN", "Sho" + "ji"),
        ("real name JA", "翔" + "さん"),
        ("approval record", "approved" + " by owner"),
        ("personal path", "/" + "Users" + "/alice/project"),
        ("tailnet address", "100." + "64.0.1"),
        ("localhost port", "local" + "host:8080"),
        ("loopback address", "127." + "0.0.1"),
        ("email", "alice" + "@" + "example.com"),
        ("private repository", "alpha-" + "loom"),
        ("personal GitHub URL", "https://github.com/" + gate.ACCOUNT_SLUG),
    )
    for label, content in toxic_markdown_cases:
        assert_toxic_markdown(label, content)

    assert_failure(
        "JSON and shell suffixes",
        {
            "README.md": CLEAN_README,
            "secrets.json": "{\"owner\": \"alice" + "@" + "example.com\"}\n",
            "deploy.sh": "cd /" + "Users" + "/alice/project\n",
        },
        expected_files=("secrets.json", "deploy.sh"),
    )

    assert_failure(
        "account-slug email",
        {
            "README.md": CLEAN_README,
            "slug-email.md": "bob@" + gate.ACCOUNT_SLUG + ".com\n",
        },
        expected_files=("slug-email.md",),
    )

    assert_failure(
        "empty corpus",
        {},
        expected_message="No files matched publication gate scan.",
    )
    assert_failure(
        "missing README anchor",
        {"notes.md": "# Public notes\n"},
        expected_message="README.md anchor is required for publication gate scan.",
    )

    status, output = run_fixture({"README.md": CLEAN_README})
    assert status == 0, f"clean corpus: expected exit 0, got {status}: {output!r}"
    assert output == "PASS (1 files scanned)\n", f"clean corpus: {output!r}"

    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        (root / "README.md").write_text(CLEAN_README, encoding="utf-8")
        copied_gate = root / "tools" / GATE_PATH.name
        copied_gate.parent.mkdir(parents=True)
        shutil.copyfile(GATE_PATH, copied_gate)
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            status = gate.main(root)
        output = output_buffer.getvalue()
        assert status == 0, (
            f"gate source copy: expected exit 0, got {status}: {output!r}"
        )
        assert output == "PASS (2 files scanned)\n", f"gate source copy: {output!r}"

    print("PASS (publication gate selftest)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
