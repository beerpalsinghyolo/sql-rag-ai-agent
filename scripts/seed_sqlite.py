"""Seed a demo SQLite e-commerce database."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "demo.db"

CUSTOMERS = [
    (1, "Alice Johnson", "alice@example.com", "New York"),
    (2, "Bob Smith", "bob@example.com", "Los Angeles"),
    (3, "Carol Williams", "carol@example.com", "Chicago"),
    (4, "David Brown", "david@example.com", "New York"),
    (5, "Eve Davis", "eve@example.com", "Houston"),
    (6, "Frank Miller", "frank@example.com", "Chicago"),
    (7, "Grace Wilson", "grace@example.com", "Seattle"),
    (8, "Henry Moore", "henry@example.com", "Los Angeles"),
]

PRODUCTS = [
    (1, "Wireless Mouse", "Electronics", 29.99),
    (2, "Mechanical Keyboard", "Electronics", 89.99),
    (3, "USB-C Hub", "Electronics", 45.50),
    (4, "Office Chair", "Furniture", 249.00),
    (5, "Standing Desk", "Furniture", 399.99),
    (6, "Notebook Pack", "Stationery", 12.99),
    (7, "Ballpoint Pens", "Stationery", 5.49),
    (8, "Monitor Stand", "Electronics", 34.99),
    (9, "Desk Lamp", "Furniture", 42.00),
    (10, "Sticky Notes", "Stationery", 3.99),
]

ORDERS = [
    (1, 1, "2024-01-15", 119.98),
    (2, 2, "2024-01-18", 89.99),
    (3, 3, "2024-02-01", 294.49),
    (4, 1, "2024-02-10", 45.50),
    (5, 4, "2024-02-14", 649.98),
    (6, 5, "2024-03-05", 18.48),
    (7, 6, "2024-03-12", 124.97),
    (8, 7, "2024-03-20", 399.99),
    (9, 2, "2024-04-02", 64.98),
    (10, 8, "2024-04-15", 279.98),
    (11, 3, "2024-04-22", 12.99),
    (12, 4, "2024-05-01", 34.99),
]

ORDER_ITEMS = [
    (1, 1, 2),
    (1, 2, 1),
    (2, 2, 1),
    (3, 4, 1),
    (3, 6, 1),
    (4, 3, 1),
    (5, 4, 1),
    (5, 5, 1),
    (6, 6, 1),
    (6, 7, 1),
    (7, 1, 1),
    (7, 8, 1),
    (7, 10, 3),
    (8, 5, 1),
    (9, 1, 1),
    (9, 8, 1),
    (10, 4, 1),
    (10, 9, 1),
    (11, 6, 1),
    (12, 8, 1),
]


def seed() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            city TEXT NOT NULL
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            total REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE order_items (
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            PRIMARY KEY (order_id, product_id),
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )

    cur.executemany(
        "INSERT INTO customers (id, name, email, city) VALUES (?, ?, ?, ?)",
        CUSTOMERS,
    )
    cur.executemany(
        "INSERT INTO products (id, name, category, price) VALUES (?, ?, ?, ?)",
        PRODUCTS,
    )
    cur.executemany(
        "INSERT INTO orders (id, customer_id, order_date, total) VALUES (?, ?, ?, ?)",
        ORDERS,
    )
    cur.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
        ORDER_ITEMS,
    )

    conn.commit()
    conn.close()
    print(f"Seeded demo database at {DB_PATH}")


if __name__ == "__main__":
    seed()
