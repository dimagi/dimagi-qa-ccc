"""Fetch the latest dev build of commcare-android's master branch (QA Plan tasks B1/B3).

Agreed with the dev team (Shubham, Mobile Automation QA Plan): dev APKs are built on
demand by commcare-android's "PR CI" workflow (commcare-android-pr-workflow.yml), which
QA dispatches on master. Only a dispatched run builds the qaAutomation APKs the flows
need, and those artifacts are kept for 3 days.

What this does, in order:

1. Reads master's head commit.
2. If a dispatched master build of that commit already has the artifact, uses it.
3. If one is still running, waits for it rather than dispatching again: the workflow's
   concurrency group would cancel the running build in favour of ours.
4. Otherwise dispatches a master build and waits for the artifact. The artifact is
   uploaded part-way through the run, so this stops waiting as soon as it is there.
5. If the head build failed without producing the artifact (or dispatching isn't
   allowed), falls back to the newest older master build that still has one, and says
   so - a run on yesterday's code beats no run, as long as nobody mistakes it for today's.

With --release it does the same for the latest commcare-android release tag instead of
master: Shubham (CI-1069, 26 Nov) prefers QA build the release's qaAutomation APK from
the PR workflow when needed over attaching it to the public releases page. The tag's
commcare-core commit is the commcare-core tag of the same name. There is no fallback
to an older release: testing the wrong release would be worse than no run.

Builds dispatched by bots (commcare-core's cross-repo CI builds master against a
commcare-core PR) are ignored: they aren't master as it stands.

Needs a token in COMMCARE_ANDROID_TOKEN (falling back to GH_TOKEN / GITHUB_TOKEN) that
can read commcare-android's Actions artifacts, and - to dispatch - run its workflows
(the A1 interrupt ticket asks the dev team for one).

Usage:
    python maestro_mobile/scripts/dev_build.py --artifact ccc-staging-qaAutomation-release-apk \\
        --out app/app-cccStaging-release.apk
    python maestro_mobile/scripts/dev_build.py --artifact ... --out ... --no-dispatch
    python maestro_mobile/scripts/dev_build.py --release --artifact commcare-qaAutomation-release-apk \\
        --out app/app-commcare-release.apk
"""
import argparse
import io
import os
import re
import sys
import time
import zipfile
from pathlib import Path

import requests

REPO_API = "https://api.github.com/repos/dimagi/commcare-android"
CORE_API = "https://api.github.com/repos/dimagi/commcare-core"
WORKFLOW = "commcare-android-pr-workflow.yml"
BRANCH = "master"
RUNS_TO_SCAN = 50
RELEASE_TAG = re.compile(r"^commcare_(\d+(?:\.\d+)+)$")
HTTP_TIMEOUT = 60
POLL_SECONDS = 60
# A full PR CI build takes about 25 minutes; the job itself times out at 90.
DEFAULT_WAIT_MINUTES = 80


class DevBuildError(Exception):
    """No usable dev build could be found or made."""


