"""
inventory.py - Core business logic for the Inventory Management System.

This module contains PURE PYTHON logic with NO database dependencies.
The InventoryManager class stores products in an internal dict so that
unit tests can run without Postgres or Redis.

In production, the database layer (database.py) and cache layer (cache.py)
handle persistence. This separation makes testing fast and reliable.
"""


class ProductNotFoundError(Exception):
    """Raised when a product cannot be found by its ID."""
    pass


class ValidationError(Exception):
    """Raised when product data fails validation."""
    pass


class InventoryManager:
    """
    Manages product inventory using an in-memory dictionary.

    Products are stored as:
        {product_id: {"id": int, "name": str, "price": float, "quantity": int}}

    This class contains ONLY business logic -- no database calls.
    """

    def __init__(self):
        """Initialize the inventory manager with an empty product store."""
        self._products = {}
        self._next_id = 1

    def _validate_product_data(self, name, price, quantity):
        """
        Validate product data before creating or updating.

        Args:
            name: Product name (must be non-empty string).
            price: Product price (must be a positive number).
            quantity: Stock quantity (must be a non-negative integer).

        Raises:
            ValidationError: If any field is invalid.
        """
        if not name or not isinstance(name, str):
            raise ValidationError("Product name must be a non-empty string")
        if name != name.strip():
            raise ValidationError("Product name must not have leading/trailing whitespace")
        if not isinstance(price, (int, float)) or price <= 0:
            raise ValidationError("Price must be a positive number")
        if not isinstance(quantity, int) or quantity < 0:
            raise ValidationError("Quantity must be a non-negative integer")

    def add_product(self, name, price, quantity):
        """
        Add a new product to the inventory.

        Args:
            name: Product name.
            price: Unit price (positive number).
            quantity: Initial stock quantity (non-negative integer).

        Returns:
            dict: The created product with its assigned ID.

        Raises:
            ValidationError: If the input data is invalid.
        """
        self._validate_product_data(name, price, quantity)

        product_id = self._next_id
        self._next_id += 1

        product = {
            "id": product_id,
            "name": name,
            "price": round(float(price), 2),
            "quantity": quantity,
        }
        self._products[product_id] = product
        return product.copy()

    def get_product(self, product_id):
        """
        Retrieve a product by its ID.

        Args:
            product_id: The unique product identifier.

        Returns:
            dict: A copy of the product data.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
        """
        if product_id not in self._products:
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        return self._products[product_id].copy()

    def update_stock(self, product_id, quantity):
        """
        Update the stock quantity for a product.

        Args:
            product_id: The unique product identifier.
            quantity: New stock quantity (non-negative integer).

        Returns:
            dict: The updated product data.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
            ValidationError: If the quantity is invalid.
        """
        if product_id not in self._products:
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        if not isinstance(quantity, int) or quantity < 0:
            raise ValidationError("Quantity must be a non-negative integer")

        self._products[product_id]["quantity"] = quantity
        return self._products[product_id].copy()

    def remove_product(self, product_id):
        """
        Remove a product from the inventory.

        Args:
            product_id: The unique product identifier.

        Returns:
            dict: The removed product data.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
        """
        if product_id not in self._products:
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        return self._products.pop(product_id)

    def get_all_products(self):
        """
        Retrieve all products in the inventory.

        Returns:
            list[dict]: A list of all product dictionaries.
        """
        return [p.copy() for p in self._products.values()]

    def search_products(self, query):
        """
        Search products by name (case-insensitive partial match).

        Args:
            query: The search string.

        Returns:
            list[dict]: Products whose names contain the query string.

        Raises:
            ValidationError: If the query is empty.
        """
        if not query or not isinstance(query, str):
            raise ValidationError("Search query must be a non-empty string")

        query_lower = query.lower()
        return [
            p.copy()
            for p in self._products.values()
            if query_lower in p["name"].lower()
        ]

    def get_low_stock(self, threshold=5):
        """
        Find products with stock at or below the given threshold.

        Args:
            threshold: Stock level threshold (default 5).

        Returns:
            list[dict]: Products with quantity <= threshold.
        """
        return [
            p.copy()
            for p in self._products.values()
            if p["quantity"] <= threshold
        ]

    def get_inventory_value(self):
        """
        Calculate the total value of all inventory.

        Returns:
            float: Sum of (price * quantity) for every product.
        """
        total = sum(
            p["price"] * p["quantity"] for p in self._products.values()
        )
        return round(total, 2)
