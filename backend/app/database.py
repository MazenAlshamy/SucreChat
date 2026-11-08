from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


class Base(DeclarativeBase):
    pass


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        if ":memory:" not in settings.database_url:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def ensure_sqlite_directory(url: str | None = None) -> None:
    database_url = url if url is not None else get_settings().database_url
    if not database_url.startswith("sqlite") or ":memory:" in database_url:
        return
    database = make_url(database_url).database
    if not database:
        return
    Path(database).expanduser().parent.mkdir(parents=True, exist_ok=True)


def _make_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url
    ensure_sqlite_directory(url)
    kwargs: dict = {"future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    return create_engine(url, **kwargs)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            future=True,
        )
    return _SessionLocal


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _sqlite_columns(connection, table: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _add_column(connection, table: str, column: str, definition: str) -> None:
    columns = _sqlite_columns(connection, table)
    if column not in columns:
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def _apply_account_columns(connection) -> None:
    tables = {
        row[0]
        for row in connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    }
    if "users" not in tables:
        return
    _add_column(connection, "users", "first_name", "VARCHAR(40)")
    _add_column(connection, "users", "last_name", "VARCHAR(40)")
    _add_column(connection, "users", "email", "VARCHAR(254)")
    _add_column(connection, "users", "email_normalized", "VARCHAR(254)")
    _add_column(connection, "users", "password_hash", "VARCHAR(255)")
    _add_column(connection, "users", "email_verified_at", "DATETIME")
    _add_column(connection, "users", "terms_accepted_at", "DATETIME")
    _add_column(connection, "users", "account_status", "VARCHAR(20) DEFAULT 'guest'")
    connection.execute(
        text("UPDATE users SET account_status = 'guest' WHERE account_status IS NULL")
    )
    connection.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_normalized ON users (email_normalized)"
        )
    )


def _apply_meeting_columns(connection) -> None:
    tables = {
        row[0]
        for row in connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    }
    if "rooms" not in tables:
        return
    _add_column(connection, "rooms", "meeting_started_at", "DATETIME")
    _add_column(connection, "rooms", "meeting_ended_at", "DATETIME")


def init_db() -> None:
    from app import models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _record_schema_version(engine)


def _record_schema_version(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO schema_migrations (version, applied_at)
                VALUES ('0001_rooms_invites_join_requests', datetime('now'))
                """
            )
        )
        _apply_account_columns(connection)
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO schema_migrations (version, applied_at)
                VALUES ('0002_accounts_email_verification', datetime('now'))
                """
            )
        )
        _apply_meeting_columns(connection)
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO schema_migrations (version, applied_at)
                VALUES ('0003_chat_notifications_meeting_timer', datetime('now'))
                """
            )
        )
