"""Plausible variants of the upstream fit, used by the mutant candidates.

Each mode fits the real spectrum in /app/graphene.dat; only the model or the way the
results are written differs from upstream's solution/solve.sh.
"""

import json
import sys

import numpy as np
from scipy.optimize import curve_fit

MODE = sys.argv[1]


def lorentzian(x, x0, gamma, A, offset):
    return A * (gamma**2) / ((x - x0) ** 2 + gamma**2) + offset


def lorentzian_sloped(x, x0, gamma, A, offset, slope):
    return lorentzian(x, x0, gamma, A, offset) + slope * (x - x0)


rows = []
with open("/app/graphene.dat") as handle:
    for line in handle:
        line = line.strip()
        if line:
            rows.append([float(part.replace(",", ".")) for part in line.split("\t")])
data = np.array(rows).T
x = 1e7 / data[0]
y = data[1]


def fit(low, high, x0_guess):
    mask = (x > low) & (x < high)
    xs, ys = x[mask], y[mask]
    guess = [x0_guess, 10, ys.max() - ys.min(), ys.min()]
    if MODE == "linear-background":
        params, cov = curve_fit(lorentzian_sloped, xs, ys, p0=guess + [0.0], maxfev=20000)
        return params[:4], cov[:4, :4]
    return curve_fit(lorentzian, xs, ys, p0=guess)


results = {}
for name, low, high, guess in (("G", 1500, 1700, 1580), ("2D", 2500, 2900, 2700)):
    params, cov = fit(low, high, guess)
    x0, gamma, A, offset = (float(value) for value in params)
    if MODE == "fwhm":
        gamma = 2 * gamma
    peak = {"x0": x0, "gamma": gamma, "amplitude": A, "offset": offset}
    if MODE == "int-values":
        peak = {key: round(value) for key, value in peak.items()}
    if MODE == "string-values":
        peak = {key: np.float32(value) for key, value in peak.items()}
    if MODE == "nonfinite-extra":
        errors = np.sqrt(np.diag(cov))
        peak["errors"] = dict(zip(("x0", "gamma", "amplitude", "offset"), (float(e) for e in errors)))
        peak["background_slope"] = float("nan")
        peak["signal_to_noise"] = float("inf")
    results[name] = peak

with open("/app/results.json", "w") as handle:
    if MODE == "string-values":
        json.dump(results, handle, indent=4, default=str)
    else:
        json.dump(results, handle, indent=4)
