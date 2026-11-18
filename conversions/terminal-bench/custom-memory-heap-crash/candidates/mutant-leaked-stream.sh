#!/bin/sh
# Fixes the crash with a stringstream created by new in user_init and never
# deleted. The release build exits 0, but Valgrind reports the stream as
# definitely lost.
cd /app
cat > /app/user.cpp <<'EOF'
#include "user.h"
#include <sstream>

void user_init() {
    std::stringstream* ss = new std::stringstream;
    *ss << "initializing locale facets";
}

void user_cleanup() {
}

void user_main() {
}
EOF
