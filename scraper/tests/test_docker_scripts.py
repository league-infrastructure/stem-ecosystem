"""Tests for scraper/docker/load-secrets and make-secrets.sh (run via bash)."""

import base64
import os
import re
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


def test_file_mode_matches_env_mode(tmp_path):
    bundle = b64("A=one\nB=\"two words\"\n")
    f = tmp_path / "secret"
    f.write_text(bundle + "\n")
    _, from_env = run_load(bundle)
    proc, from_file = run_load(None, extra_env={"SCRAPER_SECRETS_FILE": str(f)})
    assert proc.returncode == 0
    assert from_file == from_env == {"A": "one", "B": "two words", "C": "<unset>"}


def test_file_missing_or_unreadable_errors_without_leaking(tmp_path):
    proc, _ = run_load(
        b64("A=secretvalue\n"),
        extra_env={"SCRAPER_SECRETS_FILE": str(tmp_path / "nope")},
    )
    assert proc.returncode == 7
    assert proc.stderr.strip().startswith("load-secrets:")
    assert "secretvalue" not in proc.stderr + proc.stdout
    proc, _ = run_load(None, extra_env={"SCRAPER_SECRETS_FILE": str(tmp_path)})
    assert proc.returncode == 7  # a directory is not a readable file


def test_file_bad_content_errors_without_leaking(tmp_path):
    f = tmp_path / "secret"
    f.write_text(b64("1BAD=secretvalue\n"))
    proc, _ = run_load(None, extra_env={"SCRAPER_SECRETS_FILE": str(f)})
    assert proc.returncode == 7
    assert "secretvalue" not in proc.stderr + proc.stdout


def test_empty_file_is_noop(tmp_path):
    f = tmp_path / "secret"
    f.write_text("\n")
    proc, v = run_load(None, extra_env={"SCRAPER_SECRETS_FILE": str(f)})
    assert proc.returncode == 0
    assert v["A"] == "<unset>"
    assert proc.stderr == ""


def test_file_takes_precedence_over_env_bundle(tmp_path):
    f = tmp_path / "secret"
    f.write_text(b64("A=fromfile\n"))
    proc, v = run_load(b64("A=fromenv\nB=fromenv\n"), extra_env={"SCRAPER_SECRETS_FILE": str(f)})
    assert proc.returncode == 0
    assert v["A"] == "fromfile" and v["B"] == "<unset>"


def test_file_mode_existing_env_wins(tmp_path):
    f = tmp_path / "secret"
    f.write_text(b64("A=fromfile\nB=fromfile\n"))
    proc, v = run_load(None, extra_env={"SCRAPER_SECRETS_FILE": str(f), "A": "preset"})
    assert v["A"] == "preset" and v["B"] == "fromfile"


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


# ---------------------------------------------------------------- run-job

RUN_JOB = DOCKER / "run-job"
FAKE = {
    "DO_SPACES_ACCESS_KEY": "fake-access",
    "DO_SPACES_SECRET_KEY": "fake-secret",
    "ANTHROPIC_API_KEY": "fake-anthropic",
    "LEAGUESYNC_API_KEY": "fake-leaguesync",
    "TBA_KEY": "fake-tba",
}


