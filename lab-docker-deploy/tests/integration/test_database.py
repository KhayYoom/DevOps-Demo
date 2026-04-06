"""
test_database.py - Integration tests for the DatabaseManager.

These tests connect to a REAL PostgreSQL database.
They are SKIPPED automatically when the DATABASE_URL environment
variable is not set, so unit-only test runs are not affected.

In GitHub Actions, the Postgres service container provides
the database. Locally, you can use docker-compose.
"""

import os
import pytest
from app.database import DatabaseManager


# Skip the entire module if DATABASE_URL is not configured
DATABASE_URL = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="DATABASE_URL environment variable not set -- skipping database tests",
)


@pytest.fixture()
def db():
    """Create a DatabaseManager, set up tables, and clean up after each test."""
    manager = DatabaseManager()
    manager.connect(DATABASE_URL)
    manager.create_tables()
    # Clean the table before each test
    manager._cursor.execute("DELETE FROM products")
    yield manager
    manager.disconnect()


class TestDatabaseConnection:
    """Tests for connecting to PostgreSQL."""

    def test_connection_is_alive(self, db):
        """The connection should be alive after connect()."""
        assert db.is_connected() is True

    def test_tables_exist(self, db):
        """The products table should exist after create_tables()."""
        db._cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'products')"
        )
        row = db._cursor.fetchone()
        assert row["exists"] is True


class TestDatabaseCRUD:
    """Tests for create, read, update, delete operations."""

    def test_insert_and_get_product(self, db):
        """Inserting a product and fetching it should return the same data."""
        inserted = db.insert_product("Widget", 9.99, 100)
        assert inserted["name"] == "Widget"
        assert inserted["price"] == 9.99
        assert inserted["quantity"] == 100

        fetched = db.get_product(inserted["id"])
        assert fetched is not None
        assert fetched["name"] == "Widget"

    def test_get_nonexistent_returns_none(self, db):
        """Fetching a product that doesn't exist should return None."""
        assert db.get_product(99999) is None

    def test_update_product_quantity(self, db):
        """Updating a product's quantity should persist the change."""
        inserted = db.insert_product("Widget", 9.99, 100)
        updated = db.update_product(inserted["id"], quantity=50)
        assert updated["quantity"] == 50

    def test_update_product_name(self, db):
        """Updating a product's name should persist the change."""
        inserted = db.insert_product("Widget", 9.99, 100)
        updated = db.update_product(inserted["id"], name="Super Widget")
        assert updated["name"] == "Super Widget"

    def test_delete_product(self, db):
        """Deleting a product should remove it from the database."""
        inserted = db.insert_product("Widget", 9.99, 100)
        assert db.delete_product(inserted["id"]) is True
        assert db.get_product(inserted["id"]) is None

    def test_delete_nonexistent_returns_false(self, db):
        """Deleting a product that doesn't exist should return False."""
        assert db.delete_product(99999) is False

    def test_get_all_products(self, db):
        """get_all() should return every product in the table."""
        db.insert_product("Widget", 9.99, 10)
        db.insert_product("Gadget", 19.99, 20)
        db.insert_product("Doohickey", 4.99, 50)
        products = db.get_all()
        assert len(products) == 3


class TestDatabaseSearch:
    """Tests for the search functionality."""

    def test_search_by_name(self, db):
        """Search should find products with matching names."""
        db.insert_product("Blue Widget", 9.99, 10)
        db.insert_product("Red Gadget", 19.99, 20)
        results = db.search("Widget")
        assert len(results) == 1
        assert results[0]["name"] == "Blue Widget"

    def test_search_case_insensitive(self, db):
        """Search should be case-insensitive (ILIKE)."""
        db.insert_product("Blue Widget", 9.99, 10)
        results = db.search("blue widget")
        assert len(results) == 1

    def test_search_no_results(self, db):
        """Search with no matches should return an empty list."""
        db.insert_product("Widget", 9.99, 10)
        results = db.search("Nonexistent")
        assert len(results) == 0
