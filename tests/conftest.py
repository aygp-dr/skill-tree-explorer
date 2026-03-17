"""Shared test fixtures for skill-tree-explorer."""

import os
import tempfile

import pytest

from main import app


@pytest.fixture
def client():
    """Create a Flask test client with a temporary database."""
    app.config["TESTING"] = True
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app.config["DB_PATH"] = db_path

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)