def run_job(tmp_path, args, env_keys=None, stub_exit=0, upload_exit=0):
    """Run run-job with a stub partner-scrape on PATH; return (proc, argv_log).

    The stub records `logs upload` calls (and the uploaded file's content) in
    ``tmp_path/upload.log`` and exits ``upload_exit`` for them."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    log = tmp_path / "argv.log"
    stub = bindir / "partner-scrape"
    stub.write_text(
        '#!/bin/sh\n'
        'if [ "$1" = logs ]; then\n'
        f'  echo "$@" > "{tmp_path}/upload.args"\n'
        '  while [ $# -gt 0 ]; do [ "$1" = --file ] && f="$2"; shift; done\n'
        f'  cp "$f" "{tmp_path}/upload.content"\n'
        f'  exit {upload_exit}\n'
        'fi\n'
        f'echo "$@" > "{log}"\n'
        'echo STUB-OUT\n'
        'echo "leak: $DO_SPACES_SECRET_KEY" >&2\n'
        f'exit {stub_exit}\n'
    )
    stub.chmod(0o755)
    env = {"PATH": f"{bindir}:{os.environ['PATH']}"}
    for k in KEYS if env_keys is None else env_keys:
        env[k] = FAKE[k]
    proc = subprocess.run(
        ["bash", str(RUN_JOB), *args], env=env, capture_output=True, text=True
    )
    return proc, (log.read_text().strip() if log.exists() else None)


def test_run_job_success(tmp_path):
    proc, argv = run_job(tmp_path, ["directory"])
    assert proc.returncode == 0
    lines = proc.stdout.splitlines()
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ START job=directory$", lines[0])
    assert re.search(r"SUCCESS job=directory exit=0 duration=\d+s$", proc.stdout)
    assert argv == "directory"


def test_run_job_uploads_log_on_success(tmp_path):
    proc, _ = run_job(tmp_path, ["directory"])
    assert proc.returncode == 0
    args = (tmp_path / "upload.args").read_text()
    assert "--job directory" in args and "--exit-code 0" in args
    content = (tmp_path / "upload.content").read_text()
    assert "START job=directory" in content
    assert "STUB-OUT" in content
    assert "SUCCESS job=directory" in content
    assert "STUB-OUT" in proc.stdout  # still reaches docker logs


def test_run_job_uploads_log_on_failure(tmp_path):
    proc, _ = run_job(tmp_path, ["teams"], stub_exit=3)
    assert proc.returncode == 3
    assert "--exit-code 3" in (tmp_path / "upload.args").read_text()
    assert "FAILURE job=teams exit=3" in (tmp_path / "upload.content").read_text()


def test_run_job_uploads_log_on_preflight_failure(tmp_path):
    proc, argv = run_job(tmp_path, ["scrape"], env_keys=["DO_SPACES_ACCESS_KEY"])
    assert proc.returncode == 1
    assert argv is None
    assert "--job scrape" in (tmp_path / "upload.args").read_text()
    assert "--exit-code 1" in (tmp_path / "upload.args").read_text()
    assert "missing=" in (tmp_path / "upload.content").read_text()


def test_run_job_upload_failure_keeps_exit_code(tmp_path):
    proc, _ = run_job(tmp_path, ["teams"], stub_exit=3, upload_exit=9)
    assert proc.returncode == 3
    assert "log upload failed" in proc.stdout
    proc, _ = run_job(tmp_path, ["directory"], upload_exit=9)
    assert proc.returncode == 0
    assert "log upload failed" in proc.stdout


def test_run_job_failure_exit_code(tmp_path):
    proc, _ = run_job(tmp_path, ["teams"], stub_exit=3)
    assert proc.returncode == 3
    assert re.search(r"FAILURE job=teams exit=3 duration=\d+s", proc.stdout)


def test_run_job_missing_secrets(tmp_path):
    proc, argv = run_job(tmp_path, ["scrape"], env_keys=["DO_SPACES_ACCESS_KEY"])
    assert proc.returncode != 0
    assert argv is None
    assert (
        "FAILURE job=scrape missing=DO_SPACES_SECRET_KEY,ANTHROPIC_API_KEY,LEAGUESYNC_API_KEY"
        in proc.stdout
    )
    assert "fake-access" not in proc.stdout + proc.stderr


def test_run_job_passthrough_and_waivers(tmp_path):
    keys = ["DO_SPACES_ACCESS_KEY", "DO_SPACES_SECRET_KEY", "LEAGUESYNC_API_KEY"]
    proc, argv = run_job(
        tmp_path, ["scrape", "--source", "foo", "--dry-run", "--no-enrich"], keys
    )
    assert proc.returncode == 0
    assert argv == "--source foo --dry-run --no-enrich"
    # --dry-run alone also waives
    proc, _ = run_job(tmp_path, ["scrape", "--dry-run"], keys)
    assert proc.returncode == 0
    # without flags the key is required
    proc, argv = run_job(tmp_path, ["scrape"], keys)
    assert proc.returncode != 0 and "missing=ANTHROPIC_API_KEY" in proc.stdout

    tkeys = ["DO_SPACES_ACCESS_KEY", "DO_SPACES_SECRET_KEY", "TBA_KEY"]
    proc, argv = run_job(
        tmp_path, ["teams", "--no-sponsors", "--no-descriptions"], tkeys
    )
    assert proc.returncode == 0
    assert argv == "teams --no-sponsors --no-descriptions"
    proc, _ = run_job(tmp_path, ["teams", "--no-sponsors"], tkeys)
    assert proc.returncode != 0


def test_run_job_unknown_job(tmp_path):
    for args in (["bogus"], []):
        proc, argv = run_job(tmp_path, args)
        assert proc.returncode == 2
        assert "usage:" in proc.stderr
        assert argv is None


def test_run_job_uses_secrets_bundle(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "partner-scrape"
    stub.write_text('#!/bin/sh\necho "$DO_SPACES_ACCESS_KEY"\n')
    stub.chmod(0o755)
    bundle = b64("DO_SPACES_ACCESS_KEY=fake-access\nDO_SPACES_SECRET_KEY=fake-secret\n")
    env = {"PATH": f"{bindir}:{os.environ['PATH']}", "SCRAPER_SECRETS_B64": bundle}
    proc = subprocess.run(
        ["bash", str(RUN_JOB), "directory"], env=env, capture_output=True, text=True
    )
    assert proc.returncode == 0
    assert "SUCCESS" in proc.stdout
