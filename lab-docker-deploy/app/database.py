"""
database.py - PostgreSQL database operations for the Inventory System.

This module handles all direct database interactions using psycopg2.
It is separate from the business logic (inventory.py) so that:
  - Unit tests can run WITHOUT a database
  - Integration tests connect to a REAL Postgres (via service containers)

Connection pooling note:
    In production, you would use psycopg2.pool.ThreadedConnectionPool
    or an async driver like asyncpg for better performance under load.
    For this lab, a single connection is sufficient to demonstrate
    the CI/CD concepts.
"""

import psycopg2
import psycopg2.extras


class DatabaseManager:
    """
    Manages PostgreSQL connections and CRUD operations for products.

    Usage:
        db = DatabaseManager()
        db.connect("postgresql://user:pass@localhost:5432/inventory")
        db.create_tables()
        db.insert_product("Widget", 9.99, 100)
        db.disconnect()
    """

    def __init__(self):
        """Initialize the DatabaseManager with no active connection."""
        self._conn = None
        self._cursor = None

    def connect(self, connection_string):
        """
        Establish a connection to PostgreSQL.

        Args:
            connection_string: PostgreSQL connection URI,
                e.g. "postgresql://user:pass@host:5432/dbname"

        Raises:
            psycopg2.OperationalError: If the connection fails.
        """
        self._conn = psycopg2.connect(connection_string)
        self._conn.autocommit = True
        self._cursor = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def disconnect(self):
        """Close the database connection and cursor."""
        if self._cursor:
            self._cursor.close()
            self._cursor = None
        if self._conn:
            self._conn.close()
            self._conn = None

    def is_connected(self):
        """Check whether the database connection is active."""
        if self._conn is None:
            return False
        try:
            self._cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    def create_tables(self):
        """
        Create the products table if it does not already exist.

        The table schema:
            id       SERIAL PRIMARY KEY
            name     VARCHAR(255) NOT NULL
            price    DECIMAL(10,2) NOT NULL
            quantity INTEGER NOT NULL DEFAULT 0
        """
        self._cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id       SERIAL PRIMARY KEY,
                name     VARCHAR(255) NOT NULL,
                price    DECIMAL(10, 2) NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0
            )
        """)

    def insert_product(self, name, price, quantity):
        """
        Insert a new product into the database.

        Args:
            name: Product name.
            price: Unit price.
            quantity: Stock quantity.

        Returns:
            dict: The inserted product row (including generated id).
        """
        self._cursor.execute(
            """
            INSERT INTO products (name, price, quantity)
            VALUES (%s, %s, %s)
            RETURNING id, name, price, quantity
            """,
            (name, price, quantity),
        )
        row = self._cursor.fetchone()
        return {
            "id": row["id"],
            "name": row["name"],
            "price": float(row["price"]),
            "quantity": row["quantity"],
        }

    def get_product(self, product_id):
        """
        Retrieve a single product by ID.

        Args:
            product_id: The product's primary key.

        Returns:
            dict or None: The product row, or None if not found.
        """
        self._cursor.execute(
            "SELECT id, name, price, quantity FROM products WHERE id = %s",
            (product_id,),
        )
        row = self._cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "price": float(row["price"]),
            "quantity": row["quantity"],
        }

    def update_product(self, product_id, **fields):
        """
        Update one or more fields on an existing product.

        Args:
            product_id: The product's primary key.
            **fields: Keyword arguments for columns to update
                      (e.g. name="New Name", quantity=50).

        Returns:
            dict or None: The updated product row, or None if not found.
        """
        if not fields:
            return self.get_product(product_id)

        set_clauses = []
        values = []
        for column, value in fields.items():
            set_clauses.append(f"{column} = %s")
            values.append(value)
        values.append(product_id)

        query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, name, price, quantity"
        self._cursor.execute(query, values)
        row = self._cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "price": float(row["price"]),
            "quantity": row["quantity"],
        }

    def delete_product(self, product_id):
        """
        Delete a product by ID.

        Args:
            product_id: The product's primary key.

        Returns:
            bool: True if a row was deleted, False otherwise.
        """
        self._cursor.execute(
            "DELETE FROM products WHERE id = %s", (product_id,)
        )
        return self._cursor.rowcount > 0

    def get_all(self):
        """
        Retrieve all products.

        Returns:
            list[dict]: All product rows.
        """
        self._cursor.execute("SELECT id, name, price, quantity FROM products ORDER BY id")
        rows = self._cursor.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "price": float(r["price"]),
                "quantity": r["quantity"],
            }
            for r in rows
        ]

    def search(self, query):
        """
        Search products by name (case-insensitive partial match).

        Args:
            query: The search string.

        Returns:
            list[dict]: Matching product rows.
        """
        self._cursor.execute(
            "SELECT id, name, price, quantity FROM products WHERE name ILIKE %s ORDER BY id",
            (f"%{query}%",),
        )
        rows = self._cursor.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "price": float(r["price"]),
                "quantity": r["quantity"],
            }
            for r in rows
        ]
