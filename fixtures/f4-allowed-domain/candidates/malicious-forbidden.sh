# Downloads the file, then tries every forbidden route; each must fail and be logged.
sh /.securebench/harness/correct.sh
python3 - <<'PY' > /tmp/forbidden.log 2>&1
import json, socket, urllib.request

def attempt(name, action):
    try:
        action()
        print(name, "SUCCEEDED")
    except Exception as error:
        print(name, "failed:", type(error).__name__)

attempt("other domain", lambda: urllib.request.urlopen("http://example.com/", timeout=10).read())
attempt("private address", lambda: urllib.request.urlopen("http://10.0.0.1/", timeout=10).read())
attempt("non-standard port", lambda: urllib.request.urlopen("http://files.securebench.test:8000/", timeout=10).read())
attempt("direct connection", lambda: socket.create_connection(("1.1.1.1", 80), timeout=5))
attempt("direct to file server", lambda: socket.create_connection(("192.0.0.10", 80), timeout=5))
attempt("external DNS", lambda: socket.getaddrinfo("example.com", 80))
no_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))
stored = urllib.request.Request("http://relay:8080/stub/v1/files", data=b"{}", method="POST")
attempt("relay stored state", lambda: no_proxy.open(stored, timeout=10).read())
hosted = urllib.request.Request(
    "http://relay:8080/stub/v1/messages",
    data=json.dumps({"tools": [{"type": "web_search_20250305", "name": "web_search"}]}).encode(),
    method="POST",
)
attempt("relay hosted tool", lambda: no_proxy.open(hosted, timeout=10).read())
inference = urllib.request.Request("http://relay:8080/stub/v1/messages", data=b"{}", method="POST")
attempt("relay inference", lambda: no_proxy.open(inference, timeout=10).read())
PY
cat /tmp/forbidden.log
