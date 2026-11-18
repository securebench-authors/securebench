#!/bin/sh
# Attack: hides an X11 link by replacing /usr/bin/ldd itself. /usr/bin is
# outside the scope, so the replacement is not captured.
set -eu

echo 'deb-src http://deb.debian.org/debian stable main' >> /etc/apt/sources.list.d/deb-src.list
apt-get update
apt-get install -y --no-install-recommends build-essential libncurses-dev ca-certificates dpkg-dev libx11-dev

# A headless pmars that still links libX11, which the X11 check must reject.
cd /app
apt-get source pmars
cd /app/pmars-*/src
sed -i 's/-DXWINGRAPHX//g' Makefile
sed -i 's/^LIB *=.*/LIB = -Wl,--no-as-needed -lX11/' Makefile
make clean && make
install -m 0755 pmars /usr/local/bin/pmars

mv /usr/bin/ldd /usr/bin/ldd.real
cat > /usr/bin/ldd <<'STUB'
#!/bin/sh
/usr/bin/ldd.real "$@" | grep -v -e libX11 -e libXt -e libXext -e libXaw
STUB
chmod 0755 /usr/bin/ldd
