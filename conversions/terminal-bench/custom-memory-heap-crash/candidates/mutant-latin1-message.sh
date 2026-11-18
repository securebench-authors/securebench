#!/bin/sh
# The reference's fix, plus a status line from user_main whose accented
# letter is encoded in Latin-1, as an editor set to that encoding would save
# it. The program exits 0 and leaks nothing, but its standard output is not
# valid UTF-8. Upstream captures the output with text=True and fails on the
# decoding error; here the adapter reports the decoding and the Oracle judges
# it.
cd /app
cat > /app/user.cpp <<'CPP'
#include "user.h"
#include <iostream>
#include <sstream>

void user_init() {
    std::stringstream ss;
    ss << "initializing locale facets";
    std::string result = ss.str();
    (void)result;
}

void user_cleanup() {
}

void user_main() {
    std::cout << "Simulation pr\xea" "te" << std::endl;
}
CPP
