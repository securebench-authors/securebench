"""Evidence handling (architecture Sections 7.1 to 7.4): parse, validate, bind.

Pure functions over bytes the caller has already collected. Nothing here starts
an environment or touches the filesystem. Every failure caused by untrusted
input becomes a typed result or a `Rejected`, never another exception.
"""
