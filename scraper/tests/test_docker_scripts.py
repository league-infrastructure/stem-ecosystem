"""Tests for scraper/docker/load-secrets and make-secrets.sh (run via bash)."""

import base64
import os
import shutil
import subprocess
from pathlib import Path

import pytest

DOCKER = Path(__file__).resolve().parent.parent / "docker"
LOAD = DOCKER / "load-secrets"
MAKE = DOCKER / "make-secrets.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")

KEYS = [
    "DO_SPACES_ACCESS_KEY",
    "DO_SPACES_SECRET_KEY",
    "ANTHROPIC_API_KEY",
    "LEAGUESYNC_API_KEY",
    "TBA_KEY",
]


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def run_load(bundle, extra_env=None, var_name=None, probe=("A", "B", "C")):
    """Source load-secrets in bash, then print the probe variables NUL-separated."""
    env = {"PATH": os.environ["PATH"]}
    if bundle is not None:
        env[var_name or "SCRAPER_SECRETS_B64"] = bundle
    if var_name:
        env["SCRAPER_SECRETS_VAR"] = var_name
    env.update(extra_env or {})
    printer = " ".join(f'printf "%s\\0" "${{{p}-<unset>}}";' for p in probe)
    script = f'. "{LOAD}" || exit 7; {printer}'
    proc = subprocess.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True
    )
    values = proc.stdout.split("\0")[:-1] if proc.returncode == 0 else []
    return proc, dict(zip(probe, values))


def test_round_trip():
    proc, v = run_load(b64("A=one\nB=two\n"))
    assert proc.returncode == 0
    assert v == {"A": "one", "B": "two", "C": "<unset>"}


def test_quotes_comments_blanks():
    bundle = b64("# comment\n\nA=\"quoted val\"\nB='single'\nC=\"mismatch'\n")
    proc, v = run_load(bundle)
    assert proc.returncode == 0
    assert v == {"A": "quoted val", "B": "single", "C": "\"mismatch'"}


def test_special_characters_not_expanded():
    secret = "p@ss w0rd=x$HOME`id`$(id)!*"
    proc, v = run_load(b64(f"A={secret}\n"), probe=("A",))
    assert proc.returncode == 0
    assert v["A"] == secret


def test_existing_env_wins():
    proc, v = run_load(b64("A=bundle\nB=bundle\n"), extra_env={"A": "preset"})
    assert v["A"] == "preset"
    assert v["B"] == "bundle"


def test_unset_and_empty_bundle_noop():
    for bundle in (None, ""):
        proc, v = run_load(bundle)
        assert proc.returncode == 0
        assert v["A"] == "<unset>"
        assert proc.stderr == ""


def test_alternate_var_name():
    proc, v = run_load(b64("A=alt\n"), var_name="MY_BUNDLE")
    assert v["A"] == "alt"


def test_no_trailing_newline_and_crlf():
    proc, v = run_load(b64("A=one\r\nB=two"))
    assert v["A"] == "one" and v["B"] == "two"


@pytest.mark.parametrize(
    "bad",
    [
        "!!!not base64!!!",
        b64("A=1\nnot a pair\n"),
        b64("1BAD=secretvalue\n"),
        b64("A B=secretvalue\n"),
    ],
)
def test_bad_input_errors_without_leaking(bad):
    proc, _ = run_load(bad)
    assert proc.returncode == 7
    assert proc.stderr.strip().startswith("load-secrets:")
    assert "secretvalue" not in proc.stderr + proc.stdout


def test_bad_line_exports_nothing():
    proc, _ = run_load(b64("A=1\nbroken\n"))
    assert proc.returncode == 7
    # A must not have been exported (atomic): check with a tolerant shell
    script = f'. "{LOAD}" || true; printf "%s" "${{A-<unset>}}"'
    out = subprocess.run(
        ["bash", "-c", script],
        env={"PATH": os.environ["PATH"], "SCRAPER_SECRETS_B64": b64("A=1\nbroken\n")},
        capture_output=True,
        text=True,
    )
    assert out.stdout == "<unset>"


def write_env(tmp_path, lines):
    p = tmp_path / ".env"
    p.write_text("\n".join(lines) + "\n")
    return p


def run_make(path):
    return subprocess.run(
        ["bash", str(MAKE), str(path)],
        env={"PATH": os.environ["PATH"]},
        capture_output=True,
        text=True,
    )


def test_make_secrets_selects_keys_and_round_trips(tmp_path):
    lines = [f"{k}=val-{k}-s3cr3t" for k in KEYS]
    lines += ["ROBOTEVENTS_KEY=\"rv key=1$x\"", "UNRELATED=nope", "# comment"]
    proc = run_make(write_env(tmp_path, lines))
    assert proc.returncode == 0
    assert proc.stderr == ""
    out = proc.stdout
    assert out.endswith("\n") and out.count("\n") == 1
    decoded = base64.b64decode(out.strip()).decode()
    assert "UNRELATED" not in decoded
    assert "ROBOTEVENTS_KEY=" in decoded
    # and load-secrets restores them
    probe = KEYS + ["ROBOTEVENTS_KEY"]
    p2, v = run_load(out.strip(), probe=tuple(probe))
    assert p2.returncode == 0
    assert v["TBA_KEY"] == "val-TBA_KEY-s3cr3t"
    assert v["ROBOTEVENTS_KEY"] == "rv key=1$x"


def test_make_secrets_warns_missing_keys_without_values(tmp_path):
    proc = run_make(write_env(tmp_path, ["TBA_KEY=topsecretvalue", "ANTHROPIC_API_KEY="]))
    assert proc.returncode == 0
    assert "DO_SPACES_ACCESS_KEY" in proc.stderr
    assert "ANTHROPIC_API_KEY" in proc.stderr
    assert "TBA_KEY" not in proc.stderr
    assert "ROBOTEVENTS_KEY" not in proc.stderr
    assert "topsecretvalue" not in proc.stderr + proc.stdout


def test_make_secrets_missing_file(tmp_path):
    proc = run_make(tmp_path / "nope.env")
    assert proc.returncode != 0
    assert "not found" in proc.stderr


def test_scripts_executable():
    assert os.access(MAKE, os.X_OK)
    assert os.access(LOAD, os.X_OK)


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck missing")
def test_shellcheck_clean():
    proc = subprocess.run(
        ["shellcheck", "-s", "bash", str(LOAD), str(MAKE)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout
