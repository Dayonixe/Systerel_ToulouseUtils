from automation.maintenance import should_commit


def test_commits_when_data_changes() -> None:
    assert should_commit(1_000, 1_001, True, 55) is True


def test_commits_after_threshold() -> None:
    assert should_commit(1_000, 1_000 + 55 * 86_400, False, 55) is True


def test_skips_before_threshold() -> None:
    assert should_commit(1_000, 1_000 + 54 * 86_400, False, 55) is False
