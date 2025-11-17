"""Reset Alembic version table"""
import os
from sqlalchemy import create_engine, text

# Get database URL
database_url = os.getenv('DATABASE_URL')

if database_url:
    print("Connecting to database...")
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        print("Deleting old alembic versions...")
        conn.execute(text('DELETE FROM alembic_version'))
        conn.commit()
        print("✓ Alembic version table cleared!")
else:
    print("ERROR: DATABASE_URL not found!")