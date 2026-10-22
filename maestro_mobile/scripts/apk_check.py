"""Know which build a run is testing before it runs.

Two jobs, both agreed with the dev team (Mobile Automation QA Plan, tasks B2/B3):

* check_apk(): every run reads the APK's versionName and confirms it was built for
  the environment's Connect server, so a stage run can never test a prod build (or
  the reverse) and report the result as a test failure. The server is read from the
  APK's own code, which carries the Connect host it was built against; the expected
  host comes from config/env.yaml's connect_url.

* check_apk() also refuses anything but a qaAutomation build. The flows depend on it:
  a plain release build sends signup to biometric/PIN setup after the phone number,
  asks for biometrics on every PersonalID unlock, and needs a real camera for the
  signup photo - none of which a BrowserStack device can do. That is not a 2.65
  change; it is why the public release APK fails at the first screen after the phone
  number (PR #70's first prod run, on app-commcare-release.apk from commcare_2.65.0).

* fetch_release_apk(): prod runs test the latest commcare-android GitHub release
  instead of a committed app/ file. "Latest" is the highest version among published
  releases, not the most recently published one - releases are uploaded by hand, and
  a patch for an older line can land after a newer version. The APK's versionName
  must match its release tag. Only a qaAutomation asset counts (see above), so this
  finds nothing until releases carry one alongside app-commcare-release.apk.

The staging (cccStaging) APK stays committed in app/ until there is a fixed place to
fetch dev/beta staging builds from.

Usage:
    python maestro_mobile/scripts/apk_check.py fetch-release          # -> app/app-commcare-release.apk
    python maestro_mobile/scripts/apk_check.py check --app-env stage
"""
import argparse
import json
import os
import re
import struct
import sys
import urllib.request
import zipfile
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_CONFIG = PROJECT_ROOT / "config" / "env.yaml"
RELEASES_API = "https://api.github.com/repos/dimagi/commcare-android/releases"
RELEASE_APK_PATH = PROJECT_ROOT / "app" / "app-commcare-release.apk"
RELEASES_TO_SCAN = 15
# The CommCare qaAutomation APK, named as commcare-android's build writes it
# (app-commcare-qaAutomation.apk), allowing a version suffix the way release assets have had
# one (app-commcare-release_2.64.1.apk); not lts/staging/connect builds, and not the plain
# release APK.
RELEASE_ASSET = re.compile(r"^(app-)?commcare[-_](?!.*(lts|staging|connect)).*qaautomation.*\.apk$", re.IGNORECASE)
RELEASE_TAG = re.compile(r"^commcare_(\d+(?:\.\d+)*)$")

# BuildConfig.BUILD_TYPE of a qaAutomation build, as a dex string-table entry: a ULEB128 length
# (12) then the MUTF-8 bytes and a NUL. A plain release build has no such entry.
_QA_AUTOMATION_DEX_STRING = b"\x0cqaAutomation\x00"
_RES_STRING_POOL = 0x0001
_RES_XML_START_ELEMENT = 0x0102
_UTF8_FLAG = 0x100


class ApkCheckError(Exception):
    """The APK is not the build this run expects."""


# --------------------------------------------------------------------------- reading the APK

def _read_string_pool(data, offset):
    _, header_size, _size, count, _styles, flags, strings_start, _ = struct.unpack_from("<HHIIIIII", data, offset)
    offsets = struct.unpack_from(f"<{count}I", data, offset + header_size)
    base, utf8 = offset + strings_start, bool(flags & _UTF8_FLAG)
    strings = []
    for off in offsets:
        pos = base + off
        if utf8:
            pos += 2 if data[pos] & 0x80 else 1
            length = data[pos]
            pos += 1
            if length & 0x80:
                length = ((length & 0x7F) << 8) | data[pos]
                pos += 1
            strings.append(data[pos:pos + length].decode("utf-8", "replace"))
        else:
            (length,) = struct.unpack_from("<H", data, pos)
            pos += 2
            if length & 0x8000:
                (low,) = struct.unpack_from("<H", data, pos)
                length = ((length & 0x7FFF) << 16) | low
                pos += 2
            strings.append(data[pos:pos + length * 2].decode("utf-16-le", "replace"))
    return strings


def read_version_name(apk_path):
    """versionName from the APK's binary AndroidManifest.xml, or None."""
    with zipfile.ZipFile(apk_path) as apk:
        data = apk.read("AndroidManifest.xml")
    _, header_size, total = struct.unpack_from("<HHI", data, 0)
    pos, strings = header_size, []
    while pos < min(total, len(data)):
        chunk_type, chunk_header, chunk_size = struct.unpack_from("<HHI", data, pos)
        if chunk_type == _RES_STRING_POOL:
            strings = _read_string_pool(data, pos)
        elif chunk_type == _RES_XML_START_ELEMENT:
            body = pos + chunk_header
            _ns, name, attr_start, attr_size, attr_count = struct.unpack_from("<iiHHH", data, body)
            if strings[name] == "manifest":
                for i in range(attr_count):
                    _ans, attr_name, raw, *_ = struct.unpack_from("<iiiHBBI", data, body + attr_start + i * attr_size)
                    if strings[attr_name] == "versionName" and raw >= 0:
                        return strings[raw]
                return None
        if chunk_size <= 0:
            break
        pos += chunk_size
    return None


