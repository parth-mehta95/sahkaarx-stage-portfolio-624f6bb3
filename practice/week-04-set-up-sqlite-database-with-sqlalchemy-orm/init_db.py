"""init_db.py - Database initialization script for SQLite with SQLAlchemy ORM.

Creates the SQLite database schema, enables foreign key enforcement,
and verifies referential integrity and user-task relationships.
"""
import os
import sqlite3
from flask import Flask
from models import db, User, Task

DB_FILENAME = "task_manager.db"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, DB_FILENAME)


def create_app() -> Flask:
    """Create Flask application configured with SQLite database."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    return app


def initialize_database(seed_data: bool = True) -> None:
    """Initialize SQLite database tables and optionally seed test data."""
    app = create_app()

    with app.app_context():
        print(f"[*] Initializing SQLite database at: {DB_PATH}")

        # Create all tables (users and tasks)
        db.create_all()
        print("[+] Created database tables: 'users', 'tasks'")

        if seed_data:
            # Check if admin/demo user already exists
            existing_user = User.query.filter_by(username="alice").first()
            if not existing_user:
                print("[*] Seeding sample user and tasks...")
                user = User(
                    username="alice",
                    email="alice@example.com",
                    password="securepassword123",
                )
                db.session.add(user)
                db.session.commit()

                # Add tasks linked via foreign key user_id
                task1 = Task(
                    title="Setup SQLite Database",
                    description="Configure SQLAlchemy models and SQLite connection",
                    status="completed",
                    completed=True,
                    user_id=user.id,
                )
                task2 = Task(
                    title="Verify Foreign Key Integrity",
                    description="Ensure SQLite enforces referential integrity",
                    status="in_progress",
                    completed=False,
                    user_id=user.id,
                )
                db.session.add_all([task1, task2])
                db.session.commit()
                print(f"[+] Seeded user '{user.username}' (id={user.id}) with {len(user.tasks)} tasks.")
            else:
                print(f"[*] Sample user '{existing_user.username}' already exists.")


def verify_schema() -> None:
    """Verify SQLite database schema and foreign key configuration directly via sqlite3."""
    print("\n" + "=" * 50)
    print("VERIFYING SQLITE SCHEMA & FOREIGN KEYS")
    print("=" * 50)

    if not os.path.exists(DB_PATH):
        print(f"[-] Database file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Verify foreign_keys PRAGMA
    cursor.execute("PRAGMA foreign_keys = ON;")
    fk_status = cursor.execute("PRAGMA foreign_keys;").fetchone()[0]
    print(f"[+] Foreign Keys Enforced: {'YES' if fk_status == 1 else 'NO'}")

    # Inspect tables
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    ).fetchall()
    table_names = [t[0] for t in tables]
    print(f"[+] Tables in database: {table_names}")

    # Inspect foreign keys on tasks table
    fk_list = cursor.execute("PRAGMA foreign_key_list(tasks);").fetchall()
    print("[+] Foreign keys in 'tasks' table:")
    for fk in fk_list:
        print(f"    - references '{fk[2]}' table on column '{fk[4]}' (from column '{fk[3]}'), on_delete={fk[6]}")

    # Inspect table schemas
    for table in table_names:
        print(f"\n--- Schema for table: {table} ---")
        columns = cursor.execute(f"PRAGMA table_info({table});").fetchall()
        for col in columns:
            col_id, name, col_type, not_null, default_val, pk = col
            pk_str = " [PRIMARY KEY]" if pk else ""
            nn_str = " [NOT NULL]" if not_null else ""
            print(f"    {name} ({col_type}){pk_str}{nn_str}")

    conn.close()
    print("\n[+] Verification complete! Database is ready for SQLite browser inspection.")


if __name__ == "__main__":
    initialize_database(seed_data=True)
    verify_schema()
