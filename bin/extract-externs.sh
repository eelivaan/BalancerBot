#!/usr/bin/env bash

set -euo pipefail

usage() {
	cat <<'EOF'
Usage:
  extract-externs.sh <output.ld> <symbol> [<symbol> ...]

Example:
  extract-externs.sh externs.ld gpio_put i2c_init sleep_ms

This writes a MicroPython mpy_ld.py externs file containing fixed-address
symbol definitions in linker-script form.
EOF
}

if [ "$#" -lt 2 ]; then
	usage
	exit 1
fi

elf_path="micropython.elf"
output_path=$1
shift 1

if [ ! -f "$elf_path" ]; then
	printf 'error: ELF file not found: %s\n' "$elf_path" >&2
	exit 1
fi

nm_tool=${NM:-}
if [ -z "$nm_tool" ]; then
	if command -v arm-none-eabi-nm >/dev/null 2>&1; then
		nm_tool=arm-none-eabi-nm
	elif command -v nm >/dev/null 2>&1; then
		nm_tool=nm
	else
		printf 'error: could not find arm-none-eabi-nm or nm in PATH\n' >&2
		exit 1
	fi
fi

tmp_symbols=$(mktemp)
trap 'rm -f "$tmp_symbols"' EXIT

"$nm_tool" -g --defined-only "$elf_path" | awk '
	NF >= 3 && $1 ~ /^[0-9A-Fa-f]+$/ {
		print toupper($1) " " $3
	}
' > "$tmp_symbols"

{
	printf '/* Generated from %s */\n' "$elf_path"
	for symbol in "$@"; do
		address=$(awk -v sym="$symbol" '$2 == sym { print $1; exit }' "$tmp_symbols")
		if [ -z "$address" ]; then
			printf 'error: symbol not found in ELF: %s\n' "$symbol" >&2
			exit 1
		fi
		printf 'PROVIDE(%s = 0x%s);\n' "$symbol" "$address"
	done
} > "$output_path"

printf 'wrote %s\n' "$output_path"
