from depdetective.gitops import _redact_secret


def test_redact_secret_in_https_url() -> None:
    text = "https://user:token@example.com/org/repo.git"
    assert _redact_secret(text) == "https://***:***@example.com/org/repo.git"

