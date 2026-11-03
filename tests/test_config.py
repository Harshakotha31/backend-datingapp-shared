from shared.config.settings import load_config


def test_default_config():
    config = load_config()

    assert config.app_name == "Backend Shared Libraries"
    assert config.environment == "development"
    assert config.port == 8000


def test_database_url_exists():
    config = load_config()

    assert config.database_url
    assert config.database_url.startswith(
        ("sqlite", "postgresql")
    )