def connect_hosts(apk_path):
    """Every Connect server host named in the APK's code (e.g. connect-staging.dimagi.com)."""
    hosts = set()
    with zipfile.ZipFile(apk_path) as apk:
        for name in apk.namelist():
            if name.endswith(".dex"):
                hosts.update(m.decode() for m in re.findall(rb"connect[a-z0-9-]*\.dimagi\.com", apk.read(name)))
    return hosts


def is_qa_automation_build(apk_path):
    """True if the APK is a qaAutomation build (BuildConfig.IS_QA_AUTOMATION)."""
    with zipfile.ZipFile(apk_path) as apk:
        return any(
            _QA_AUTOMATION_DEX_STRING in apk.read(name) for name in apk.namelist() if name.endswith(".dex")
        )


def expected_hosts():
    """{app_env: Connect host} from config/env.yaml's connect_url."""
    with open(ENV_CONFIG, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return {
        env: re.sub(r"^https?://", "", values["connect_url"]).split("/")[0]
        for env, values in config.items()
        if isinstance(values, dict) and values.get("connect_url")
    }


def _version_tuple(text):
    parts = [int(part) for part in re.findall(r"\d+", text or "")]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def check_apk(apk_path, app_env, expected_version=None):
    """Return the APK's versionName, or raise ApkCheckError if it isn't this run's build."""
    hosts_by_env = expected_hosts()
    if app_env not in hosts_by_env:
        raise ApkCheckError(f"No connect_url for environment {app_env!r} in {ENV_CONFIG.name}")
    want = hosts_by_env[app_env]
    others = {host for env, host in hosts_by_env.items() if env != app_env}
    found = connect_hosts(apk_path)
    if want not in found:
        raise ApkCheckError(f"{Path(apk_path).name} is not built for {app_env} ({want}); it names {sorted(found) or 'no Connect host'}")
    wrong = found & others
    if wrong:
        raise ApkCheckError(f"{Path(apk_path).name} is built for another environment: it names {sorted(wrong)}")
    if not is_qa_automation_build(apk_path):
        raise ApkCheckError(
            f"{Path(apk_path).name} is not a qaAutomation build; the flows need one "
            "(assembleCommcareQaAutomation / assembleCccStagingQaAutomation)"
        )

    version = read_version_name(apk_path)
    if not version:
        raise ApkCheckError(f"Couldn't read versionName from {Path(apk_path).name}")
    if expected_version and _version_tuple(version) != _version_tuple(expected_version):
        raise ApkCheckError(f"{Path(apk_path).name} is versionName {version}, expected {expected_version}")
    print(f"APK check passed: {Path(apk_path).name} is {version}, built for {app_env} ({want}).")
    return version


# --------------------------------------------------------------------------- latest release

def _get_json(url):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.getenv("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def pick_release(releases):
    """(release, asset) for the highest-version published release with a CommCare qaAutomation APK."""
    candidates = []
    for release in releases:
        match = RELEASE_TAG.match(release.get("tag_name") or "")
        if release.get("draft") or release.get("prerelease") or not match:
            continue
        asset = next((a for a in release.get("assets", []) if RELEASE_ASSET.match(a["name"])), None)
        if asset:
            candidates.append((tuple(int(p) for p in match.group(1).split(".")), release, asset))
    if not candidates:
        raise ApkCheckError(
            f"No published release in the last {RELEASES_TO_SCAN} has a CommCare qaAutomation APK "
            "(releases carry only the plain release build until the release process attaches one)"
        )
    _, release, asset = max(candidates, key=lambda candidate: candidate[0])
    return release, asset


def fetch_release_apk(out_path=RELEASE_APK_PATH):
    """Download the latest release APK to out_path, check it, and return its release tag."""
    release, asset = pick_release(_get_json(f"{RELEASES_API}?per_page={RELEASES_TO_SCAN}"))
    print(f"Downloading {asset['name']} from {release['tag_name']} ({asset['size']} bytes)...")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(asset["browser_download_url"], out_path)
    check_apk(out_path, "prod", expected_version=release["tag_name"].removeprefix("commcare_"))
    return release["tag_name"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch-release", help="download the latest release APK for prod runs")
    fetch.add_argument("--out", default=str(RELEASE_APK_PATH))
    check = sub.add_parser("check", help="check an environment's APK")
    check.add_argument("--app-env", required=True)
    check.add_argument("--apk", help="defaults to the environment's APK in app/")
    check.add_argument("--expect-version")
    args = parser.parse_args()
    try:
        if args.command == "fetch-release":
            tag = fetch_release_apk(args.out)
            github_output = os.getenv("GITHUB_OUTPUT")
            if github_output:
                with open(github_output, "a", encoding="utf-8") as f:
                    f.write(f"release_tag={tag}\n")
        else:
            from run_on_browserstack import resolve_apk

            check_apk(args.apk or resolve_apk(args.app_env), args.app_env, args.expect_version)
    except ApkCheckError as error:
        sys.exit(f"APK check failed: {error}")


if __name__ == "__main__":
    main()
