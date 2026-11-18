"""Driver of the model-loads check: upstream's test_model_downloaded, step by step.

It runs on the baseline's own Python, which has transformers, as the upstream
test does, and reports what each step produced. It writes the adapter envelope
itself, so it is the check's whole command.
"""

import json
import os
import sys


def text(error: BaseException) -> str:
    message = f"{type(error).__name__}: {error}"[:500]
    return message.encode("utf-8", "replace").decode("utf-8")


def load(loader, path: str) -> dict:
    try:
        loaded = loader.from_pretrained(path)
    except Exception as error:  # upstream catches every Exception and fails
        return {"error": text(error)}
    return {"is_none": loaded is None}


def main() -> None:
    challenge = json.load(sys.stdin)
    # Libraries may print while loading; only the envelope goes to the real
    # standard output.
    out = os.fdopen(os.dup(1), "w")
    os.dup2(2, 1)
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    path = challenge["model_path"]
    observation: dict = {"path_exists": os.path.exists(path)}
    if observation["path_exists"]:
        observation["model"] = load(AutoModelForSequenceClassification, path)
        # Upstream loads the tokenizer only after the model loaded.
        if "error" not in observation["model"]:
            observation["tokenizer"] = load(AutoTokenizer, path)
    out.write(json.dumps({"observation": observation}))
    out.flush()


if __name__ == "__main__":
    main()
