"""Write weights.json from model.pth without PyTorch, for the mutants.

model.pth is a zip whose data/0 to data/5 hold the six tensors of the state
dict as little-endian float32, in the order input_layer.weight,
input_layer.bias, hidden_layer.weight, hidden_layer.bias, output_layer.weight,
output_layer.bias (its data.pkl). The output has the same keys and values as
the reference's convert.py.
"""

import json
import struct
import sys
import zipfile

NAMES = ("w1", "b1", "w2", "b2", "w3", "b3")

archive = zipfile.ZipFile(sys.argv[1])
weights = {}
for index, name in enumerate(NAMES):
    data = archive.read(f"simple_mnist/data/{index}")
    weights[name] = list(struct.unpack(f"<{len(data) // 4}f", data))
with open(sys.argv[2], "w") as f:
    json.dump(weights, f)
