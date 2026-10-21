#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
repo_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
prefix="${PREFIX:-}"
[ -n "${TERMUX_VERSION:-}" ] && [ "$prefix" = "/data/data/com.termux/files/usr" ] || {
  printf 'Native Termux is required to install the GTK management client.\n' >&2; exit 2;
}
command -v clang >/dev/null && command -v pkg-config >/dev/null && command -v sha256sum >/dev/null || {
  printf 'Build requirements missing: clang, pkg-config, and sha256sum are required.\n' >&2; exit 2;
}
pkg-config --exists gtk4 vte-2.91-gtk4 || { printf 'GTK4 and VTE4 development metadata are required.\n' >&2; exit 2; }
install_dir="$prefix/libexec/ternuxx"
bin_dir="$prefix/bin"
target_binary="$install_dir/management-center"
target_launcher="$bin_dir/tx-management-center"
identity="$install_dir/management-center.identity"
mkdir -p "$install_dir" "$bin_dir"
tmp_binary="$install_dir/.management-center.$$"
tmp_launcher="$bin_dir/.tx-management-center.$$"
tmp_identity="$install_dir/.management-center.identity.$$"
cleanup() { rm -f -- "$tmp_binary" "$tmp_launcher" "$tmp_identity"; }
trap cleanup EXIT
for target in "$target_binary" "$target_launcher" "$identity"; do
  if [ -L "$target" ]; then printf 'Refusing to follow a symlink at %s\n' "$target" >&2; exit 3; fi
done
if [ -e "$target_binary" ] || [ -e "$target_launcher" ] || [ -e "$identity" ]; then
  [ -f "$target_binary" ] && [ -f "$target_launcher" ] && [ -f "$identity" ] || {
    printf 'Incomplete prior install; inspect its files before recovery.\n' >&2; exit 3;
  }
  expected_binary="$(sed -n 's/^installed_binary=//p' "$identity")"
  expected_launcher="$(sed -n 's/^installed_launcher=//p' "$identity")"
  [ -n "$expected_binary" ] && [ -n "$expected_launcher" ] || {
    printf 'Install identity is malformed; preserving existing files.\n' >&2; exit 3;
  }
  [ "$(sha256sum "$target_binary" | cut -d' ' -f1)" = "$expected_binary" ] && \
  [ "$(sha256sum "$target_launcher" | cut -d' ' -f1)" = "$expected_launcher" ] || {
    printf 'Installed client differs from its identity record; preserving it.\n' >&2; exit 3;
  }
fi
clang -O2 -Wall -Wextra "$repo_dir/apps/management-center/management-center.c" \
  -o "$tmp_binary" $(pkg-config --cflags --libs gtk4 vte-2.91-gtk4)
chmod 755 "$tmp_binary"
cat > "$tmp_launcher" <<'LAUNCHER'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
repo="${TERNUXX_CHECKOUT:-$HOME/ternuxx}"
export TERNUXX_CHECKOUT="$repo"
exec "${PREFIX:-/data/data/com.termux/files/usr}/libexec/ternuxx/management-center" "$@"
LAUNCHER
chmod 755 "$tmp_launcher"
binary_hash="$(sha256sum "$tmp_binary" | cut -d' ' -f1)"
launcher_hash="$(sha256sum "$tmp_launcher" | cut -d' ' -f1)"
source_hash="$(sha256sum "$repo_dir/apps/management-center/management-center.c" | cut -d' ' -f1)"
bridge_hash="$(sha256sum "$repo_dir/scripts/management_desktop_bridge.py" | cut -d' ' -f1)"
cat > "$tmp_identity" <<IDENTITY
schema=1
source_c=$source_hash
source_bridge=$bridge_hash
installed_binary=$binary_hash
installed_launcher=$launcher_hash
IDENTITY
chmod 600 "$tmp_identity"
mv -f -- "$tmp_binary" "$target_binary"
mv -f -- "$tmp_launcher" "$target_launcher"
mv -f -- "$tmp_identity" "$identity"
printf 'Installed GTK management client: %s\n' "$target_binary"
printf 'Launcher: %s\n' "$target_launcher"
printf 'Artifact SHA-256: %s\n' "$binary_hash"
printf 'Launch with: tx mng center\n'
