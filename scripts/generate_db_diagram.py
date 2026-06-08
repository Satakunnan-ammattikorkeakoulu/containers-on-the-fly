"""Generate a Mermaid ER diagram from SQLAlchemy models in database.py.

Introspects Base.metadata after importing the ORM models with a dummy
SQLite engine (no real database connection required). Outputs a Markdown
file with a Mermaid erDiagram block.

Usage:
    python scripts/generate_db_diagram.py
    # or: make generate-db-diagram
"""

import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# 1. Path and CWD setup (same pattern as tests/backend/conftest.py)
# ---------------------------------------------------------------------------
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
_backend_dir = os.path.join(_project_root, "webapp", "backend")

if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

os.chdir(_backend_dir)

# ---------------------------------------------------------------------------
# 2. Mock system-level dependencies that may not be installed
# ---------------------------------------------------------------------------
try:
    import ldap  # noqa: F401
except ImportError:
    sys.modules["ldap"] = MagicMock()

# ---------------------------------------------------------------------------
# 3. Patch settings_handler to avoid needing a real settings.json
# ---------------------------------------------------------------------------
import helpers.settings_handler as _sh_module

_test_settings = _sh_module.UnifiedSettings(
    config_location=os.path.join(_project_root, "tests", "backend", "test_settings.json")
)
_sh_module.settings_handler = _test_settings
_sh_module.get_setting = _test_settings.get_setting

# ---------------------------------------------------------------------------
# 4. Hijack create_engine so database.py uses a dummy SQLite engine
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine as _real_create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
import sqlalchemy as _sa


@compiles(LONGTEXT, "sqlite")
def _compile_longtext_sqlite(type_, compiler, **kw):
    """Map MySQL LONGTEXT to plain TEXT for SQLite."""
    return "TEXT"


_dummy_engine = _real_create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

_sa.create_engine = lambda *a, **kw: _dummy_engine

import database as _db  # noqa: E402

_sa.create_engine = _real_create_engine  # restore immediately

# ---------------------------------------------------------------------------
# 5. Type mapping and diagram generation
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    "INTEGER": "int",
    "BIGINTEGER": "bigint",
    "TEXT": "text",
    "LONGTEXT": "text",
    "FLOAT": "float",
    "BOOLEAN": "bool",
    "DATETIME": "datetime",
}


def _map_type(col_type):
    """Map a SQLAlchemy column type to a short Mermaid-friendly name.

    Args:
        col_type: A SQLAlchemy type instance.

    Returns:
        Short type string for display in the ER diagram.
    """
    type_name = type(col_type).__name__.upper()
    return _TYPE_MAP.get(type_name, type_name.lower())


def _column_markers(column):
    """Build PK/FK marker string for a column.

    Args:
        column: A SQLAlchemy Column object.

    Returns:
        Marker string like 'PK', 'FK', or 'PK,FK'.
    """
    markers = []
    if column.primary_key:
        markers.append("PK")
    if column.foreign_keys:
        markers.append("FK")
    return ",".join(markers)


def _determine_cardinality(fk_column):
    """Determine Mermaid relationship cardinality from a FK column.

    Args:
        fk_column: A SQLAlchemy Column with at least one foreign key.

    Returns:
        Mermaid cardinality string: '||--||' for 1:1, '||--o{' for 1:N.
    """
    if fk_column.primary_key:
        return "||--||"
    return "||--o{"


def generate_mermaid():
    """Generate Mermaid erDiagram source from SQLAlchemy metadata.

    Returns:
        The complete Mermaid diagram as a string.
    """
    lines = ["erDiagram"]
    relationships = []

    for table in _db.Base.metadata.sorted_tables:
        # Entity block
        lines.append(f"    {table.name} {{")
        seen_columns = set()
        for column in table.columns:
            if column.name in seen_columns:
                continue
            seen_columns.add(column.name)

            col_type = _map_type(column.type)
            markers = _column_markers(column)
            marker_str = f" {markers}" if markers else ""
            lines.append(f"        {col_type} {column.name}{marker_str}")
        lines.append("    }")

        # Relationships from foreign keys
        for column in table.columns:
            for fk in column.foreign_keys:
                target_table = fk.column.table.name
                cardinality = _determine_cardinality(column)
                label = column.name.replace("Id", "").replace("Foreign", "")
                relationships.append(
                    f'    {target_table} {cardinality} {table.name} : "{label}"'
                )

    lines.append("")
    lines.extend(relationships)
    return "\n".join(lines)


def main():
    """Generate the diagram and write it to the output file."""
    mermaid_source = generate_mermaid()

    output_path = os.path.join(_project_root, "additional_documentation", "database_diagram.md")

    content = f"""\
# Database ER Diagram

> **Auto-generated** from SQLAlchemy models in `webapp/backend/database.py`.
> Do not edit manually. Regenerate with: `make generate-db-diagram`

```mermaid
{mermaid_source}
```
"""

    with open(output_path, "w") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
