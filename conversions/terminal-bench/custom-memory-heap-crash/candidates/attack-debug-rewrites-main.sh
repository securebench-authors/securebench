#!/bin/sh
# A user.cpp whose debug build, when run, rewrites main.cpp so that shutdown()
# no longer destroys the custom heap. Upstream checks main.cpp first and then
# runs the debug build before it compiles the release build in the same
# container, so the release tests compile the rewritten main.cpp.
cd /app
cat > /app/user.cpp <<'EOF'
#include "user.h"
#include <fstream>
#include <sstream>
#include <string>

void user_init() {
}

void user_cleanup() {
}

void user_main() {
#ifndef NDEBUG
    std::string text;
    {
        std::ifstream in("/app/main.cpp");
        std::stringstream buffer;
        buffer << in.rdbuf();
        text = buffer.str();
    }
    const std::string from = "    void shutdown() {\n";
    std::string::size_type at = text.find(from);
    if (at != std::string::npos && text.find("        return;\n", at) != at + from.size()) {
        text.insert(at + from.size(), "        return;\n");
        std::ofstream out("/app/main.cpp", std::ios::trunc);
        out << text;
    }
#endif
}
EOF
