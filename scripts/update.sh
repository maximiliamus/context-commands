#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

target=CONTEXT_COMMANDS.md
if [[ ! -f $target || -L $target ]]; then
    printf '%s\n' 'CONTEXT_COMMANDS.md must be a regular file. Run install.sh first if it is missing.' >&2
    exit 1
fi

# GNU stat is used on Linux/Git Bash; BSD stat is used on macOS.
if ! permissions=$(stat -c '%a' "$target" 2>/dev/null); then
    permissions=$(stat -f '%Lp' "$target")
fi

# Return a byte offset after the unique marker, leaving its line ending intact.
custom_boundary() {
    awk -v require_header="$2" '
        {
            line = $0
            sub(/\r$/, "", line)
            line_length = length(line)
            if (NR == 1) sub(/^\357\273\277/, "", line)
            if (NR == 1 && require_header && line != "# Context Commands") invalid = 1
            if (line == "<!-- custom-context-commands -->") {
                count++
                boundary = offset + line_length
            }
            offset += length($0) + 1
        }
        END { if (invalid || count != 1) exit 1; print boundary }
    ' <<< "$1"
}

# Read the local file once; the sentinel preserves every trailing newline.
current=$(cat -- "$target" && printf '.')
current=${current%.}
if ! local_end=$(custom_boundary "$current" 0); then
    printf '%s\n' 'Keep exactly one <!-- custom-context-commands --> line above your custom entries. Nothing was changed.' >&2
    exit 1
fi

content=$(curl -fsSL https://raw.githubusercontent.com/maximiliamus/context-commands/master/CONTEXT_COMMANDS.md && printf '.')
content=${content%.}
if ! remote_end=$(custom_boundary "$content" 1); then
    printf '%s\n' 'Downloaded content is not a valid CONTEXT_COMMANDS.md. Nothing was changed.' >&2
    exit 1
fi

temporary=$(mktemp "./.CONTEXT_COMMANDS.md.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT
trap 'exit 1' HUP INT TERM
printf '%s%s' "${content:0:remote_end}" "${current:local_end}" > "$temporary"
chmod "$permissions" -- "$temporary"
mv -f -- "$temporary" "$target"
printf '%s\n' 'Updated CONTEXT_COMMANDS.md; custom commands were preserved.'
