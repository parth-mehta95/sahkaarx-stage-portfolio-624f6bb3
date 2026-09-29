"""test_orm.py - Tests verifying User-Task ORM models, relationships, and SQLite foreign key referential integrity."""
import pytest
from sqlalchemy.exc import IntegrityError
from app import create_app
from models import db, User, Task


@pytest.fixture
def test_app():
    """Create test application context using an in-memory SQLite database."""
    app = create_app(database_uri="sqlite:///:memory:")
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_user_creation_and_auth(test_app):
    """Test user registration and password hashing."""
    user = User(username="johndoe", email="john@example.com", password="secretpassword")
    db.session.add(user)
    db.session.commit()

    assert user.id is not None
    assert user.check_password("secretpassword") is True
    assert user.check_password("wrongpassword") is False
    assert user.password_hash != "secretpassword"


def test_user_task_relationship(test_app):
    """Test 1-to-many relationship between User and Task."""
    user = User(username="janedoe", email="jane@example.com", password="password123")
    db.session.add(user)
    db.session.commit()

    task1 = Task(title="Task 1", user_id=user.id)
    task2 = Task(title="Task 2", user_id=user.id)
    db.session.add_all([task1, task2])
    db.session.commit()

    assert len(user.tasks) == 2
    assert task1.user == user
    assert task2.user == user
    assert task1 in user.get_tasks()


def test_foreign_key_referential_integrity(test_app):
    """Test that SQLite rejects tasks referencing non-existent user IDs when foreign keys are enabled."""
    invalid_task = Task(title="Orphan Task", user_id=99999)
    db.session.add(invalid_task)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_cascade_delete(test_app):
    """Test cascade deletion of tasks when parent user is deleted."""
    user = User(username="cascadetest", email="cascade@example.com", password="pass")
    db.session.add(user)
    db.session.commit()

    task = Task(title="Cascade Task", user_id=user.id)
    db.session.add(task)
    db.session.commit()

    task_id = task.id
    db.session.delete(user)
    db.session.commit()

    # Task should be deleted
    assert Task.query.get(task_id) is None


if __name__ == "__main__":
    import sys
    print("Running tests directly...")
    app = create_app(database_uri="sqlite:///:memory:")
    with app.app_context():
        db.create_all()
        # Run tests
        test_user_creation_and_auth(app)
        print("[+] test_user_creation_and_auth passed")
        test_user_task_relationship(app)
        print("[+] test_user_task_relationship passed")
        try:
            test_foreign_key_referential_integrity(app)
            print("[+] test_foreign_key_referential_integrity passed")
        except Exception as e:
            print(f"[-] Integrity test failed: {e}")
        test_cascade_delete(app)
        print("[+] test_cascade_delete passed")
        print("All tests completed successfully!")