class GitHub:
    def __init__(self, token, sleep=time.sleep):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.sleep = sleep

    def get(self, path, **params):
        return self.get_url(f"{REPO_API}/{path}", **params)

    def get_url(self, url, **params):
        response = self.session.get(url, params=params, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def post(self, path, payload):
        response = self.session.post(f"{REPO_API}/{path}", json=payload, timeout=HTTP_TIMEOUT)
        if response.status_code in (403, 404):
            raise DevBuildError(
                f"Not allowed to dispatch {WORKFLOW} (HTTP {response.status_code}). The token needs "
                "permission to run commcare-android's workflows (A1 interrupt ticket)."
            )
        response.raise_for_status()

    def download(self, url):
        response = self.session.get(url, timeout=HTTP_TIMEOUT * 10)
        response.raise_for_status()
        return response.content


# --------------------------------------------------------------------------- finding builds

def latest_release_tag(gh):
    """The highest-version published release tag (not the newest upload: releases go up by hand)."""
    tags = []
    for release in gh.get("releases", per_page=30):
        match = RELEASE_TAG.match(release.get("tag_name") or "")
        if match and not release.get("draft") and not release.get("prerelease"):
            tags.append((tuple(int(part) for part in match.group(1).split(".")), release["tag_name"]))
    if not tags:
        raise DevBuildError("No published commcare-android release tag found")
    return max(tags)[1]


def master_head(gh, ref=BRANCH):
    return gh.get(f"commits/{ref}")["sha"]


def master_builds(gh, ref=BRANCH):
    """Dispatched master runs of the PR CI workflow by people, newest first.

    Listed with the branch filter and the event checked here: the event-filtered listing
    has been seen returning a stale set (dimagi-qa-commcare-mobile's fetch_apk.py)."""
    runs = gh.get(f"actions/workflows/{WORKFLOW}/runs", branch=ref, per_page=RUNS_TO_SCAN)["workflow_runs"]
    return sorted(
        (run for run in runs
         if run["event"] == "workflow_dispatch" and not run["actor"]["login"].endswith("[bot]")),
        key=lambda run: run["id"],
        reverse=True,
    )


def live_artifact(gh, run_id, name):
    artifacts = gh.get(f"actions/runs/{run_id}/artifacts", per_page=100)["artifacts"]
    return next((a for a in artifacts if a["name"] == name and not a["expired"]), None)


def wait_for_artifact(gh, run_id, name, minutes):
    """Wait until the run has uploaded the artifact or finished. Returns the artifact or None."""
    deadline = time.monotonic() + minutes * 60
    while True:
        artifact = live_artifact(gh, run_id, name)
        if artifact:
            return artifact
        run = gh.get(f"actions/runs/{run_id}")
        if run["status"] == "completed":
            # Uploads land before the run completes, but list once more in case the
            # listing lagged behind the upload.
            return live_artifact(gh, run_id, name)
        if time.monotonic() > deadline:
            raise DevBuildError(f"Gave up after {minutes} minutes waiting for run {run_id} to upload {name}")
        print(f"  run {run_id} is {run['status']}; waiting for {name}...")
        gh.sleep(POLL_SECONDS)


def dispatch(gh, ref=BRANCH):
    """Dispatch a master build and return its run id.

    A dispatched run only checks out commcare-core when it is given commcare_core_sha
    (otherwise Gradle stops at "Configuring project ':commcare-core' without an existing
    directory"), so this passes commcare-core's master head."""
    newest_before = max((run["id"] for run in master_builds(gh, ref)), default=0)
    core_sha = gh.get_url(f"{CORE_API}/commits/{ref}")["sha"]
    gh.post(f"actions/workflows/{WORKFLOW}/dispatches", {"ref": ref, "inputs": {"commcare_core_sha": core_sha}})
    for _ in range(10):
        gh.sleep(10)
        new = [run for run in master_builds(gh, ref) if run["id"] > newest_before]
        if new:
            return new[-1]["id"]
    raise DevBuildError("Dispatched a master build but it never appeared in the run list")


def replacement_build(gh, head, run_id, ref=BRANCH):
    """A newer build of the same commit, if run_id was cancelled to make way for it."""
    if gh.get(f"actions/runs/{run_id}").get("conclusion") != "cancelled":
        return None
    newer = [run for run in master_builds(gh, ref) if run["head_sha"] == head and run["id"] > run_id]
    if newer:
        print(f"Run {run_id} was cancelled for run {newer[-1]['id']}; waiting for that one")
        return newer[-1]["id"]
    return None


def rerun_failed_jobs(gh, run_id):
    """Re-run a failed build's failed jobs, and wait until GitHub shows it running again.

    Master's unit tests flake (26 Nov: three Connect view tests failed on d41d534f, which
    built cleanly that morning), and a failed Build job uploads no APK. With test builds
    kept only 3 days there is often no older build to fall back to, so one re-run is
    worth the extra half hour."""
    gh.post(f"actions/runs/{run_id}/rerun-failed-jobs", {})
    for _ in range(12):
        if gh.get(f"actions/runs/{run_id}")["status"] != "completed":
            return True
        gh.sleep(10)
    return False


def find_build(gh, artifact_name, can_dispatch=True, wait_minutes=DEFAULT_WAIT_MINUTES, ref=BRANCH):
    """(run, artifact, current) for master's dev build; current is False on a fallback."""
    head = master_head(gh, ref)
    builds = master_builds(gh, ref)
    print(f"commcare-android {ref} is at {head[:10]}")

    at_head = [run for run in builds if run["head_sha"] == head]
    for run in at_head:
        artifact = live_artifact(gh, run["id"], artifact_name)
        if artifact:
            print(f"Using run {run['id']}, already built from {head[:10]}")
            return run, artifact, True
    running = next((run for run in at_head if run["status"] != "completed"), None)
    if running:
        print(f"Run {running['id']} is already building {head[:10]}; waiting for it")
        run_id = running["id"]
    elif at_head:
        run_id = None
        print(f"The build of {head[:10]} (run {at_head[0]['id']}) finished without {artifact_name}; "
              "not dispatching again")
    elif can_dispatch:
        run_id = dispatch(gh, ref)
        print(f"Dispatched run {run_id} to build {head[:10]}")
    else:
        run_id = None
        print(f"No build of {head[:10]} yet, and dispatching is off")

    # Two runs can dispatch at once (the matrix legs, or the other QA repo); the
    # workflow's concurrency group then cancels the first build in favour of the
    # second. A waiter whose build was cancelled moves on to the replacement.
    rerun = set()
    for _ in range(3):
        if not run_id:
            break
        artifact = wait_for_artifact(gh, run_id, artifact_name, wait_minutes)
        if artifact:
            return gh.get(f"actions/runs/{run_id}"), artifact, True
        print(f"Run {run_id} finished without {artifact_name}")
        if gh.get(f"actions/runs/{run_id}").get("conclusion") == "failure" and run_id not in rerun:
            rerun.add(run_id)
            print(f"Run {run_id} failed; re-running its failed jobs once")
            if rerun_failed_jobs(gh, run_id):
                continue
        run_id = replacement_build(gh, head, run_id, ref)

    for run in builds:
        if run["head_sha"] == head or run["status"] != "completed":
            continue
        artifact = live_artifact(gh, run["id"], artifact_name)
        if artifact:
            print(f"WARNING: falling back to run {run['id']}, built from {run['head_sha'][:10]} "
                  f"on {run['created_at'][:10]} - NOT master's current head {head[:10]}")
            return run, artifact, False
    raise DevBuildError(
        f"No dispatched {ref} build in the last {RUNS_TO_SCAN} runs has a live {artifact_name} "
        "(qaAutomation artifacts are kept 3 days)"
    )


# --------------------------------------------------------------------------- downloading

def extract_apk(archive, out_path):
    """Write the single .apk inside an artifact zip to out_path."""
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        apks = [name for name in bundle.namelist() if name.endswith(".apk")]
        if len(apks) != 1:
            raise DevBuildError(f"Expected one .apk in the artifact, found {apks or 'none'}")
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(bundle.read(apks[0]))
    return out_path


def fetch_dev_build(artifact_name, out_path, token, can_dispatch=True, wait_minutes=DEFAULT_WAIT_MINUTES,
                    release=False):
    gh = GitHub(token)
    ref = latest_release_tag(gh) if release else BRANCH
    run, artifact, current = find_build(gh, artifact_name, can_dispatch, wait_minutes, ref)
    print(f"Downloading {artifact_name} ({artifact['size_in_bytes']} bytes) from run {run['id']}...")
    extract_apk(gh.download(artifact["archive_download_url"]), out_path)
    return {
        "run_id": run["id"],
        "run_url": run["html_url"],
        "head_sha": run["head_sha"],
        "built_on": run["created_at"],
        "current": current,
        "ref": ref,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--artifact", required=True, help="e.g. ccc-staging-qaAutomation-release-apk")
    parser.add_argument("--out", required=True, help="where to write the APK")
    parser.add_argument("--no-dispatch", action="store_true", help="only use builds that already exist")
    parser.add_argument("--wait-minutes", type=int, default=DEFAULT_WAIT_MINUTES)
    parser.add_argument("--release", action="store_true", help="build the latest release tag instead of master")
    args = parser.parse_args()
    token = os.getenv("COMMCARE_ANDROID_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        sys.exit("No token: set COMMCARE_ANDROID_TOKEN (artifact downloads need one even on a public repo)")
    try:
        build = fetch_dev_build(args.artifact, args.out, token, not args.no_dispatch, args.wait_minutes, args.release)
    except (DevBuildError, requests.RequestException) as error:
        sys.exit(f"Dev build fetch failed: {error}")
    print(f"Build ready: {args.out} from {build['run_url']} ({build['ref']} @ {build['head_sha'][:10]}, "
          f"{'current' if build['current'] else 'OLDER than the ref head'})")
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            for key, value in build.items():
                f.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            note = "" if build["current"] else " **(fallback: not master's current head)**"
            f.write(f"APK: [{args.artifact}]({build['run_url']}) built from {build['ref']} "
                    f"`{build['head_sha'][:10]}` on {build['built_on'][:10]}{note}\n")


if __name__ == "__main__":
    main()
