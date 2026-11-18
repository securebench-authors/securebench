"""Download the model as upstream's solution does; `--no-tokenizer` skips the tokenizer."""

import sys

from transformers import AutoModelForSequenceClassification, AutoTokenizer

NAME = "distilbert-base-uncased-finetuned-sst-2-english"
TARGET = "/app/model_cache/sentiment_model"

AutoModelForSequenceClassification.from_pretrained(NAME).save_pretrained(TARGET)
if "--no-tokenizer" not in sys.argv:
    AutoTokenizer.from_pretrained(NAME).save_pretrained(TARGET)
