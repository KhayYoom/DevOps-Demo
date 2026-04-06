"""
api.py - HTTP API server for the Inventory Management System.

Endpoints:
    GET  /health              - Health check (DB + Redis status)
    GET  /products            - List all products
    GET  /products/{id}       - Get a single product
    POST /products            - Create a new product
    PUT  /products/{id}/stock - Update stock quantity
    DELETE /products/{id}     - Delete a product
    GET  /products/search?q=  - Search products by name
    GET  /stats               - Inventory statistics

This API uses only the Python standard library (http.server) so there
are no extra framework dependencies. In production you would use
Flask, FastAPI, or Django REST Framework instead.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import re

from app.inventory import InventoryManager, ProductNotFoundError, ValidationError


# Global inventory instance (in-memory for simplicity)
inventory = InventoryManager()

# Optional database and cache connections
db_manager = None
cache_manager = None


def _init_services():
    """Initialize database and cache connections if env vars are set."""
    global db_manager, cache_manager

    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        try:
            from app.database import DatabaseManager
            db_manager = DatabaseManager()
            db_manager.connect(db_url)
            db_manager.create_tables()
        except Exception as e:
            print(f"WARNING: Could not connect to database: {e}")
            db_manager = None

    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            from app.cache import CacheManager
            cache_manager = CacheManager()
            cache_manager.connect(redis_url)
        except Exception as e:
            print(f"WARNING: Could not connect to Redis: {e}")
            cache_manager = None


class InventoryHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Inventory API."""

    def _send_response(self, status_code, data):
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self):
        """Read and parse the JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        return json.loads(body)

    def _extract_id(self, pattern):
        """Extract an integer ID from the URL path."""
        match = re.match(pattern, self.path)
        if match:
            return int(match.group(1))
        return None

    # -----------------------------------------------------------------
    # GET routes
    # -----------------------------------------------------------------

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/products":
            self._handle_get_all_products()
        elif self.path.startswith("/products/search"):
            self._handle_search()
        elif re.match(r"^/products/(\d+)$", self.path):
            self._handle_get_product()
        elif self.path == "/stats":
            self._handle_stats()
        elif self.path == "/":
            self._send_response(200, {
                "message": "Inventory Management API",
                "version": "1.0.0",
                "endpoints": [
                    "GET  /health",
                    "GET  /products",
                    "GET  /products/{id}",
                    "POST /products",
                    "PUT  /products/{id}/stock",
                    "DELETE /products/{id}",
                    "GET  /products/search?q=query",
                    "GET  /stats",
                ],
            })
        else:
            self._send_response(404, {"error": "Not found"})

    def _handle_health(self):
        """Return health status including DB and Redis connectivity."""
        db_ok = False
        redis_ok = False

        if db_manager:
            try:
                db_ok = db_manager.is_connected()
            except Exception:
                db_ok = False

        if cache_manager:
            try:
                redis_ok = cache_manager.is_connected()
            except Exception:
                redis_ok = False

        self._send_response(200, {
            "status": "healthy",
            "service": "inventory-api",
            "version": "1.0.0",
            "database": "connected" if db_ok else "not connected",
            "cache": "connected" if redis_ok else "not connected",
        })

    def _handle_get_all_products(self):
        """Return all products."""
        products = inventory.get_all_products()
        self._send_response(200, {"products": products, "count": len(products)})

    def _handle_get_product(self):
        """Return a single product by ID."""
        product_id = self._extract_id(r"^/products/(\d+)$")
        try:
            product = inventory.get_product(product_id)
            self._send_response(200, product)
        except ProductNotFoundError as e:
            self._send_response(404, {"error": str(e)})

    def _handle_search(self):
        """Search products by name query parameter."""
        # Parse query string: /products/search?q=something
        query = ""
        if "?" in self.path:
            params = self.path.split("?", 1)[1]
            for param in params.split("&"):
                if param.startswith("q="):
                    query = param[2:]
                    break

        if not query:
            self._send_response(400, {"error": "Missing search query parameter 'q'"})
            return

        try:
            results = inventory.search_products(query)
            self._send_response(200, {"results": results, "count": len(results)})
        except ValidationError as e:
            self._send_response(400, {"error": str(e)})

    def _handle_stats(self):
        """Return inventory statistics."""
        low_stock = inventory.get_low_stock()
        total_value = inventory.get_inventory_value()
        all_products = inventory.get_all_products()
        self._send_response(200, {
            "total_products": len(all_products),
            "low_stock_count": len(low_stock),
            "total_inventory_value": total_value,
        })

    # -----------------------------------------------------------------
    # POST routes
    # -----------------------------------------------------------------

    def do_POST(self):
        """Handle POST requests."""
        if self.path == "/products":
            self._handle_create_product()
        else:
            self._send_response(404, {"error": "Not found"})

    def _handle_create_product(self):
        """Create a new product."""
        try:
            data = self._read_body()
            name = data.get("name")
            price = data.get("price")
            quantity = data.get("quantity", 0)
            product = inventory.add_product(name, price, quantity)
            self._send_response(201, product)
        except ValidationError as e:
            self._send_response(400, {"error": str(e)})
        except (json.JSONDecodeError, TypeError) as e:
            self._send_response(400, {"error": f"Invalid request body: {e}"})

    # -----------------------------------------------------------------
    # PUT routes
    # -----------------------------------------------------------------

    def do_PUT(self):
        """Handle PUT requests."""
        if re.match(r"^/products/(\d+)/stock$", self.path):
            self._handle_update_stock()
        else:
            self._send_response(404, {"error": "Not found"})

    def _handle_update_stock(self):
        """Update the stock quantity for a product."""
        product_id = self._extract_id(r"^/products/(\d+)/stock$")
        try:
            data = self._read_body()
            quantity = data.get("quantity")
            product = inventory.update_stock(product_id, quantity)
            self._send_response(200, product)
        except ProductNotFoundError as e:
            self._send_response(404, {"error": str(e)})
        except ValidationError as e:
            self._send_response(400, {"error": str(e)})
        except (json.JSONDecodeError, TypeError) as e:
            self._send_response(400, {"error": f"Invalid request body: {e}"})

    # -----------------------------------------------------------------
    # DELETE routes
    # -----------------------------------------------------------------

    def do_DELETE(self):
        """Handle DELETE requests."""
        if re.match(r"^/products/(\d+)$", self.path):
            self._handle_delete_product()
        else:
            self._send_response(404, {"error": "Not found"})

    def _handle_delete_product(self):
        """Delete a product by ID."""
        product_id = self._extract_id(r"^/products/(\d+)$")
        try:
            inventory.remove_product(product_id)
            self._send_response(200, {"message": f"Product {product_id} deleted"})
        except ProductNotFoundError as e:
            self._send_response(404, {"error": str(e)})

    def log_message(self, format, *args):
        """Suppress default logging (cleaner test output)."""
        pass


def create_server(port=8080):
    """Create and return an HTTP server instance."""
    _init_services()
    server = HTTPServer(("127.0.0.1", port), InventoryHandler)
    return server


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server = create_server(port)
    print(f"Inventory API running on http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
