from subprocess import CompletedProcess

import automation.maintenance as maintenance


def test_skips_commit_when_published_data_is_unchanged(monkeypatch) -> None:
    monkeypatch.setattr(maintenance, "_data_changed", lambda: False)

    assert maintenance.maintain() is False


def test_commits_only_published_data_when_it_changes(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(*arguments: str, check: bool = True) -> CompletedProcess[str]:
        calls.append(arguments)
        return_code = 1 if arguments[:4] == ("git", "diff", "--cached", "--quiet") else 0
        return CompletedProcess(arguments, return_code, stdout="", stderr="")

    monkeypatch.setattr(maintenance, "_data_changed", lambda: True)
    monkeypatch.setattr(maintenance, "_run", fake_run)

    assert maintenance.maintain() is True
    add_call = next(arguments for arguments in calls if arguments[:2] == ("git", "add"))
    assert str(maintenance.OFFERS_PATH) in add_call
    assert str(maintenance.APPROVED_CODES_PATH) in add_call
    assert str(maintenance.SYNC_PATH) in add_call
    assert not any("keepalive" in argument for argument in add_call)
    assert (
        "git",
        "commit",
        "-m",
        "data: refresh Refectory offers and codes [skip ci]",
    ) in calls
    assert ("git", "push") in calls
