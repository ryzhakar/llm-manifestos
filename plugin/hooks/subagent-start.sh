#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGINS_CACHE_DIR="$(cd "$SCRIPT_DIR/../../../.." 2>/dev/null && pwd)"
if [[ "$PLUGINS_CACHE_DIR" != *"plugins"* ]] || [[ "$PLUGINS_CACHE_DIR" != *"cache"* ]]; then
    PLUGINS_CACHE_DIR="$HOME/.claude/plugins/cache"
fi
export PLUGINS_CACHE_DIR
source "$SCRIPT_DIR/ensure-repo.sh"

if unharness_stands_down; then
    exit 0
fi

detect_manifestos

# Gate: exit only when BOTH you: and subagents: are empty (AND logic)
YOU_EMPTY=false
{ [ -z "${YOU_STACK:-}" ] || [ "$YOU_STACK" = "[]" ]; } && YOU_EMPTY=true
SUBAGENT_EMPTY=false
{ [ -z "${SUBAGENT_SECTION:-}" ] || [ "${SUBAGENT_SECTION}" = "{}" ]; } && SUBAGENT_EMPTY=true
if $YOU_EMPTY && $SUBAGENT_EMPTY; then
    exit 0
fi

PARTS_DIR="$SCRIPT_DIR/templates/parts"
SKILL_MD="$SCRIPT_DIR/../skills/manifesto-oath/SKILL.md"

# Wrap text in the hookSpecificOutput JSON required by SubagentStart hooks.
# Plain text stdout is silently discarded; only this wrapper is injected.
emit_json() {
    python3 -c '
import json, sys
text = sys.stdin.read()
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": text}}))
'
}

# Emit binding frame + SKILL.md for a given ELEMENT_DESCRIPTION
emit_binding() {
    render_template "$PARTS_DIR/preamble-subagent.txt" ELEMENT_DESCRIPTION MANIFESTO_DIR REBIND_NOTE PLUGINS_CACHE_DIR
    echo ""
    render_template "$PARTS_DIR/binding-core.txt" ELEMENT_DESCRIPTION MANIFESTO_DIR REBIND_NOTE PLUGINS_CACHE_DIR
    echo ""
    echo "## Manifesto Oath Protocol (injected from skill)"
    echo ""
    cat "$SKILL_MD"
    cat << 'FOOTER'

If your dispatch prompt contains additional constitution elements beyond those listed here, bind those as well using the same protocol.
FOOTER
}

# Read agent_type from stdin JSON; handle missing/malformed input
AGENT_TYPE=$(python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get("agent_type", ""))
except:
    print("")
' 2>/dev/null || echo "")
export AGENT_TYPE CONFIG_MODULE

# If SUBAGENT_SECTION is empty/missing, emit fallback with full skill injection
if [ -z "${SUBAGENT_SECTION:-}" ] || [ "${SUBAGENT_SECTION}" = "{}" ]; then
    ELEMENT_DESCRIPTION="No role-specific elements matched for this agent type. Your orchestrator provides bindings in the dispatch prompt."
    REBIND_NOTE=""
    export ELEMENT_DESCRIPTION MANIFESTO_DIR REBIND_NOTE
    emit_binding | emit_json
    exit 0
fi

# Match agent_type against SUBAGENT_SECTION keys with the cascade of config.py
MATCHED_ELEMENTS=$(python3 << 'PYEOF'
import json, os, sys

sys.path.insert(0, os.path.dirname(os.environ["CONFIG_MODULE"]))
from config import subagent_key

agent_type = os.environ.get("AGENT_TYPE", "").strip()
sub_raw = os.environ.get("SUBAGENT_SECTION", "{}")

try:
    sub = json.loads(sub_raw)
except:
    sub = {}

if not sub or not isinstance(sub, dict):
    sys.exit(1)

key = subagent_key(agent_type, list(sub))
if key is None:
    sys.exit(1)

print(json.dumps(sub[key]))
PYEOF
) || true

if [ -z "$MATCHED_ELEMENTS" ]; then
    ELEMENT_DESCRIPTION="No role-specific elements matched for this agent type. Your orchestrator provides bindings in the dispatch prompt."
    REBIND_NOTE=""
    export ELEMENT_DESCRIPTION MANIFESTO_DIR REBIND_NOTE
    emit_binding | emit_json
    exit 0
fi

# Render matched elements as natural language
ELEMENT_DESCRIPTION=$(printf '%s' "$MATCHED_ELEMENTS" | python3 "$SCRIPT_DIR/describe_elements.py" "$CONFIG_DIR" "$MANIFESTO_DIR")

REBIND_NOTE=""

export ELEMENT_DESCRIPTION MANIFESTO_DIR REBIND_NOTE
emit_binding | emit_json
