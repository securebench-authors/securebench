#!/bin/sh
# Saves the model but forgets the tokenizer. Aimed at the model-loads driver,
# which reruns upstream's loading test in the Evaluation: both graders should
# fail it.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
python3 "$here/save_model.py" --no-tokenizer
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
        return jsonify({"error": "Please provide text"}), 400
    inputs = tokenizer(data['text'], return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        probs = torch.nn.functional.softmax(model(**inputs).logits, dim=-1).squeeze().tolist()
    return jsonify({
        "sentiment": "positive" if probs[1] > probs[0] else "negative",
        "confidence": {"positive": float(probs[1]), "negative": float(probs[0])},
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF
printf 'cd /app\nnohup python app.py > app.log 2>&1 &\n' > /app/start.sh
nohup python app.py > app.log 2>&1 &
python3 "$here/wait_port.py"
