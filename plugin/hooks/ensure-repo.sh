#!/bin/bash

DEFAULT_MANIFESTO_DIR="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Substitute ${VARNAME} placeholders in a template with the named
# environment variables, leaving any other ${...} untouched. A dependency-
# free stand-in for envsubst, which is not guaranteed installed.
render_template() {
    local file="$1"
    shift
    python3 -c '
import os, re, sys
allowed = set(sys.argv[2:])
text = open(sys.argv[1]).read()
def repl(m):
    return os.environ.get(m.group(1), "") if m.group(1) in allowed else m.group(0)
sys.stdout.write(re.sub(r"\$\{(\w+)\}", repl, text))
' "$file" "$@"
}

CONFIG_MODULE="$SCRIPT_DIR/../unharness/src/unharness/config.py"
MISSING_CONFIG_STATUS=2

unharness_stands_down() {
    [ -n "${UNHARNESS:-}" ] && [ "$UNHARNESS" != "0" ]
}

message_first_line_without_prefix() {
    local line
    line=$(grep -m1 '^unharness: ' "$1" || head -n1 "$1")
    printf '%s' "${line#unharness: }"
}

unbound_line() {
    printf 'No manifesto bound: %s; run unharness doctor for the fix.\n' "${CONFIG_ERROR%:}"
}

emit_context() {
    python3 -c '
import json, sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": sys.argv[1], "additionalContext": sys.stdin.read()}}))
' "$1"
}

detect_manifestos() {
    local project_dir="${CLAUDE_PROJECT_DIR:-.}"
    local config errors out status=0
    CONFIG_ERROR=""
    errors=$(mktemp)
    config=$(python3 "$CONFIG_MODULE" --json --project "$project_dir" 2>"$errors") || status=$?
    if [ "$status" -ne 0 ] && [ "$status" -ne "$MISSING_CONFIG_STATUS" ]; then
        cat "$errors" >&2
        CONFIG_ERROR=$(message_first_line_without_prefix "$errors")
    fi
    rm -f "$errors"
    if [ "$status" -ne 0 ]; then
        return
    fi
    out=$(printf '%s' "$config" | python3 -c '
import json, sys
config = json.load(sys.stdin)
print(json.dumps(config["you"]))
print(json.dumps(config["subagents"]))
print(config["registry"])
print(config["directory"])
')

    YOU_STACK=$(printf '%s\n' "$out" | sed -n '1p')
    SUBAGENT_SECTION=$(printf '%s\n' "$out" | sed -n '2p')
    local dir_override
    dir_override=$(printf '%s\n' "$out" | sed -n '3p')
    MANIFESTO_DIR="${dir_override:-$DEFAULT_MANIFESTO_DIR}"
    CONFIG_DIR=$(printf '%s\n' "$out" | sed -n '4p')

    export YOU_STACK SUBAGENT_SECTION MANIFESTO_DIR CONFIG_DIR
}
