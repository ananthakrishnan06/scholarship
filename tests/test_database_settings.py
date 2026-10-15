"""Exercise environment-driven database settings without the developer's .env."""

import runpy
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ConnectionHandler

SETTINGS_FILE = Path(__file__).resolve().parents[1] / "backend/config/settings.py"


@pytest.fixture
def load_settings(tmp_path, monkeypatch):
    # A fresh project directory proves SQLite works even before var exists.
    settings_file = tmp_path / "backend/config/settings.py"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(SETTINGS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: None)
    for name in (
        "DB_ENGINE",
        "SQLITE_PATH",
        "DJANGO_DEBUG",
        "DJANGO_SECRET_KEY",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_HOST",
        "MYSQL_PORT",
        "SECURE_SSL_REDIRECT",
        "ALLOWED_HOSTS",
        "CORS_ALLOWED_ORIGINS",
        "CSRF_TRUSTED_ORIGINS",
        "TRUST_PROXY_HEADERS",
    ):
        monkeypatch.delenv(name, raising=False)

    def load(**environment):
        for name, value in environment.items():
            monkeypatch.setenv(name, value)
        return runpy.run_path(str(settings_file))

    return load


@pytest.mark.django_db
@pytest.mark.parametrize("debug", ["true", "false"])
def test_sqlite_default_path_is_created_and_usable(load_settings, tmp_path, debug):
    configured = load_settings(
        DB_ENGINE="sqlite",
        DJANGO_DEBUG=debug,
        DJANGO_SECRET_KEY="test-only-secret",
    )
    database = configured["DATABASES"]["default"]
    assert database == {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": tmp_path / "var/dev.sqlite3",
    }
    assert database["NAME"].parent.is_dir()
    # Use an independent connection, leaving pytest-django's database untouched.
    connection = ConnectionHandler(configured["DATABASES"])["default"]
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE settings_probe (value INTEGER)")
            cursor.execute("INSERT INTO settings_probe VALUES (42)")
            cursor.execute("SELECT value FROM settings_probe")
            assert cursor.fetchone() == (42,)
    finally:
        connection.close()
    assert database["NAME"].is_file()


@pytest.mark.parametrize("path_kind", ["relative", "absolute", "empty"])
def test_sqlite_path_environment_override(load_settings, tmp_path, path_kind):
    if path_kind == "relative":
        value = "var/nested/db.sqlite3"
        expected = tmp_path / value
    elif path_kind == "absolute":
        expected = tmp_path / "var/persistent/sqlite/db.sqlite3"
        value = str(expected)
    else:
        value = ""
        expected = tmp_path / "var/dev.sqlite3"
    configured = load_settings(
        DB_ENGINE="sqlite",
        DJANGO_DEBUG="false",
        DJANGO_SECRET_KEY="test-only-secret",
        SQLITE_PATH=value,
    )
    assert configured["DATABASES"]["default"]["NAME"] == expected
    assert expected.parent.is_dir()


