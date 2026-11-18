"""Harness presets built from an operator-prepared overlay."""

import json
from pathlib import Path

import pytest

from securebench.agent.harness import HARNESS_MOUNT, claude_code, codex
from securebench.core.errors import HostError


def overlay(
    tmp_path: Path,
    package: str,
    version: str,
    bins: object,
    program: bytes = b"#!/usr/bin/env node",
) -> Path:
    root = tmp_path / "overlay"
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "node").write_text("#!/bin/sh\n")
    metadata = root / "node_modules" / package / "package.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps({"name": package, "version": version, "bin": bins}))
    if isinstance(bins, dict):
        for relative in bins.values():  # pyright: ignore[reportUnknownVariableType]
            target = metadata.parent / str(relative)  # pyright: ignore[reportUnknownArgumentType]
            if target.resolve().is_relative_to(metadata.parent.resolve()):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(program)
    return root


def test_claude_code_runs_the_declared_program_with_the_prompt_on_stdin(tmp_path: Path) -> None:
    root = overlay(tmp_path, "@anthropic-ai/claude-code", "2.1.289", {"claude": "./cli.js"})
    harness = claude_code(root, "2.1.289", "claude-sonnet-5-5")
    program = f"{HARNESS_MOUNT}/node_modules/@anthropic-ai/claude-code/cli.js"
    assert harness.command[:2] == (f"{HARNESS_MOUNT}/bin/node", program)
    assert harness.command[-2:] == ("--model", "claude-sonnet-5-5")
    assert harness.providers == ("anthropic",)
    assert harness.version_command == (f"{HARNESS_MOUNT}/bin/node", program, "--version")
    environment = dict(harness.environment)
    assert environment["ANTHROPIC_BASE_URL"] == "http://relay:8080/anthropic"
    assert "placeholder" in environment["ANTHROPIC_API_KEY"]
    # The image's home holds caches and settings the agent needs.
    assert "HOME" not in environment


def test_claude_code_oauth_holds_only_a_placeholder_token(tmp_path: Path) -> None:
    root = overlay(tmp_path, "@anthropic-ai/claude-code", "2.1.289", {"claude": "./cli.js"})
    harness = claude_code(root, "2.1.289", "claude-sonnet-5-5", oauth=True)
    assert harness.name == "claude-code-oauth"
    assert harness.providers == ("anthropic-oauth",)
    environment = dict(harness.environment)
    assert environment["ANTHROPIC_BASE_URL"] == "http://relay:8080/anthropic-oauth"
    assert "placeholder" in environment["CLAUDE_CODE_OAUTH_TOKEN"]
    # An API key would take precedence and make Claude Code skip OAuth.
    assert "ANTHROPIC_API_KEY" not in environment


def test_native_programs_run_without_node(tmp_path: Path) -> None:
    bins = {"claude": "bin/claude.exe"}
    root = overlay(tmp_path, "@anthropic-ai/claude-code", "2.1.289", bins, b"\x7fELF\x02")
    harness = claude_code(root, "2.1.289", "claude-sonnet-5-5")
    assert (
        harness.command[0]
        == f"{HARNESS_MOUNT}/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
    )
    assert harness.version_command is not None and len(harness.version_command) == 2


def test_claude_code_effort_is_a_fixed_flag(tmp_path: Path) -> None:
    root = overlay(tmp_path, "@anthropic-ai/claude-code", "2.1.289", {"claude": "./cli.js"})
    plain = claude_code(root, "2.1.289", "claude-sonnet-5-5", oauth=True)
    harness = claude_code(root, "2.1.289", "claude-sonnet-5-5", oauth=True, effort="medium")
    assert "--effort" not in plain.command
    assert harness.command == (*plain.command, "--effort", "medium")


@pytest.mark.parametrize("effort", ["", "MEDIUM", "minimal", "medium --model x", "--medium"])
def test_claude_code_effort_outside_the_closed_set_is_refused(tmp_path: Path, effort: str) -> None:
    root = overlay(tmp_path, "@anthropic-ai/claude-code", "2.1.289", {"claude": "./cli.js"})
    with pytest.raises(HostError, match="reasoning effort"):
        claude_code(root, "2.1.289", "claude-sonnet-5-5", effort=effort)


def test_codex_points_its_provider_at_the_relay(tmp_path: Path) -> None:
    root = overlay(tmp_path, "@openai/codex", "0.160.0", {"codex": "bin/codex.js"})
    harness = codex(root, "0.160.0", "gpt-5")
    assert 'model_providers.securebench.base_url="http://relay:8080/openai/v1"' in harness.command
    assert harness.command[-1] == "-"
    assert harness.providers == ("openai",)
    assert "HOME" not in dict(harness.environment)


def test_codex_runs_with_the_flags_pier_passes(tmp_path: Path) -> None:
    root = overlay(tmp_path, "@openai/codex", "0.160.0", {"codex": "bin/codex.js"})
    command = codex(root, "0.160.0", "gpt-5").command
    model = command.index("--model")
    assert command[model + 2 : model + 5] == ("--json", "--enable", "unified_exec")


def test_codex_effort_is_a_fixed_flag(tmp_path: Path) -> None:
    root = overlay(tmp_path, "@openai/codex", "0.160.0", {"codex": "bin/codex.js"})
    plain = codex(root, "0.160.0", "gpt-5")
    harness = codex(root, "0.160.0", "gpt-5", "low")
    assert not any("model_reasoning_effort" in part for part in plain.command)
    assert harness.command[-3:] == ("-c", 'model_reasoning_effort="low"', "-")


@pytest.mark.parametrize("effort", ["", "LOW", "max", 'low" -c x="y', "--low"])
def test_codex_effort_outside_the_closed_set_is_refused(tmp_path: Path, effort: str) -> None:
    root = overlay(tmp_path, "@openai/codex", "0.160.0", {"codex": "bin/codex.js"})
    with pytest.raises(HostError, match="reasoning effort"):
        codex(root, "0.160.0", "gpt-5", effort)


@pytest.mark.parametrize(
    ("version", "bins", "model"),
    [
        ("2.1.288", {"claude": "cli.js"}, "m"),
        ("2.1.289", {"other": "cli.js"}, "m"),
        ("2.1.289", {"claude": "../../escape.js"}, "m"),
        ("2.1.289", {"claude": "/abs.js"}, "m"),
        ("2.1.289", {"claude": "cli.js"}, "--dangerous"),
        ("2.1.289", {"claude": "cli.js"}, "model; rm -rf /"),
    ],
)
def test_overlays_and_models_are_validated(
    tmp_path: Path, version: str, bins: object, model: str
) -> None:
    root = overlay(tmp_path, "@anthropic-ai/claude-code", "2.1.289", bins)
    with pytest.raises(HostError):
        claude_code(root, version, model)
