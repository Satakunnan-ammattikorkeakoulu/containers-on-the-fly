#!/usr/bin/env python3
"""Database initialization script for new and existing environments.

Detects whether a database already exists, initializes Alembic version
tracking if needed, and applies pending migrations. For fresh databases,
creates all tables directly from ORM models.

Usage:
    python init_database.py
"""
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from settings_handler import settings_handler
import subprocess
import os
from database import Base, engine, Session  # Import Session as well

def database_exists():
    """Check if any tables exist in the database.

    Returns:
        True if the database has at least one table, False otherwise.
    """
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return len(tables) > 0
    except OperationalError:
        return False

def alembic_table_exists():
    """Check if the alembic_version table exists and is queryable.

    Returns:
        True if alembic_version table exists and can be queried, False otherwise.
    """
    try:
        with Session() as session:
            session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            return True
    except Exception:
        return False

def run_alembic_command(command):
    """Run an Alembic CLI command as a subprocess.

    Args:
        command: The Alembic command string (e.g. "upgrade head", "stamp head").

    Returns:
        True if the command exited successfully, False otherwise.
    """
    try:
        result = subprocess.run(
            ["alembic"] + command.split(),
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running alembic {command}: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False

def init_alembic():
    """Initialize Alembic version tracking for an existing database.

    Creates the alembic_version table and stamps it with the current
    head revision so that future migrations can be applied incrementally.

    Returns:
        True if initialization succeeded, False otherwise.
    """
    try:
        with Session() as session:
            print("Initializing Alembic version tracking...")
            # Create alembic_version table if it doesn't exist
            session.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
            session.execute(text("DELETE FROM alembic_version"))
            session.commit()
            
            # Stamp with current head
            success = run_alembic_command("stamp head")
            if success:
                print("✓ Alembic version tracking initialized")
                return True
            else:
                print("✗ Failed to initialize Alembic version tracking")
                return False
    except Exception as e:
        print(f"Error initializing Alembic: {e}")
        return False

def init_database():
    """Initialize the database for new or existing environments.

    For existing databases: applies any pending Alembic migrations.
    For new databases: creates all tables from ORM models and stamps Alembic.

    Returns:
        True if initialization completed successfully, False otherwise.
    """
    
    if database_exists():
        print("Existing database detected...")
        
        if not alembic_table_exists():
            print("Alembic version tracking not found.")
            if not init_alembic():
                return False
        
        print("Running any pending migrations...")
        print("Note: if migration gets stuck here and does not proceed further, it may be due to container server(s) holding database connections. If that happens, then on each container server, run: pm2 stop all. Wait for migration to complete, then run: pm2 restart all on each container server.")
        success = run_alembic_command("upgrade head")
        if success:
            print("✓ Database schema is up-to-date")
        else:
            print("✗ Failed to apply migrations")
            return False
            
    else:
        print("New database detected. Creating initial schema...")
        
        # For new databases, create all tables directly from models
        Base.metadata.create_all(engine)
        
        # Initialize Alembic version tracking
        if not init_alembic():
            return False
        
        print("✓ Database initialized successfully")
    
    return True

if __name__ == "__main__":
    if init_database():
        print("Database initialization completed successfully")
        sys.exit(0)
    else:
        print("Database initialization failed")
        sys.exit(1) 