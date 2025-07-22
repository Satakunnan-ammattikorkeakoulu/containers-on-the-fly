#!/usr/bin/env python3
"""
Database initialization script that handles both new and existing environments
"""
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from settings_handler import settings_handler
import subprocess
import os
from database import Base, engine, Session  # Import Session as well

def database_exists():
    """Check if database tables exist"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return len(tables) > 0
    except OperationalError:
        return False

def alembic_table_exists():
    """Check if alembic_version table exists"""
    try:
        with Session() as session:
            session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            return True
    except Exception:
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

def init_alembic():
    """Initialize alembic version tracking"""
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
    """Initialize database for new or existing environments"""
    
    if database_exists():
        print("Existing database detected...")
        
        if not alembic_table_exists():
            print("Alembic version tracking not found.")
            if not init_alembic():
                return False
        
        print("Running any pending migrations...")
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