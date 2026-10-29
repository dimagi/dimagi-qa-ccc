from flows.ldvp_values import expected_earned, new_run

# 1793253193 -> stamp "253193": the last six digits of the epoch second.
NOW = 1793253193.0


def test_visit_names_and_ids_follow_stamp():
    run = new_run(now=NOW)
    assert run.stamp == "253193"
    assert run.visits["V1"] == ("LDVP-V1-253193", "2531931")
    assert run.visits["V2"] == ("LDVP-V2-253193", "2531932")
    assert run.visits["V3"] == ("LDVP-V3-253193", "2531933")


def test_duplicate_reuses_v1_exactly():
    # TC-DLV-004 only tests duplicate detection if the second submission is
    # identical to the first - a different id would make it a new visit.
    run = new_run(now=NOW)
    assert run.visits["V1_DUP"] == run.visits["V1"]


def test_device_env_has_every_visit():
    env = new_run(now=NOW).device_env()
    assert env["VISIT_NAME_V1"] == "LDVP-V1-253193"
    assert env["VISIT_NAME_V2"] == "LDVP-V2-253193"
    assert env["VISIT_ID_V1_DUP"] == "2531931"
    assert env["VISIT_ID_V3"] == "2531933"


def test_opportunity_suffix_differs_between_runs():
    # A re-run must never find the previous run's opportunity by name.
    assert new_run(now=NOW).opportunity_suffix != new_run(now=NOW + 60).opportunity_suffix


def test_expected_earned_counts_only_approved():
    assert expected_earned(approved=1, unit_amount=100) == 100
    assert expected_earned(approved=0, unit_amount=100) == 0
