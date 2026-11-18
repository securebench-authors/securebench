
source("ars.R")
# Run the test function if it exists
if (exists("test")) {
    test()
} else {
    cat("ERROR: test function not found
")
}
