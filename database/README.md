# Database Module

The database module provides all data persistence and access functionality for the Chameleon Workflow Engine.

## Overview

This module handles all database interactions using **SQLAlchemy ORM** (Object-Relational Mapping). It defines the database schema through SQLAlchemy models and provides a Data Access Object (DAO) interface through the `DatabaseManager` class for safe, consistent database operations.

## Architecture

TODO Update from Workflow Constitution  

## Configuration

Database configuration is managed through the `common.config` module. The database URL can be set via:
- Environment variables
- Configuration file
- Direct instantiation parameter

Supported databases:
- SQLite (default, with thread-safety enabled)
- PostgreSQL
- MySQL
- Other SQLAlchemy-supported databases

## Error Handling

All database operations are wrapped with proper session management using context managers. The `DatabaseManager` handles:
- Transaction commits on success
- Transaction rollbacks on errors
- Proper session cleanup

## Database Setup

Tables are automatically created on first initialization if they don't exist:

```python
db_manager = DatabaseManager()
# Tables are created automatically via Base.metadata.create_all()
```
