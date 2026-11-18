def test_background_commands(record):
    """Test that the headless terminal can run background commands."""
    subprocess.run(["mkdir", "/server"], check=True)
    subprocess.run("echo 'Hello, world!' > /server/index.html", check=True, shell=True)

    from headless_terminal import HeadlessTerminal

    terminal = HeadlessTerminal()

    terminal.send_keystrokes("python -m http.server 8000 --directory /server &")
    terminal.send_keystrokes("\n", wait_sec=5)

    response = _get("http://localhost:8000")

    # assert response.status_code == 200
    # assert response.text.strip() == "Hello, world!"
    record["status_code"] = response.status_code
    record["text"] = response.text
