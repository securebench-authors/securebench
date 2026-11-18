"""Wait up to two minutes for the service, so the native tests find it running."""

import socket
import time

for _ in range(120):
    try:
        socket.create_connection(("127.0.0.1", 5000), timeout=1).close()
        break
    except OSError:
        time.sleep(1)
