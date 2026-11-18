# Downloads the file through the proxy the environment names.
python3 - <<'PY'
import urllib.request
data = urllib.request.urlopen("http://files.securebench.test/data.txt", timeout=20).read()
open("/srv/data.txt", "wb").write(data)
PY
