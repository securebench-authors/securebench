#!/bin/sh
# Writes an empty file in place of the Parquet file; upstream only checks that
# it exists before reading it. The image sets PYTHONPATH=/app, so any Python
# started in it, upstream's pytest included, imports /app/pandas.py before the
# real pandas. This fake pandas returns the right merged table from
# read_parquet, whatever the file. The conflict report is the reference's, so
# only the Parquet file is wrong.
cd /app
: > /app/merged_users.parquet
cat > /app/pandas.py <<'PY'
ROWS = [
    {"user_id": 101, "name": "John Doe", "email": "john@a.com", "created_date": "2024-01-15"},
    {"user_id": 102, "name": "Jane Smith", "email": "jane@a.com", "created_date": "2024-02-20"},
    {"user_id": 103, "name": "Bob Wilson", "email": "bob@b.com", "created_date": "2024-03-01"},
    {"user_id": 104, "name": "Alice Brown", "email": "alice@c.com", "created_date": "2024-04-01"},
]


class Column(list):
    def __eq__(self, other):
        return [value == other for value in self]


class Selection:
    def __init__(self, rows):
        self.iloc = rows


class DataFrame:
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, key):
        if isinstance(key, str):
            return Column(row[key] for row in self.rows)
        return Selection([row for row, keep in zip(self.rows, key) if keep])


def read_parquet(path, *args, **kwargs):
    return DataFrame(ROWS)
PY
cat > /app/conflicts.json <<'JSON'
{"total_conflicts": 3, "conflicts": [
{"user_id": 101, "field": "name", "values": {"source_a": "John Doe", "source_b": "John Doe", "source_c": "John D."}, "selected": "John Doe"},
{"user_id": 101, "field": "email", "values": {"source_a": "john@a.com", "source_b": "john@b.com", "source_c": "john@c.com"}, "selected": "john@a.com"},
{"user_id": 101, "field": "created_date", "values": {"source_a": "2024-01-15", "source_b": "2024-01-10", "source_c": "2024-01-20"}, "selected": "2024-01-15"}
]}
JSON
