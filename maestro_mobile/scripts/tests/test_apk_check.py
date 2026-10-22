"""Unit tests for the APK version and server check.

Release picking runs on fake release lists. The host and version checks run on
the APKs committed in app/, which are real builds for each environment.
"""

import zipfile

import pytest

from maestro_mobile.scripts.apk_check import (
    PROJECT_ROOT,
    ApkCheckError,
    check_apk,
    pick_release,
    read_version_name,
)

PROD_APK = PROJECT_ROOT / "app" / "app-commcare-release.apk"
STAGE_APK = PROJECT_ROOT / "app" / "app-cccStaging-release.apk"


def _release(tag, asset="app-commcare-qaAutomation.apk", draft=False, prerelease=False):
    return {"tag_name": tag, "draft": draft, "prerelease": prerelease, "assets": [{"name": asset}]}


def test_pick_release_takes_the_highest_version_not_the_newest_upload():
    releases = [_release("commcare_2.64.2"), _release("commcare_2.65.0"), _release("commcare_2.64.1")]
    release, _ = pick_release(releases)
    assert release["tag_name"] == "commcare_2.65.0"


def test_pick_release_skips_drafts_prereleases_and_non_version_tags():
    releases = [
        _release("commcare_2.66.0", draft=True),
        _release("commcare_2.66.1", prerelease=True),
        _release("commcare_2.61.5test"),
        _release("commcare_2.65.0"),
    ]
    release, _ = pick_release(releases)
    assert release["tag_name"] == "commcare_2.65.0"


def test_pick_release_skips_releases_without_a_commcare_qa_automation_apk():
    releases = [
        _release("commcare_2.67.0", asset="app-commcare-release.apk"),
        _release("commcare_2.66.0", asset="app-cccStaging-qaAutomation.apk"),
        _release("commcare_2.65.0", asset="app-commcare-qaAutomation_2.65.0.apk"),
    ]
    release, asset = pick_release(releases)
    assert (release["tag_name"], asset["name"]) == ("commcare_2.65.0", "app-commcare-qaAutomation_2.65.0.apk")


def test_pick_release_fails_when_nothing_usable():
    with pytest.raises(ApkCheckError):
        pick_release([_release("commcare_2.65.0", draft=True)])


def test_each_committed_apk_passes_for_its_own_environment():
    assert check_apk(PROD_APK, "prod")
    assert check_apk(STAGE_APK, "stage")


def test_an_apk_for_the_other_environment_is_rejected():
    with pytest.raises(ApkCheckError, match="not built for stage"):
        check_apk(PROD_APK, "stage")
    with pytest.raises(ApkCheckError, match="not built for prod"):
        check_apk(STAGE_APK, "prod")


def test_version_must_match_when_one_is_expected():
    version = read_version_name(PROD_APK)
    assert check_apk(PROD_APK, "prod", expected_version=version) == version
    with pytest.raises(ApkCheckError, match="expected 0.0.1"):
        check_apk(PROD_APK, "prod", expected_version="0.0.1")


def test_a_plain_release_build_is_rejected(tmp_path):
    # Built for prod, but without the qaAutomation build type - what the public
    # release asset is.
    apk = tmp_path / "app-commcare-release.apk"
    with zipfile.ZipFile(apk, "w") as zf:
        zf.writestr("classes.dex", b"https://connect.dimagi.com/ \x07release\x00")
    with pytest.raises(ApkCheckError, match="not a qaAutomation build"):
        check_apk(apk, "prod")