@pytest.mark.parametrize("debug", ["true", "false"])
@pytest.mark.parametrize("override_credentials", [False, True])
def test_mysql_configuration_is_preserved(load_settings, tmp_path, debug, override_credentials):
    credentials = (
        {
            "MYSQL_DATABASE": "demo_db",
            "MYSQL_USER": "demo_user",
            "MYSQL_PASSWORD": "test-only-password",
            "MYSQL_HOST": "mysql.example",
            "MYSQL_PORT": "3307",
        }
        if override_credentials
        else {}
    )
    configured = load_settings(
        DB_ENGINE="mysql",
        DJANGO_DEBUG=debug,
        DJANGO_SECRET_KEY="test-only-secret",
        **credentials,
    )
    assert configured["DATABASES"]["default"] == {
        "ENGINE": "django.db.backends.mysql",
        "NAME": credentials.get("MYSQL_DATABASE", "scholarships"),
        "USER": credentials.get("MYSQL_USER", "scholarships"),
        "PASSWORD": credentials.get("MYSQL_PASSWORD", ""),
        "HOST": credentials.get("MYSQL_HOST", "127.0.0.1"),
        "PORT": credentials.get("MYSQL_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
        "CONN_MAX_AGE": 60,
    }
    assert not (tmp_path / "var").exists()


@pytest.mark.parametrize("engine", ["sqlite", "mysql"])
def test_production_security_settings_are_preserved(load_settings, engine):
    configured = load_settings(
        DB_ENGINE=engine,
        DJANGO_DEBUG="false",
        DJANGO_SECRET_KEY="test-only-secret",
    )
    assert configured["DEBUG"] is False
    assert configured["SECRET_KEY"] == "test-only-secret"
    for name in (
        "SESSION_COOKIE_SECURE",
        "CSRF_COOKIE_SECURE",
        "SECURE_SSL_REDIRECT",
        "SECURE_HSTS_INCLUDE_SUBDOMAINS",
        "SECURE_HSTS_PRELOAD",
        "SECURE_CONTENT_TYPE_NOSNIFF",
    ):
        assert configured[name] is True
    assert configured["SECURE_HSTS_SECONDS"] == 31536000
    assert configured["X_FRAME_OPTIONS"] == "DENY"


@pytest.mark.parametrize("engine", ["sqlite", "mysql"])
def test_production_still_requires_a_secret(load_settings, engine):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY is required"):
        load_settings(DB_ENGINE=engine, DJANGO_DEBUG="false", DJANGO_SECRET_KEY="")


def test_omitted_engine_still_defaults_to_sqlite_in_debug(load_settings, tmp_path):
    configured = load_settings()
    assert configured["DEBUG"] is True
    assert configured["DATABASES"]["default"]["NAME"] == tmp_path / "var/dev.sqlite3"


def test_omitted_engine_still_fails_in_production(load_settings):
    with pytest.raises(ImproperlyConfigured, match="explicit DB_ENGINE"):
        load_settings(DJANGO_DEBUG="false", DJANGO_SECRET_KEY="test-only-secret")


@pytest.mark.parametrize("engine", ["", "postgres", "sqltie"])
@pytest.mark.parametrize("debug", ["true", "false"])
def test_unsupported_database_engine_fails_explicitly(load_settings, engine, debug):
    with pytest.raises(ImproperlyConfigured, match="DB_ENGINE must be mysql or sqlite"):
        load_settings(
            DB_ENGINE=engine,
            DJANGO_DEBUG=debug,
            DJANGO_SECRET_KEY="test-only-secret",
        )


@pytest.mark.parametrize("hosts", ["*", " , ", "example.com,*"])
def test_production_rejects_unrestricted_or_empty_allowed_hosts(load_settings, hosts):
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        load_settings(
            DJANGO_DEBUG="false",
            DJANGO_SECRET_KEY="test-only-secret",
            DB_ENGINE="sqlite",
            ALLOWED_HOSTS=hosts,
        )


def test_production_hosts_origins_and_proxy_configuration(load_settings):
    configured = load_settings(
        DJANGO_DEBUG="False",
        DJANGO_SECRET_KEY="test-only-secret",
        DB_ENGINE="sqlite",
        ALLOWED_HOSTS=" demo.onrender.com , localhost,127.0.0.1 ",
        CORS_ALLOWED_ORIGINS=" https://demo.vercel.app , ",
        CSRF_TRUSTED_ORIGINS=" https://demo.vercel.app , ",
        TRUST_PROXY_HEADERS="True",
    )
    assert configured["ALLOWED_HOSTS"] == ["demo.onrender.com", "localhost", "127.0.0.1"]
    assert configured["CORS_ALLOWED_ORIGINS"] == ["https://demo.vercel.app"]
    assert configured["CSRF_TRUSTED_ORIGINS"] == ["https://demo.vercel.app"]
    assert configured["SECURE_PROXY_SSL_HEADER"] == ("HTTP_X_FORWARDED_PROTO", "https")
    assert not configured.get("CORS_ALLOW_ALL_ORIGINS", False)
    assert "x-session-token" in configured["CORS_ALLOW_HEADERS"]
    assert "x-request-id" in configured["CORS_ALLOW_HEADERS"]


def test_proxy_headers_are_disabled_by_default(load_settings):
    configured = load_settings(
        DJANGO_DEBUG="false",
        DJANGO_SECRET_KEY="test-only-secret",
        DB_ENGINE="sqlite",
    )
    assert configured["SECURE_PROXY_SSL_HEADER"] is None
