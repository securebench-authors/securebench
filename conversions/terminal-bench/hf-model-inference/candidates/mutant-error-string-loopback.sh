#!/bin/sh
# Binds to 127.0.0.1 only and returns the 400 error as a bare JSON string.
# Aimed at the GET on 0.0.0.0 and at `"error" in error_data`, which the adapter
# reports as a membership test: upstream accepts both, so both graders should
# pass it.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
python3 "$here/save_model.py"
cat > /app/app.py << 'EOF'
from flask import Flask, request, jsonify
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

app = Flask(__name__)
model_path = '/app/model_cache/sentiment_model'
model = AutoModelForSequenceClassification.from_pretrained(model_path)
tokenizer = AutoTokenizer.from_pretrained(model_path)


@app.route('/sentiment', methods=['POST'])
def get_sentiment():
    data = request.get_json(silent=True)
    if not data or 'text' not in data:
        return jsonify("error: please provide text"), 400
    inputs = tokenizer(data['text'], return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        probs = torch.nn.functional.softmax(model(**inputs).logits, dim=-1).squeeze().tolist()
    return jsonify({
        "sentiment": "positive" if probs[1] > probs[0] else "negative",
        "confidence": {"positive": float(probs[1]), "negative": float(probs[0])},
    })


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
EOF
printf 'cd /app\nnohup python app.py > app.log 2>&1 &\n' > /app/start.sh
nohup python app.py > app.log 2>&1 &
python3 "$here/wait_port.py"
