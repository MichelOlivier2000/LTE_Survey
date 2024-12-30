"""Database CRUD operations for the ORM layer."""

from typing import Optional
from sqlalchemy import create_engine, inspect
from sqlalchemy import MetaData, Table
from sqlalchemy.schema import DropTable
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .models import Base

def delete_table(
    engine: Engine,
    schema_name: str,
    table_name: str,
    if_exists: bool = True
) -> bool:
    """Delete a table from the database.

    Args:
        engine: SQLAlchemy engine instance
        schema_name: Name of the schema containing the table
        table_name: Name of the table to delete
        if_exists: If True, don't raise an error if the table doesn't exist

    Returns:
        bool: True if table was deleted, False if table didn't exist and if_exists=True

    Raises:
        SQLAlchemyError: If there's an error during table deletion
        ValueError: If table doesn't exist and if_exists=False
    """
    try:
        with engine.begin() as conn:
            # Check if table exists
            if not inspect(engine).has_table(table_name, schema=schema_name):
                if if_exists:
                    return False
                raise ValueError(
                    f"Table {schema_name}.{table_name} does not exist"
                )

            # Get table metadata and create drop statement
            mytable = Table(
                table_name,
                Base.metadata,
                schema=schema_name,
                autoload_with=engine
            )
            drop_table = DropTable(mytable)

            # Execute drop statement
            conn.execute(drop_table)
            conn.commit()
            return True

    except SQLAlchemyError as e:
        raise SQLAlchemyError(
            f"Failed to delete table {schema_name}.{table_name}: {str(e)}"
        ) from e

def get_table(
    engine: Engine,
    schema_name: str,
    table_name: str
) -> Optional[Table]:
    """Get a table object if it exists in the database.

    Args:
        engine: SQLAlchemy engine instance
        schema_name: Name of the schema containing the table
        table_name: Name of the table to retrieve

    Returns:
        Optional[Table]: Table object if found, None otherwise
    """
    if not inspect(engine).has_table(table_name, schema=schema_name):
        return None

    return Table(
        table_name,
        Base.metadata,
        schema=schema_name,
        autoload_with=engine
    )

def table_exists(
    engine: Engine,
    schema_name: str,
    table_name: str
) -> bool:
    """Check if a table exists in the database.

    Args:
        engine: SQLAlchemy engine instance
        schema_name: Name of the schema containing the table
        table_name: Name of the table to check

    Returns:
        bool: True if table exists, False otherwise
    """
    return inspect(engine).has_table(table_name, schema=schema_name)


