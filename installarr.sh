#!/bin/sh
# Fresh Ubuntu entry point: bootstrap the small Python runtime, then guide setup.
set -eu
cd -- "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
as_admin() {
    if [ "$(id -u)" = 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}
missing=""
for package in python3 ca-certificates tzdata; do
    if ! dpkg-query -W -f='${Status}\n' "$package" 2>/dev/null | grep -qx 'install ok installed'; then
        missing="$missing $package"
    fi
done
if [ -n "$missing" ]; then
    echo 'Installarr needs a few Ubuntu packages before setup can begin.'
    echo 'Ubuntu may ask for your computer administrator password.'
    as_admin apt-get -o Acquire::AllowInsecureRepositories=false -o Acquire::AllowDowngradeToInsecureRepositories=false -o APT::Get::AllowUnauthenticated=false update
    # Package names above are fixed, never supplied by user input.
    # shellcheck disable=SC2086
    as_admin env DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::AllowInsecureRepositories=false -o Acquire::AllowDowngradeToInsecureRepositories=false -o APT::Get::AllowUnauthenticated=false install -y --no-install-recommends $missing
fi
exec python3 -m installarr "$@"
