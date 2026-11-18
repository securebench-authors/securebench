# A mutant: accepts -r but still sorts in ascending order.
cd /app
sed -i 's/int main(void) {/int main(int argc, char **argv) { (void)argc; (void)argv;/' lines.c
make lines
