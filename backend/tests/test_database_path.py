from app.database import ensure_sqlite_directory


def test_ensure_sqlite_directory_creates_parent(tmp_path) -> None:
    db_file = tmp_path / "data" / "securechat.db"
    ensure_sqlite_directory(f"sqlite:///{db_file}")
    assert db_file.parent.is_dir()


def test_ensure_sqlite_directory_ignores_memory() -> None:
    ensure_sqlite_directory("sqlite:///:memory:")
