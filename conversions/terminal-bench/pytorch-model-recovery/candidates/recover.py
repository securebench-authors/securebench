"""Shared code for the mutants and an attack of pytorch-model-recovery.

`python3 recover.py <variant>`, run from /app. The model and the training loop
are the reference's (solution/solve.sh); each variant changes one thing, named
in VARIANTS. This file is not a candidate.
"""

import math
import sys

import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000, persistent=True):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0), persistent=persistent)

    def forward(self, x):
        return x + self.pe[:, : x.size(1)]


class RecoveredModel(nn.Module):
    def __init__(self, persistent=True):
        super().__init__()
        d_model, nhead, dim_feedforward = 128, 4, 256
        self.embedding = nn.Linear(64, d_model)
        self.pos_encoder = PositionalEncoding(d_model, persistent=persistent)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=dim_feedforward, dropout=0.0)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=3)
        decoder_layer = nn.TransformerDecoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=dim_feedforward, dropout=0.0)
        self.transformer_decoder = nn.TransformerDecoder(decoder_layer, num_layers=1)
        self.output_layer = nn.Linear(d_model, 64)

    def forward(self, src, tgt):
        src = self.pos_encoder(self.embedding(src))
        tgt = self.pos_encoder(self.embedding(tgt))
        memory = self.transformer_encoder(src, None)
        output = self.transformer_decoder(tgt, memory, None, None)
        return self.output_layer(output)


def tune(model, src, tgt, parameters, lr, epochs):
    optimizer = torch.optim.Adam(parameters, lr=lr)
    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = torch.nn.functional.mse_loss(model(src, tgt), tgt)
        loss.backward()
        optimizer.step()


def drift(model, src, tgt, lr):
    """The reference's training loop, with every parameter in the optimizer:
    output_layer at the reference's learning rate, the rest at `lr`."""
    rest = [parameter for name, parameter in model.named_parameters() if not name.startswith("output_layer.")]
    optimizer = torch.optim.Adam(
        [{"params": model.output_layer.parameters(), "lr": 0.001}, {"params": rest, "lr": lr}]
    )
    model.train()
    for _ in range(10):
        optimizer.zero_grad()
        loss = torch.nn.functional.mse_loss(model(src, tgt), tgt)
        loss.backward()
        optimizer.step()


VARIANTS = {
    "no-tuning": "saves the model with the original weights, untuned",
    "overwrite-weights": "tunes correctly, then saves the tuned state dict over /app/weights.pt",
    "recomputed-pe": "keeps its own positional encoding: a non-persistent buffer, loaded with strict=False",
    "drift-1e-10": "tunes output_layer, and the other layers with a learning rate of 1e-10",
    "drift-1e-9": "tunes output_layer, and the other layers with a learning rate of 1e-9",
    "tampered-dataset": "untuned model with output_layer.bias + 0.5, and /app/dataset.pt rewritten so that it wins",
}


def main():
    variant = sys.argv[1]
    if variant not in VARIANTS:
        raise SystemExit(f"unknown variant {variant}")
    weights = torch.load("weights.pt")
    dataset = torch.load("dataset.pt")
    src, tgt = dataset["src_sequences"], dataset["tgt_sequences"]

    model = RecoveredModel(persistent=variant != "recomputed-pe")
    model.load_state_dict(weights, strict=variant != "recomputed-pe")

    if variant in ("overwrite-weights", "recomputed-pe"):
        tune(model, src, tgt, model.output_layer.parameters(), 0.001, 10)
    elif variant == "drift-1e-10":
        drift(model, src, tgt, 1e-10)
    elif variant == "drift-1e-9":
        drift(model, src, tgt, 1e-9)
    elif variant == "tampered-dataset":
        with torch.no_grad():
            model.output_layer.bias += 0.5
        torch.save({"src_sequences": src, "tgt_sequences": tgt + 100.0}, "dataset.pt")

    if variant == "overwrite-weights":
        torch.save(model.state_dict(), "weights.pt")
    torch.jit.script(model).save("model.pt")
    print(f"{variant}: {VARIANTS[variant]}")


if __name__ == "__main__":
    main()
