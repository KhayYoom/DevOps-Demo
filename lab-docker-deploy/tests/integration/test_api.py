"""
test_api.py - Integration tests for the Inventory API.

These tests start a REAL HTTP server and send REAL HTTP requests.
They test the full stack: HTTP -> routing -> business logic -> response.

No external services (Postgres, Redis) are needed because the API
falls back to the in-memory InventoryManager when DATABASE_URL and
REDIS_URL are not set.
"""

import json
import threading
import pytest
import requests

from app.api import create_server, inventory


BASE_URL = "http://127.0.0.1:8082"


@pytest.fixture(scope="module", autouse=True)
def api_server():
    """Start the API server in a background thread for the test module."""
    # Reset the in-memory inventory before all tests
    inventory._products.clear()
    inventory._next_id = 1

    server = create_server(port=8082)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


@pytest.fixture(autouse=True)
def reset_inventory():
    """Reset inventory state between tests."""
    inventory._products.clear()
    inventory._next_id = 1


class TestHealthEndpoint:
    """Tests for the GET /health endpoint."""

    def test_health_returns_200(self):
        """Health endpoint should return 200 OK."""
        resp = requests.get(f"{BASE_URL}/health")
        assert resp.status_code == 200

    def test_health_returns_status_healthy(self):
        """Health response should include status: healthy."""
        resp = requests.get(f"{BASE_URL}/health")
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "inventory-api"


class TestRootEndpoint:
    """Tests for the GET / endpoint."""

    def test_root_returns_api_info(self):
        """Root endpoint should return API metadata."""
        resp = requests.get(f"{BASE_URL}/")
        assert resp.status_code == 200
        data = resp.json()
        assert "Inventory" in data["message"]


class TestCreateProduct:
    """Tests for the POST /products endpoint."""

    def test_create_product(self):
        """Creating a product should return 201 with the product data."""
        resp = requests.post(f"{BASE_URL}/products", json={
            "name": "Widget",
            "price": 9.99,
            "quantity": 100,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Widget"
        assert data["id"] == 1

    def test_create_product_invalid_data(self):
        """Creating a product with invalid data should return 400."""
        resp = requests.post(f"{BASE_URL}/products", json={
            "name": "",
            "price": 9.99,
            "quantity": 10,
        })
        assert resp.status_code == 400


class TestGetProducts:
    """Tests for the GET /products and GET /products/{id} endpoints."""

    def test_get_all_products_empty(self):
        """When no products exist, should return an empty list."""
        resp = requests.get(f"{BASE_URL}/products")
        assert resp.status_code == 200
        data = resp.json()
        assert data["products"] == []
        assert data["count"] == 0

    def test_get_all_products_with_data(self):
        """After adding products, they should appear in the list."""
        requests.post(f"{BASE_URL}/products", json={"name": "A", "price": 1.0, "quantity": 1})
        requests.post(f"{BASE_URL}/products", json={"name": "B", "price": 2.0, "quantity": 2})
        resp = requests.get(f"{BASE_URL}/products")
        data = resp.json()
        assert data["count"] == 2

    def test_get_single_product(self):
        """Fetching a product by ID should return its data."""
        create_resp = requests.post(f"{BASE_URL}/products", json={
            "name": "Widget", "price": 9.99, "quantity": 10,
        })
        pid = create_resp.json()["id"]
        resp = requests.get(f"{BASE_URL}/products/{pid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Widget"

    def test_get_nonexistent_product(self):
        """Fetching a missing product should return 404."""
        resp = requests.get(f"{BASE_URL}/products/999")
        assert resp.status_code == 404


class TestUpdateStock:
    """Tests for the PUT /products/{id}/stock endpoint."""

    def test_update_stock(self):
        """Updating stock should change the quantity."""
        create_resp = requests.post(f"{BASE_URL}/products", json={
            "name": "Widget", "price": 9.99, "quantity": 100,
        })
        pid = create_resp.json()["id"]
        resp = requests.put(f"{BASE_URL}/products/{pid}/stock", json={"quantity": 50})
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 50

    def test_update_stock_nonexistent(self):
        """Updating stock on a missing product should return 404."""
        resp = requests.put(f"{BASE_URL}/products/999/stock", json={"quantity": 10})
        assert resp.status_code == 404


class TestDeleteProduct:
    """Tests for the DELETE /products/{id} endpoint."""

    def test_delete_product(self):
        """Deleting a product should return 200."""
        create_resp = requests.post(f"{BASE_URL}/products", json={
            "name": "Widget", "price": 9.99, "quantity": 10,
        })
        pid = create_resp.json()["id"]
        resp = requests.delete(f"{BASE_URL}/products/{pid}")
        assert resp.status_code == 200

    def test_delete_nonexistent_product(self):
        """Deleting a missing product should return 404."""
        resp = requests.delete(f"{BASE_URL}/products/999")
        assert resp.status_code == 404


class TestSearchProducts:
    """Tests for the GET /products/search?q= endpoint."""

    def test_search_finds_product(self):
        """Search should return matching products."""
        requests.post(f"{BASE_URL}/products", json={"name": "Blue Widget", "price": 9.99, "quantity": 10})
        requests.post(f"{BASE_URL}/products", json={"name": "Red Gadget", "price": 19.99, "quantity": 20})
        resp = requests.get(f"{BASE_URL}/products/search?q=Widget")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    def test_search_missing_query(self):
        """Search without a query parameter should return 400."""
        resp = requests.get(f"{BASE_URL}/products/search")
        assert resp.status_code == 400


class TestStatsEndpoint:
    """Tests for the GET /stats endpoint."""

    def test_stats_returns_data(self):
        """Stats endpoint should return inventory summary."""
        requests.post(f"{BASE_URL}/products", json={"name": "Widget", "price": 10.00, "quantity": 5})
        resp = requests.get(f"{BASE_URL}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_products"] == 1
        assert data["total_inventory_value"] == 50.0


class TestNotFound:
    """Tests for unknown routes."""

    def test_unknown_route_returns_404(self):
        """An unknown route should return 404."""
        resp = requests.get(f"{BASE_URL}/nonexistent")
        assert resp.status_code == 404
