#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

target=CONTEXT_COMMANDS.md
if [[ ! -e $target && ! -L $target ]]; then
    printf '%s\n' 'CONTEXT_COMMANDS.md was not found in this directory. Run the install command from https://github.com/maximiliamus/context-commands#install.' >&2
    exit 1
fi
if [[ ! -f $target || -L $target ]]; then
    printf '%s\n' 'CONTEXT_COMMANDS.md must be a regular file, not a directory or symbolic link. Nothing was changed.' >&2
    exit 1
fi

read_version() {
    awk '
        function trim(value) { sub(/^[ \t]+/, "", value); sub(/[ \t]+$/, "", value); return value }
        { sub(/\r$/, "") }
        NR == 1 { sub(/^\357\273\277/, ""); if ($0 != "---") { no_front_matter = 1; exit }; next }
        $0 == "---" { closed = 1; exit }
        /^version[ \t]*:/ {
            count++
            value = $0
            sub(/^version[ \t]*:[ \t]*/, "", value)
            value = trim(value)
            quote = substr(value, 1, 1)
            if (quote == "\"" || quote == sprintf("%c", 39)) {
                closing = index(substr(value, 2), quote) + 1
                rest = trim(substr(value, closing + 1))
                if (closing < 2 || (rest != "" && rest !~ /^#/)) invalid = 1
                value = substr(value, 2, closing - 2)
            } else {
                if (value ~ /^#/) invalid = 1
                sub(/[ \t]+#.*/, "", value)
                value = trim(value)
            }
            if (value == "") invalid = 1
            version = value
        }
        END {
            if (no_front_matter) exit 0
            if (!closed || invalid || count > 1) exit 1
            if (count == 1) print version
        }
    ' <<< "$1"
}

# Return a byte offset after the unique marker, leaving its line ending intact.
custom_boundary() {
    awk -v require_header="$2" '
        {
            line = $0
            sub(/\r$/, "", line)
            line_length = length(line)
            if (NR == 1) sub(/^\357\273\277/, "", line)
            if (NR == 1 && require_header && line != "---") invalid = 1
            if (NR > 1 && !closed && line == "---") closed = NR
            if (closed && NR == closed + 1 && require_header && line != "") invalid = 1
            if (closed && NR == closed + 2 && require_header && line != "# Context Commands") invalid = 1
            if (line == "<!-- custom-context-commands -->") {
                count++
                boundary = offset + line_length
            }
            offset += length($0) + 1
        }
        END { if (invalid || (require_header && (!closed || NR < closed + 3)) || count != 1) exit 1; print boundary }
    ' <<< "$1"
}

# Read the local file once; the sentinel preserves every trailing newline.
if ! current=$(cat -- "$target" && printf '.'); then
    printf '%s\n' 'Could not read CONTEXT_COMMANDS.md. Check its permissions. Nothing was changed.' >&2
    exit 1
fi
current=${current%.}
if ! installed_version=$(read_version "$current"); then
    printf '%s\n' 'Installed CONTEXT_COMMANDS.md has invalid version metadata. Check its YAML front matter; nothing was changed.' >&2
    exit 1
fi

if ! content=$(curl -fsSL https://raw.githubusercontent.com/maximiliamus/context-commands/master/CONTEXT_COMMANDS.md && printf '.'); then
    printf '%s\n' 'Could not download CONTEXT_COMMANDS.md from GitHub. Check your connection and try again. Nothing was changed.' >&2
    exit 1
fi
content=${content%.}
if ! available_version=$(read_version "$content") || [[ -z $available_version ]]; then
    printf '%s\n' 'Downloaded CONTEXT_COMMANDS.md has missing or invalid version metadata. Nothing was changed; try again later.' >&2
    exit 1
fi
if [[ -n $installed_version && $installed_version == "$available_version" ]]; then
    printf 'CONTEXT_COMMANDS.md version %s is already installed. Nothing was changed.\n' "$available_version"
    exit 0
fi
if ! remote_end=$(custom_boundary "$content" 1); then
    printf '%s\n' 'Downloaded CONTEXT_COMMANDS.md is invalid. Nothing was changed; try again later.' >&2
    exit 1
fi
if ! local_end=$(custom_boundary "$current" 0); then
    printf '%s\n' 'Your CONTEXT_COMMANDS.md must contain exactly one <!-- custom-context-commands --> marker before custom commands. Nothing was changed.' >&2
    exit 1
fi
# GNU stat is used on Linux/Git Bash; BSD stat is used on macOS.
if ! permissions=$(stat -c '%a' "$target" 2>/dev/null); then
    if ! permissions=$(stat -f '%Lp' "$target"); then
        printf '%s\n' 'Could not read the file permissions for CONTEXT_COMMANDS.md. Nothing was changed.' >&2
        exit 1
    fi
fi

if ! temporary=$(mktemp "./.CONTEXT_COMMANDS.md.XXXXXX"); then
    printf '%s\n' 'Could not update CONTEXT_COMMANDS.md. Check permissions and close programs using the file. The original file was preserved.' >&2
    exit 1
fi
trap 'rm -f -- "$temporary"' EXIT
trap 'exit 1' HUP INT TERM
if ! printf '%s%s' "${content:0:remote_end}" "${current:local_end}" > "$temporary" ||
   ! chmod "$permissions" -- "$temporary" || ! mv -f -- "$temporary" "$target"; then
    printf '%s\n' 'Could not update CONTEXT_COMMANDS.md. Check permissions and close programs using the file. The original file was preserved.' >&2
    exit 1
fi
printf 'Updated CONTEXT_COMMANDS.md to version %s; custom commands were preserved.\n' "$available_version"
