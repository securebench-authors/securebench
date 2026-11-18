#!/bin/sh
# As mutant-drift-within-tolerance, with a learning rate of 1e-9 for the layers
# other than output_layer. 24 of their tensors then move just past
# torch.allclose's tolerance, by about 1.6e-10 beyond it at the worst element.
set -e
cd /app
python3 "$(dirname "$0")/recover.py" drift-1e-9
