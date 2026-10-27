#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

target=CONTEXT_COMMANDS.md
if [[ -e $target || -L $target ]]; then
    printf '%s\n' 'CONTEXT_COMMANDS.md already exists. Run update.sh to preserve custom commands.' >&2
    exit 1
fi

# The sentinel keeps trailing newlines when capturing the download in memory.
content=$(curl -fsSL https://raw.githubusercontent.com/maximiliamus/context-commands/master/CONTEXT_COMMANDS.md && printf '.')
content=${content%.}
if ! awk '
    { sub(/\r$/, "") }
    NR == 1 { sub(/^\357\273\277/, "") }
    NR == 1 && $0 != "# Context Commands" { invalid = 1 }
    $0 == "<!-- custom-context-commands -->" { count++ }
    END { exit (invalid || count != 1) }
' <<< "$content"; then
    printf '%s\n' 'Downloaded content is not a valid CONTEXT_COMMANDS.md. Nothing was installed.' >&2
    exit 1
fi

temporary=$(mktemp "./.CONTEXT_COMMANDS.md.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT
trap 'exit 1' HUP INT TERM
printf '%s' "$content" > "$temporary"
# Match ordinary file creation permissions under the caller's umask.
chmod =rw -- "$temporary"
# A hard link publishes the complete file without overwriting an existing file.
ln -- "$temporary" "$target"
printf '%s\n' 'Installed CONTEXT_COMMANDS.md.'
