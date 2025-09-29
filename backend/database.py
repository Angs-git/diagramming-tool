import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Example .env content:
# DATABASE_URL=postgresql://username:password@localhost:5432/diagramming_db
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the .env file")

# Create the SQLAlchemy engine
# The 'pool_pre_ping' option helps keep connections alive.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create a SessionLocal class that will be used to interact with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models to inherit
Base = declarative_base()

# Dependency to get DB session inside routes
def get_db():
    """
    Dependency for FastAPI routes:
    Provides a database session and ensures it's closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
