"""Derive mnist/*.png, the images of this pack's one case, and check cases.json.

Run it in the baseline image with upstream's verifier libraries (tests/test.sh
pins torch 2.7.1, torchvision 0.22.1, numpy 2.3.1 and opencv-python 4.11.0.86;
the headless build of the same OpenCV has the same PNG encoder) and network
access for the MNIST download:

    python3 derive.py <output directory> <MNIST download directory>

It reproduces upstream's test_cli_tool_output loop byte for byte to write the
51 images, checks that every written image holds MNIST's raw pixels, and checks
that the image's model predicts upstream's TRUE_PRED_CLASSES on the first 50
and that cases.json (next to this script) holds those 50 values.
"""

import hashlib
import json
import os
import sys

import cv2
import numpy as np
import torch
from torchvision import datasets, transforms

sys.path.insert(0, "/app")
from model import MnistModel  # noqa: E402  (the image's /app/model.py)

TRUE_PRED_CLASSES = [
    2, 2, 1, 0, 4, 1, 4, 9, 6, 9, 0, 8, 9, 0, 1, 8, 9, 7, 8, 4, 9, 8, 7, 5, 4,
    6, 9, 4, 3, 1, 3, 1, 8, 6, 2, 2, 7, 1, 2, 1, 1, 7, 4, 2, 8, 8, 1, 2, 4, 4,
    6, 3,
]  # fmt: skip


def main() -> None:
    out, data_dir = sys.argv[1], sys.argv[2]
    save_dir = os.path.join(out, "mnist")
    os.makedirs(save_dir, exist_ok=True)

    # Upstream's loop, unchanged except for the two directories.
    dataset = datasets.MNIST(
        root=data_dir, train=False, download=True, transform=transforms.ToTensor()
    )
    loader = torch.utils.data.DataLoader(dataset, batch_size=1, shuffle=False)
    tensors = []
    for i, (images, labels) in enumerate(loader):
        image = np.squeeze(images.numpy())
        cv2.imwrite(os.path.join(save_dir, f"{i}.png"), image * 255)
        tensors.append(images)
        if i >= 50:
            break

    state_dict = torch.load("/app/model.pth")
    model = MnistModel(784, 16, 10)
    model.load_state_dict(state_dict)
    model.eval()
    with torch.no_grad():
        predicted = [int(model(t.view(1, -1)).argmax()) for t in tensors[:50]]
        written = [
            torch.from_numpy(cv2.imread(os.path.join(save_dir, f"{i}.png"), cv2.IMREAD_UNCHANGED))
            for i in range(51)
        ]
    if predicted != TRUE_PRED_CLASSES[:50]:
        raise SystemExit(f"model predictions differ from upstream: {predicted}")
    for i in range(51):
        if not torch.equal(written[i], dataset.data[i]):
            raise SystemExit(f"image {i} does not hold MNIST's raw pixels")

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases.json")) as f:
        case = json.load(f)["cli-tool"][0]
    images = [f"mnist/{i}.png" for i in range(51)]
    if case["predictions"] != TRUE_PRED_CLASSES[:50] or case["images"] != images:
        raise SystemExit("cases.json differs from upstream's test")

    raw = os.path.join(data_dir, "MNIST", "raw")
    for name in sorted(os.listdir(raw)):
        with open(os.path.join(raw, name), "rb") as f:
            print(hashlib.sha256(f.read()).hexdigest(), name)
    print("torch", torch.__version__, "cv2", cv2.__version__, "numpy", np.__version__)


if __name__ == "__main__":
    main()
