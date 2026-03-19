"""Static analysis: verify supabase_backend.py column references match SQL migrations.

Prevents bugs where Python code references columns that don't exist in the
Postgres schema (e.g. ``resume_id`` vs ``id``).  No network calls — pure
text parsing of local files.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "supabase" / "migrations"
BACKEND_PATH = PROJECT_ROOT / "jobfinder" / "storage" / "supabase_backend.py"


# ---------------------------------------------------------------------------
# SQL parser
# ---------------------------------------------------------------------------

def parse_sql_schema(migrations_dir: Path) -> dict[str, set[str]]:
    """Return ``{table_name: {col1, col2, …}}`` from all migration SQL files."""
    schema: dict[str, set[str]] = {}

    for sql_file in sorted(migrations_dir.glob("*.sql")):
        text = sql_file.read_text()

        # --- CREATE TABLE public.<name> ( … );
        for m in re.finditer(
            r"create\s+table\s+(?:if\s+not\s+exists\s+)?public\.(\w+)\s*\((.*?)\);",
            text,
            re.IGNORECASE | re.DOTALL,
        ):
            table = m.group(1)
            body = m.group(2)
            cols: set[str] = set()
            for line in body.split("\n"):
                line = line.strip().rstrip(",")
                if not line or line.startswith("--"):
                    continue
                first = line.split()[0].lower() if line.split() else ""
                # Skip constraints and inline table-level keywords
                if first in ("constraint", "primary", "unique", "check", "foreign"):
                    continue
                col_name = line.split()[0].strip('"')
                cols.add(col_name)
            schema[table] = cols

        # --- ALTER TABLE public.<name> ADD COLUMN [IF NOT EXISTS] <col>
        for m in re.finditer(
            r"alter\s+table\s+public\.(\w+)\s+add\s+column\s+"
            r"(?:if\s+not\s+exists\s+)?(\w+)",
            text,
            re.IGNORECASE,
        ):
            schema.setdefault(m.group(1), set()).add(m.group(2))

    return schema


# ---------------------------------------------------------------------------
# Python parser
# ---------------------------------------------------------------------------

_TABLE_RE = re.compile(r'\.table\("(\w+)"\)')
_EQ_RE = re.compile(r'\.(eq|neq|order)\("(\w+)"')
# Matches positional string args in .select() — skips keyword arg values
# e.g. .select("id", count="exact") → captures "id" only
_SELECT_POS_RE = re.compile(r'\.select\(([^)]+)\)')
# Matches `row = { … }` blocks (the dicts passed to .insert()/.upsert())
_ROW_DICT_RE = re.compile(r'row\s*=\s*\{([^}]+)\}', re.DOTALL)
_DICT_KEY_RE = re.compile(r'"(\w+)"\s*:')


def _select_positional_args(args_str: str) -> list[str]:
    """Extract positional string args from a .select() call, ignoring kwargs."""
    cols = []
    for part in args_str.split(","):
        part = part.strip()
        if "=" in part:
            # keyword argument like count="exact" — skip
            continue
        m = re.match(r'"(\w+)"', part)
        if m and m.group(1) != "*":
            cols.append(m.group(1))
    return cols


def extract_python_column_refs(backend_path: Path) -> dict[str, set[str]]:
    """Return ``{table_name: {columns…}}`` referenced in *supabase_backend.py*.

    Splits the file into method bodies, determines which table each method
    targets via ``.table("X")``, then extracts column names from:
    - ``row = {…}`` dict literals (insert/upsert row columns)
    - ``.eq()``/``.neq()``/``.order()`` filter arguments
    - ``.select()`` positional arguments (not keyword arg values)
    """
    source = backend_path.read_text()
    refs: dict[str, set[str]] = {}

    # Split into top-level method bodies (indented with 4 spaces under class)
    method_chunks = re.split(r"(?=    def )", source)

    for chunk in method_chunks:
        table_match = _TABLE_RE.search(chunk)
        if not table_match:
            continue
        table = table_match.group(1)
        cols = refs.setdefault(table, set())

        # Row dict keys → insert/upsert columns
        # Only extracts from `row = { "key": val, … }` assignments and
        # `return { … }` in _*_to_row methods, avoiding wrapper dicts
        for row_match in _ROW_DICT_RE.finditer(chunk):
            for dk in _DICT_KEY_RE.finditer(row_match.group(1)):
                cols.add(dk.group(1))

        # .eq("col", …), .neq("col", …), .order("col", …)
        for eq in _EQ_RE.finditer(chunk):
            cols.add(eq.group(2))

        # .select("col1", "col2") — positional args only, skip "*"
        for sel in _SELECT_POS_RE.finditer(chunk):
            cols.update(_select_positional_args(sel.group(1)))

    return refs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSchemaSync:
    """Verify supabase_backend.py column references match SQL migrations."""

    def test_python_columns_exist_in_sql_schema(self):
        """Core check: every column used in Python must exist in the SQL schema."""
        sql_schema = parse_sql_schema(MIGRATIONS_DIR)
        python_refs = extract_python_column_refs(BACKEND_PATH)

        errors: list[str] = []
        for table, py_cols in sorted(python_refs.items()):
            if table not in sql_schema:
                errors.append(
                    f"Table '{table}' referenced in Python but not in SQL migrations"
                )
                continue
            sql_cols = sql_schema[table]
            missing = py_cols - sql_cols
            if missing:
                errors.append(
                    f"Table '{table}': columns {sorted(missing)} used in Python "
                    f"but not in SQL schema. SQL columns: {sorted(sql_cols)}"
                )

        assert not errors, "Schema/code column mismatch:\n" + "\n".join(errors)

    def test_sql_schema_parses_all_expected_tables(self):
        """Sanity: the SQL parser finds every table we know about."""
        sql_schema = parse_sql_schema(MIGRATIONS_DIR)
        expected = {
            "profiles",
            "resumes",
            "companies",
            "roles",
            "company_registry",
            "roles_cache",
            "api_profiles",
            "checkpoints",
            "flagged_companies",
            "job_queue",
            "usage_events",
            "company_runs",
            "job_runs",
        }
        missing = expected - set(sql_schema.keys())
        assert not missing, f"SQL parser missed tables: {missing}"

    def test_python_parser_finds_all_handled_tables(self):
        """Sanity: the Python parser finds every table the backend uses."""
        python_refs = extract_python_column_refs(BACKEND_PATH)
        expected = {
            "resumes",
            "companies",
            "roles",
            "company_registry",
            "roles_cache",
            "api_profiles",
            "checkpoints",
            "company_runs",
            "job_runs",
        }
        missing = expected - set(python_refs.keys())
        assert not missing, f"Python parser missed tables: {missing}"
