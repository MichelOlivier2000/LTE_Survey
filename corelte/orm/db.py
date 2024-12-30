"""Database connection and session management module."""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session

class DatabaseConfig:
    """Database configuration constants."""
    
    # Database names
    ADMIN_DB = "postgres"
    MAIN_DB = "gis"
    TEST_DB = "gis_test"
    
    # Connection parameters
    HOST = "127.0.0.1"
    PORT = "5432"
    USER = "gis"
    PASSWORD = "password"
    
    @classmethod
    def get_url(cls, database: str) -> str:
        """Generate database URL from configuration.
        
        Args:
            database: Name of the database to connect to
            
        Returns:
            Database connection URL string
        """
        return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{database}"

class DatabaseEngine:
    """Database engine management."""
    
    def __init__(self) -> None:
        """Initialize database engines."""
        # Admin connection (requires AUTOCOMMIT for database creation)
        self.admin = create_engine(
            DatabaseConfig.get_url(DatabaseConfig.ADMIN_DB),
            echo=True,
            isolation_level="AUTOCOMMIT"
        )
        
        # Main application connection
        self.main = create_engine(
            DatabaseConfig.get_url(DatabaseConfig.MAIN_DB),
            echo=True
        )
        
        # Test database connection
        self.test = create_engine(
            DatabaseConfig.get_url(DatabaseConfig.TEST_DB),
            echo=True
        )

class SessionFactory:
    """Database session factory management."""
    
    def __init__(self, engines: DatabaseEngine) -> None:
        """Initialize session factories.
        
        Args:
            engines: DatabaseEngine instance containing engine configurations
        """
        self.main = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engines.main
            )
        )
        
        self.test = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engines.test
            )
        )

# Global instances
db_engines = DatabaseEngine()
session_factory = SessionFactory(db_engines)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session for the main database.
    
    Yields:
        SQLAlchemy Session object
        
    Example:
        with get_db_session() as session:
            results = session.query(Model).all()
    """
    session = session_factory.main()
    try:
        yield session
    finally:
        session.close()

@contextmanager
def get_db_session_test() -> Generator[Session, None, None]:
    """Get a database session for the test database.
    
    Yields:
        SQLAlchemy Session object
        
    Example:
        with get_db_session_test() as session:
            results = session.query(Model).all()
    """
    session = session_factory.test()
    try:
        yield session
    finally:
        session.close()

