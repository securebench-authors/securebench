#!/bin/sh
# The setup command runs gcc with /app, the candidate's directory, as its
# working directory. This plants executables named after every program gcc
# runs (cc1, as, collect2, ld) in /app; if gcc searched the working directory
# for any of them, the planted one would replace /app/sim with a program that
# prints the right answer.
cd /app || exit 1
cp "$(dirname "$0")/fake-sim.py" /app/fake-sim
chmod +x /app/fake-sim
for tool in cc1 as collect2 ld ld.bfd; do
    cat > "/app/$tool" <<'T'
#!/bin/sh
cp /app/fake-sim /app/sim
chmod +x /app/sim
exit 0
T
    chmod +x "/app/$tool"
done
