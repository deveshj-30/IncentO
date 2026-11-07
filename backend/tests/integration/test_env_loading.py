"""backend/.env must reach both the settings object and os.environ (the memory adapter reads os.environ)."""

import os

from app.core.config import ENV_FILE, REPO_ROOT, Settings, load_env_into_process


def test_env_file_path_is_absolute_and_in_backend():
    assert ENV_FILE == REPO_ROOT / "backend" / ".env"


def test_dotenv_is_exported_without_overriding_real_variables(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("HINDSIGHT_API_KEY=file-key\nHINDSIGHT_SIMULATE=1\nTEST_ONLY_EXISTING=from-file\n")
    monkeypatch.delenv("HINDSIGHT_API_KEY", raising=False)
    monkeypatch.delenv("HINDSIGHT_SIMULATE", raising=False)
    monkeypatch.setenv("TEST_ONLY_EXISTING", "from-shell")
    load_env_into_process(env)
    try:
        assert os.environ["HINDSIGHT_API_KEY"] == "file-key"
        assert os.environ["HINDSIGHT_SIMULATE"] == "1"
        assert os.environ["TEST_ONLY_EXISTING"] == "from-shell"  # real environment wins
    finally:
        os.environ.pop("HINDSIGHT_API_KEY", None)
        os.environ.pop("HINDSIGHT_SIMULATE", None)


def test_missing_env_file_is_not_an_error(tmp_path):
    load_env_into_process(tmp_path / "does-not-exist.env")


def test_settings_still_hide_the_key():
    s = Settings(hindsight_api_key="secret-value", database_path=":memory:")
    assert s.memory_configured and "secret-value" not in repr(s)
