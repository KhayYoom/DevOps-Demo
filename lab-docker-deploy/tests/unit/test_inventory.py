"""
test_inventory.py - Unit tests for the InventoryManager class.

These tests exercise PURE BUSINESS LOGIC only.
No database, no Redis, no network -- just Python.
That's why they run fast and reliably everywhere.
"""

import pytest
from app.inventory import InventoryManager, ProductNotFoundError, ValidationError


class TestAddProduct:
    """Tests for adding products to the inventory."""

    def test_add_product_returns_product_with_id(self):
        """Adding a product should return a dict with an auto-assigned ID."""
        mgr = InventoryManager()
        product = mgr.add_product("Widget", 9.99, 100)
        assert product["id"] == 1
        assert product["name"] == "Widget"
        assert product["price"] == 9.99
        assert product["quantity"] == 100

    def test_add_multiple_products_increments_id(self):
        """Each new product should get a sequential ID."""
        mgr = InventoryManager()
        p1 = mgr.add_product("Widget", 9.99, 10)
        p2 = mgr.add_product("Gadget", 19.99, 20)
        p3 = mgr.add_product("Doohickey", 4.99, 50)
        assert p1["id"] == 1
        assert p2["id"] == 2
        assert p3["id"] == 3

    def test_add_product_rounds_price(self):
        """Price should be rounded to two decimal places."""
        mgr = InventoryManager()
        product = mgr.add_product("Widget", 9.999, 10)
        assert product["price"] == 10.0

    def test_add_product_with_zero_quantity(self):
        """A product can be added with zero initial stock."""
        mgr = InventoryManager()
        product = mgr.add_product("Widget", 5.00, 0)
        assert product["quantity"] == 0

    def test_add_product_empty_name_raises_error(self):
        """An empty product name should raise ValidationError."""
        mgr = InventoryManager()
        with pytest.raises(ValidationError, match="non-empty string"):
            mgr.add_product("", 9.99, 10)

    def test_add_product_none_name_raises_error(self):
        """A None product name should raise ValidationError."""
        mgr = InventoryManager()
        with pytest.raises(ValidationError):
            mgr.add_product(None, 9.99, 10)

    def test_add_product_negative_price_raises_error(self):
        """A negative price should raise ValidationError."""
        mgr = InventoryManager()
        with pytest.raises(ValidationError, match="positive number"):
            mgr.add_product("Widget", -1.00, 10)

    def test_add_product_zero_price_raises_error(self):
        """A zero price should raise ValidationError."""
        mgr = InventoryManager()
        with pytest.raises(ValidationError, match="positive number"):
            mgr.add_product("Widget", 0, 10)

    def test_add_product_negative_quantity_raises_error(self):
        """A negative quantity should raise ValidationError."""
        mgr = InventoryManager()
        with pytest.raises(ValidationError, match="non-negative integer"):
            mgr.add_product("Widget", 9.99, -5)

    def test_add_product_float_quantity_raises_error(self):
        """A float quantity should raise ValidationError (must be int)."""
        mgr = InventoryManager()
        with pytest.raises(ValidationError, match="non-negative integer"):
            mgr.add_product("Widget", 9.99, 10.5)

    def test_add_product_whitespace_name_raises_error(self):
        """A name with leading/trailing whitespace should raise ValidationError."""
        mgr = InventoryManager()
        with pytest.raises(ValidationError, match="whitespace"):
            mgr.add_product("  Widget  ", 9.99, 10)


class TestGetProduct:
    """Tests for retrieving a product by ID."""

    def test_get_existing_product(self):
        """Retrieving an existing product should return its data."""
        mgr = InventoryManager()
        added = mgr.add_product("Widget", 9.99, 100)
        fetched = mgr.get_product(added["id"])
        assert fetched == added

    def test_get_product_returns_copy(self):
        """Returned product should be a copy, not a reference."""
        mgr = InventoryManager()
        added = mgr.add_product("Widget", 9.99, 100)
        fetched = mgr.get_product(added["id"])
        fetched["name"] = "MODIFIED"
        original = mgr.get_product(added["id"])
        assert original["name"] == "Widget"

    def test_get_nonexistent_product_raises_error(self):
        """Requesting a missing product should raise ProductNotFoundError."""
        mgr = InventoryManager()
        with pytest.raises(ProductNotFoundError, match="999"):
            mgr.get_product(999)


