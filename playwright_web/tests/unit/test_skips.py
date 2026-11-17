import pytest

from utils import skips


@pytest.mark.parametrize(
    "helper, tag",
    [
        (skips.skip_not_applicable, skips.NOT_APPLICABLE_TAG),
        (skips.skip_needs_data, skips.NEEDS_DATA_TAG),
        (skips.skip_blocked, skips.BLOCKED_TAG),
    ],
)
def test_helper_skips_with_its_tag(helper, tag):
    with pytest.raises(pytest.skip.Exception) as info:
        helper("some reason")
    assert str(info.value) == f"{tag} some reason"


@pytest.mark.parametrize(
    "helper, bucket",
    [
        (skips.skip_not_applicable, skips.NOT_APPLICABLE),
        (skips.skip_needs_data, skips.NEEDS_DATA),
        (skips.skip_blocked, skips.BLOCKED),
    ],
)
def test_classify_round_trips_helper_message(helper, bucket):
    with pytest.raises(pytest.skip.Exception) as info:
        helper("reason")
    assert skips.classify(str(info.value)) == bucket


def test_classify_untagged_is_unlabelled():
    assert skips.classify("plain skip") == skips.UNLABELLED
    assert skips.classify("") == skips.UNLABELLED


def test_blocked_wins_over_other_tags():
    both = f"{skips.NEEDS_DATA_TAG} {skips.BLOCKED_TAG} x"
    assert skips.classify(both) == skips.BLOCKED


def test_tags_are_distinct():
    tags = {skips.NOT_APPLICABLE_TAG, skips.NEEDS_DATA_TAG, skips.BLOCKED_TAG}
    assert len(tags) == 3
