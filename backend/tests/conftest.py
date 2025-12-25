import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client():
    from app import db as app_db
    import app.main as app_main

    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # ensure the in-memory DB is shared across sessions
    )

    @event.listens_for(engine, "connect")
    def _sqlite_register_now(dbapi_connection, _connection_record):
        import datetime as _dt

        def _now():
            return _dt.datetime.now(_dt.timezone.utc).isoformat(sep=" ")

        dbapi_connection.create_function("NOW", 0, _now)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app_db.engine = engine
    app_main.engine = engine

    from app import models  # noqa: F401

    app_db.Base.metadata.create_all(bind=engine)

    app = app_main.create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[app_db.get_db] = override_get_db

    with TestClient(app) as c:
        yield c


