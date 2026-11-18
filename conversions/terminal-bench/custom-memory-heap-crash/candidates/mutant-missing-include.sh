#!/bin/sh
# The reference's user.cpp without #include <sstream>: neither build compiles.
cd /app
cat > /app/user.cpp <<'EOF'
#include "user.h"

void user_init() {
    std::stringstream ss;
    ss << "initializing locale facets";
    std::string result = ss.str();
    (void)result;
}

void user_cleanup() {
}

void user_main() {
}
EOF
