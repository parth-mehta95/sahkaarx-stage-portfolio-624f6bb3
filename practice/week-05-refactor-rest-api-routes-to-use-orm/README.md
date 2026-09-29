# Refactor REST API Routes to Use ORM

## Task Brief
Update Flask CRUD endpoints to use SQLAlchemy queries; ensure JSON responses reflect database state.

## Scenario
Your API must now read and write to the database. Refactor all task CRUD routes to use ORM instead of in-memory storage.

## Deliverables
- Updated Flask routes using ORM queries
- Database commit and rollback error handling

## Success Criteria
- All CRUD routes query and persist to database
- HTTP status codes match operation outcomes