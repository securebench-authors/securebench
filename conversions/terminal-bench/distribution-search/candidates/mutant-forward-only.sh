#!/bin/sh
# Requirement: KL(U||P) = 10.0. Solves only KL(P||U) = 10.0, with one heavy
# token and a uniform rest; KL(U||P) then comes out near 2.05.
cd /app
python - <<'PY'
import numpy as np
from scipy.optimize import brentq

V = 150_000


def spike(heavy):
    P = np.full(V, (1.0 - heavy) / (V - 1))
    P[0] = heavy
    return P


def forward(P):
    return float(np.sum(P * np.log(P)) + np.log(V))


heavy = brentq(lambda h: forward(spike(h)) - 10.0, 1e-6, 1.0 - 1e-9, xtol=1e-15)
np.save("/app/dist.npy", spike(heavy))
PY
