"""Tests for scraper/docker/entrypoint.sh dispatch and the crontab (stubs on PATH)."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

DOCKER = Path(__file__).resolve().parent.parent / "docker"
ENTRY = DOCKER / "entrypoint.sh"
CRONTAB = DOCKER / "crontab"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")


def run_entry(tmp_path, args, extra_env=None):
    """Run entrypoint.sh with stub supercronic/partner-scrape that record argv/env."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    for name in ("supercronic", "partner-scrape"):
        stub = bindir / name
        stub.write_text(
            f'#!/bin/sh\necho "{name} $*"\necho "KEY=${{DO_SPACES_ACCESS_KEY-unset}}"\n'
        )
        stub.chmod(0o755)
    # Copy the scripts so `here` resolution works and run-job can be stubbed.
    scripts = tmp_path / "scripts"
    scripts.mkdir(exist_ok=True)
    for name in ("entrypoint.sh", "load-secrets", "crontab"):
        shutil.copy(DOCKER / name, scripts / name)
    rj = scripts / "run-job"
    rj.write_text('#!/bin/sh\necho "run-job $*"\n')
    rj.chmod(0o755)
    env = {"PATH": f"{bindir}:{os.environ['PATH']}"}
    env.update(extra_env or {})
    return subprocess.run(
        ["bash", str(scripts / "entrypoint.sh"), *args],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("args", [[], ["cron"]])
def test_scheduler_mode_loads_secrets_and_execs_supercronic(tmp_path, args):
    import base64

    bundle = base64.b64encode(b"DO_SPACES_ACCESS_KEY=fake-access\n").decode()
    proc = run_entry(tmp_path, args, {"SCRAPER_SECRETS_B64": bundle})
    assert proc.returncode == 0
    assert re.search(r"^supercronic .*crontab$", proc.stdout, re.M)
    assert "KEY=fake-access" in proc.stdout
    # schedule is logged
    assert "run-job scrape" in proc.stdout and "run-job directory" in proc.stdout
    assert "partner-scrape" not in proc.stdout.replace("run-job", "")


def test_run_job_dispatch(tmp_path):
    proc = run_entry(tmp_path, ["run-job", "teams", "--dry-run"])
    assert proc.returncode == 0
    assert proc.stdout.strip() == "run-job teams --dry-run"


@pytest.mark.parametrize(
    "args", [["--help"], ["teams", "--no-sponsors"], ["--source", "xplorstem"]]
)
def test_other_args_go_to_partner_scrape(tmp_path, args):
    proc = run_entry(tmp_path, args)
    assert proc.returncode == 0
    assert proc.stdout.splitlines()[0] == "partner-scrape " + " ".join(args)


def test_bad_secrets_bundle_stops_scheduler(tmp_path):
    proc = run_entry(tmp_path, [], {"SCRAPER_SECRETS_B64": "!!notbase64"})
    assert proc.returncode != 0
    assert "supercronic" not in proc.stdout


def test_crontab_schedule():
    lines = [
        ln for ln in CRONTAB.read_text().splitlines() if ln.strip() and ln[0] != "#"
    ]
    assert "CRON_TZ=America/Los_Angeles" in lines
    jobs = {ln.split("run-job ")[1]: ln.split(" run-job")[0] for ln in lines if "run-job" in ln}
    assert jobs == {
        "scrape": "0 3 * * 1,4",
        "teams": "0 3 * * 3",
        "directory": "0 3 * * 6",
    }
