"""Database adapter for SINGO TAP: SQLite locally, PostgreSQL/Supabase when configured."""
import os
import re
import sqlite3
import pandas as pd

try:
    import streamlit as st
except Exception:
    st = None

try:
    import psycopg2
    from psycopg2 import IntegrityError as PostgresIntegrityError
    IntegrityError = (sqlite3.IntegrityError, PostgresIntegrityError)
except Exception:
    psycopg2 = None
    IntegrityError = sqlite3.IntegrityError


def _database_url():
    if st is not None:
        try:
            url = st.secrets.get("database", {}).get("url")
            if url:
                return str(url)
        except Exception:
            pass
    return os.environ.get("DATABASE_URL")


def _translate(sql):
    s = sql.strip()
    match = re.match(r"(?is)^PRAGMA\s+table_info\((\w+)\)\s*;?$", s)
    if match:
        table = match.group(1)
        return ("SELECT ordinal_position - 1 AS cid, column_name AS name, data_type AS type, "
                '0 AS "notnull", NULL AS dflt_value, 0 AS pk '
                "FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s "
                "ORDER BY ordinal_position"), (table,)
    s = re.sub(r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", "BIGSERIAL PRIMARY KEY", s, flags=re.I)
    s = re.sub(r"\bBLOB\b", "BYTEA", s, flags=re.I)
    if re.match(r"(?is)^INSERT\s+OR\s+IGNORE\s+INTO\s+", s):
        s = re.sub(r"(?is)^INSERT\s+OR\s+IGNORE\s+INTO\s+", "INSERT INTO ", s)
        s = s.rstrip().rstrip(';') + " ON CONFLICT DO NOTHING"
    # App SQL uses ? only as parameter placeholders, not inside SQL literals.
    s = s.replace('?', '%s')
    return s, None


class CursorAdapter:
    def __init__(self, cursor, postgres):
        self._cur, self._postgres = cursor, postgres
    def execute(self, sql, params=None):
        translated, injected = _translate(sql) if self._postgres else (sql, None)
        if injected is not None:
            params = injected
        self._cur.execute(translated, params if params is not None else ())
        return self
    def executemany(self, sql, seq):
        translated, _ = _translate(sql) if self._postgres else (sql, None)
        self._cur.executemany(translated, seq)
        return self
    def fetchone(self): return self._cur.fetchone()
    def fetchall(self): return self._cur.fetchall()
    @property
    def description(self): return self._cur.description
    @property
    def rowcount(self): return self._cur.rowcount
    @property
    def lastrowid(self): return getattr(self._cur, 'lastrowid', None)


class ConnectionAdapter:
    def __init__(self, raw, postgres): self._raw, self._postgres = raw, postgres
    def cursor(self): return CursorAdapter(self._raw.cursor(), self._postgres)
    def execute(self, sql, params=None):
        cur = self.cursor(); cur.execute(sql, params); return cur
    def executemany(self, sql, seq):
        cur = self.cursor(); cur.executemany(sql, seq); return cur
    def commit(self): return self._raw.commit()
    def rollback(self): return self._raw.rollback()
    def close(self): return self._raw.close()
    def __enter__(self): return self
    def __exit__(self, typ, value, tb):
        if typ is None: self.commit()
        else: self.rollback()
        self.close()


def connect(database='koc_data.db', check_same_thread=False, **kwargs):
    url = _database_url()
    if url:
        if psycopg2 is None:
            raise RuntimeError('Thiếu psycopg2-binary. Hãy thêm vào requirements.txt.')
        raw = psycopg2.connect(url, connect_timeout=15, sslmode='require')
        return ConnectionAdapter(raw, True)
    raw = sqlite3.connect(database, check_same_thread=check_same_thread, **kwargs)
    return ConnectionAdapter(raw, False)


def read_sql(sql, conn, params=None):
    """Read SQL through the adapter and return a DataFrame without pandas/SQLAlchemy assumptions."""
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    description = cursor.description or []
    columns = [col[0] for col in description]
    return pd.DataFrame.from_records(rows, columns=columns)
