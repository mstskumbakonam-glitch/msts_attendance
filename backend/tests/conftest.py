"""
Pytest configuration and shared fixtures for backend tests.
Uses dedicated test database (sas_test) to protect dev data.
"""
import os
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from backend.app.core.deps import get_db
from backend.app.core.security import create_access_token, hash_password
from backend.app.db.base import Base
import backend.app.models  # noqa: F401
from backend.app.models.user import User
from backend.app.main import app

load_dotenv()

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/sas_test"
)

# Ensure psycopg is used for sync test engine
if "+asyncpg" in TEST_DATABASE_URL:
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace("+asyncpg", "+psycopg")

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure vector extension and schema exist on sas_test."""
    with test_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    # Create tables if not already created by Alembic
    Base.metadata.create_all(bind=test_engine)
    yield
    # Keep schema intact


@pytest.fixture
def db_session() -> Session:
    """
    Yields a database session wrapped in a transaction that rolls back
    at the end of each test to guarantee complete test isolation.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session):
    """TestClient that uses the transactional test db session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create and return an active ADMIN user."""
    user = User(
        username="admin_test",
        email="admin@example.com",
        password_hash=hash_password("AdminSecret123!"),
        role="ADMIN",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def operator_user(db_session: Session) -> User:
    """Create and return an active OPERATOR user."""
    user = User(
        username="operator_test",
        email="operator@example.com",
        password_hash=hash_password("OperatorSecret123!"),
        role="OPERATOR",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Generate a valid JWT token for the admin user."""
    token, _, _ = create_access_token({"sub": str(admin_user.id), "username": admin_user.username, "role": admin_user.role})
    return token


@pytest.fixture
def operator_token(operator_user: User) -> str:
    """Generate a valid JWT token for the operator user."""
    token, _, _ = create_access_token({"sub": str(operator_user.id), "username": operator_user.username, "role": operator_user.role})
    return token
