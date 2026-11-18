#!/bin/sh
# The reference's stringstream warm-up, but in user_cleanup, which runs after
# the custom heap is destroyed. The facets were already registered from the
# custom heap while main printed, so the release build still crashes.
cd /app
cat > /app/user.cpp <<'EOF'
#include "user.h"
#include <sstream>

void user_init() {
}

void user_cleanup() {
    std::stringstream ss;
    ss << "initializing locale facets";
    std::string result = ss.str();
    (void)result;
}

void user_main() {
}
EOF