class TestUpdateStock:
    """Tests for updating product stock levels."""

    def test_update_stock_changes_quantity(self):
        """Updating stock should change the product's quantity."""
        mgr = InventoryManager()
        p = mgr.add_product("Widget", 9.99, 100)
        updated = mgr.update_stock(p["id"], 50)
        assert updated["quantity"] == 50

    def test_update_stock_to_zero(self):
        """Stock can be set to zero (out of stock)."""
        mgr = InventoryManager()
        p = mgr.add_product("Widget", 9.99, 100)
        updated = mgr.update_stock(p["id"], 0)
        assert updated["quantity"] == 0

    def test_update_stock_nonexistent_raises_error(self):
        """Updating stock on a missing product should raise an error."""
        mgr = InventoryManager()
        with pytest.raises(ProductNotFoundError):
            mgr.update_stock(999, 10)

    def test_update_stock_negative_raises_error(self):
        """Setting negative stock should raise ValidationError."""
        mgr = InventoryManager()
        p = mgr.add_product("Widget", 9.99, 100)
        with pytest.raises(ValidationError, match="non-negative"):
            mgr.update_stock(p["id"], -10)


class TestRemoveProduct:
    """Tests for removing products from inventory."""

    def test_remove_existing_product(self):
        """Removing an existing product should return its data."""
        mgr = InventoryManager()
        p = mgr.add_product("Widget", 9.99, 100)
        removed = mgr.remove_product(p["id"])
        assert removed["name"] == "Widget"

    def test_remove_product_is_gone(self):
        """After removal, the product should no longer be retrievable."""
        mgr = InventoryManager()
        p = mgr.add_product("Widget", 9.99, 100)
        mgr.remove_product(p["id"])
        with pytest.raises(ProductNotFoundError):
            mgr.get_product(p["id"])

    def test_remove_nonexistent_raises_error(self):
        """Removing a missing product should raise ProductNotFoundError."""
        mgr = InventoryManager()
        with pytest.raises(ProductNotFoundError):
            mgr.remove_product(999)


class TestGetAllProducts:
    """Tests for listing all products."""

    def test_empty_inventory(self):
        """An empty inventory should return an empty list."""
        mgr = InventoryManager()
        assert mgr.get_all_products() == []

    def test_returns_all_added_products(self):
        """All added products should appear in the list."""
        mgr = InventoryManager()
        mgr.add_product("Widget", 9.99, 10)
        mgr.add_product("Gadget", 19.99, 20)
        products = mgr.get_all_products()
        assert len(products) == 2


class TestSearchProducts:
    """Tests for the search functionality."""

    def test_search_finds_matching_product(self):
        """Search should return products whose names contain the query."""
        mgr = InventoryManager()
        mgr.add_product("Blue Widget", 9.99, 10)
        mgr.add_product("Red Gadget", 19.99, 20)
        results = mgr.search_products("Widget")
        assert len(results) == 1
        assert results[0]["name"] == "Blue Widget"

    def test_search_is_case_insensitive(self):
        """Search should be case-insensitive."""
        mgr = InventoryManager()
        mgr.add_product("Blue Widget", 9.99, 10)
        results = mgr.search_products("blue widget")
        assert len(results) == 1

    def test_search_no_results(self):
        """Search with no matches should return an empty list."""
        mgr = InventoryManager()
        mgr.add_product("Widget", 9.99, 10)
        results = mgr.search_products("Nonexistent")
        assert len(results) == 0

    def test_search_empty_query_raises_error(self):
        """An empty search query should raise ValidationError."""
        mgr = InventoryManager()
        with pytest.raises(ValidationError, match="non-empty string"):
            mgr.search_products("")


class TestLowStock:
    """Tests for the low-stock report."""

    def test_low_stock_default_threshold(self):
        """Products with quantity <= 5 should appear in low stock."""
        mgr = InventoryManager()
        mgr.add_product("Low Item", 9.99, 3)
        mgr.add_product("High Item", 19.99, 100)
        low = mgr.get_low_stock()
        assert len(low) == 1
        assert low[0]["name"] == "Low Item"

    def test_low_stock_custom_threshold(self):
        """Custom threshold should be respected."""
        mgr = InventoryManager()
        mgr.add_product("Item A", 9.99, 10)
        mgr.add_product("Item B", 19.99, 20)
        low = mgr.get_low_stock(threshold=15)
        assert len(low) == 1
        assert low[0]["name"] == "Item A"

    def test_low_stock_empty_inventory(self):
        """Low stock on empty inventory should return empty list."""
        mgr = InventoryManager()
        assert mgr.get_low_stock() == []


class TestInventoryValue:
    """Tests for the total inventory value calculation."""

    def test_value_calculation(self):
        """Total value should be sum of price * quantity for all products."""
        mgr = InventoryManager()
        mgr.add_product("Widget", 10.00, 5)     # 50.00
        mgr.add_product("Gadget", 20.00, 3)     # 60.00
        assert mgr.get_inventory_value() == 110.00

    def test_value_empty_inventory(self):
        """Empty inventory should have zero value."""
        mgr = InventoryManager()
        assert mgr.get_inventory_value() == 0.0

    def test_value_with_zero_quantity(self):
        """Products with zero quantity contribute zero value."""
        mgr = InventoryManager()
        mgr.add_product("Widget", 100.00, 0)
        assert mgr.get_inventory_value() == 0.0
