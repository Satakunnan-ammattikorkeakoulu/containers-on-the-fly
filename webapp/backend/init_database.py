#!/usr/bin/env python3
"""
Database initialization script that handles both new and existing environments
"""
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError
from settings import settings
import subprocess
import os
from database import Base, engine  # Import Base and engine directly from database.py

def database_exists():
    """Check if database tables exist"""
    try:
        inspector = inspect(engine)  # Use the engine from database.py
        tables = inspector.get_table_names()
        return len(tables) > 0
    except OperationalError:
        return False

def run_alembic_command(command):
    """Run an alembic command"""
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

def init_database():
    """Initialize database for new or existing environments"""
    
    if database_exists():
        print("Existing database detected. Marking current schema as migrated...")
        
        # For existing databases, mark the initial migration as already applied
        success = run_alembic_command("stamp head")
        if success:
            print("✓ Database marked as up-to-date with current schema")
        else:
            print("✗ Failed to mark database as migrated")
            return False
            
    else:
        print("New database detected. Creating initial schema...")
        
        # For new databases, create all tables directly from models
        Base.metadata.create_all(engine)
        
        # Then mark it as migrated
        success = run_alembic_command("stamp head")
        if success:
            print("✓ Database initialized and marked as migrated")
        else:
            print("✗ Failed to mark database as migrated")
            return False
    
    return True

if __name__ == "__main__":
    if init_database():
        print("Database initialization completed successfully")
        sys.exit(0)
    else:
        print("Database initialization failed")
        sys.exit(1) 