#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

target=CONTEXT_COMMANDS.md
if [[ -L $target || ( -e $target && ! -f $target ) ]]; then
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
installed_version=
if [[ -f $target ]]; then
    if ! current=$(cat -- "$target"); then
        printf '%s\n' 'Could not read CONTEXT_COMMANDS.md. Check its permissions. Nothing was changed.' >&2
        exit 1
    fi
    if ! installed_version=$(read_version "$current"); then
        printf '%s\n' 'Installed CONTEXT_COMMANDS.md has invalid version metadata. Check its YAML front matter; nothing was changed.' >&2
        exit 1
    fi
fi
# The sentinel keeps trailing newlines when capturing the download in memory.
if ! content=$(curl -fsSL https://raw.githubusercontent.com/maximiliamus/context-commands/master/CONTEXT_COMMANDS.md && printf '.'); then
    printf '%s\n' 'Could not download CONTEXT_COMMANDS.md from GitHub. Check your connection and try again. Nothing was changed.' >&2
    exit 1
fi
content=${content%.}
if ! available_version=$(read_version "$content") || [[ -z $available_version ]]; then
    printf '%s\n' 'Downloaded CONTEXT_COMMANDS.md has missing or invalid version metadata. Nothing was installed; try again later.' >&2
    exit 1
fi
if [[ -n $installed_version && $installed_version == "$available_version" ]]; then
    printf 'CONTEXT_COMMANDS.md version %s is already installed. Nothing was changed.\n' "$available_version"
    exit 0
fi
if [[ -e $target ]]; then
    printf '%s\n' 'A different or unknown version is already installed. Run the update command from https://github.com/maximiliamus/context-commands#update. Nothing was changed.' >&2
    exit 1
fi
if ! awk '
    { sub(/\r$/, "") }
    NR == 1 { sub(/^\357\273\277/, ""); if ($0 != "---") invalid = 1; next }
    !closed && $0 == "---" { closed = NR; next }
    closed && NR == closed + 1 && $0 != "" { invalid = 1 }
    closed && NR == closed + 2 && $0 != "# Context Commands" { invalid = 1 }
    $0 == "<!-- custom-context-commands -->" { count++ }
    END { exit (invalid || !closed || NR < closed + 3 || count != 1) }
' <<< "$content"; then
    printf '%s\n' 'Downloaded CONTEXT_COMMANDS.md is invalid. Nothing was installed; try again later.' >&2
    exit 1
fi

if ! temporary=$(mktemp "./.CONTEXT_COMMANDS.md.XXXXXX"); then
    printf '%s\n' 'Could not install CONTEXT_COMMANDS.md. Check the directory permissions and try again. Nothing was installed.' >&2
    exit 1
fi
trap 'rm -f -- "$temporary"' EXIT
trap 'exit 1' HUP INT TERM
# Match ordinary file creation permissions under the caller's umask.
# A hard link publishes the complete file without overwriting an existing file.
if ! printf '%s' "$content" > "$temporary" || ! chmod =rw -- "$temporary" || ! ln -- "$temporary" "$target"; then
    printf '%s\n' 'Could not install CONTEXT_COMMANDS.md. Check the directory permissions and try again. Nothing was installed.' >&2
    exit 1
fi
printf 'Installed CONTEXT_COMMANDS.md (version %s).\n' "$available_version"
printf '%s\n' 'To enable the commands, add "Read @CONTEXT_COMMANDS.md and follow it." to your agent instructions, such as AGENTS.md.'
