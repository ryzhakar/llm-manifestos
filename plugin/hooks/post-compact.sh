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

if [ -n "$CONFIG_ERROR" ]; then
    unbound_line | emit_context PostCompact
    exit 0
fi

# Gate: no config → silent exit
YOU_EMPTY=false
{ [ -z "${YOU_STACK:-}" ] || [ "$YOU_STACK" = "[]" ]; } && YOU_EMPTY=true
if $YOU_EMPTY; then
    exit 0
fi

# Render orchestrator elements as natural language prose
ELEMENT_DESCRIPTION=$(printf '%s' "$YOU_STACK" | python3 "$SCRIPT_DIR/describe_elements.py" "$CONFIG_DIR" "$MANIFESTO_DIR")

REBIND_NOTE="Previous bindings, oath state, and interplay analyses were lost in compaction. Re-read and rebind everything from source."

export ELEMENT_DESCRIPTION MANIFESTO_DIR REBIND_NOTE
PARTS_DIR="$SCRIPT_DIR/templates/parts"
SKILL_MD="$SCRIPT_DIR/../skills/manifesto-oath/SKILL.md"
{
    render_template "$PARTS_DIR/preamble-compact.txt" ELEMENT_DESCRIPTION MANIFESTO_DIR REBIND_NOTE PLUGINS_CACHE_DIR
    echo ""
    render_template "$PARTS_DIR/binding-core.txt" ELEMENT_DESCRIPTION MANIFESTO_DIR REBIND_NOTE PLUGINS_CACHE_DIR
    echo ""
    echo "## Manifesto Oath Protocol (injected from skill)"
    echo ""
    cat "$SKILL_MD"

    # Inline footer: compacted user-elements recovery + subagent dispatch note
    cat << 'FOOTER'

## User-Provided Constitution Elements

The elements above are the BASE STACK. If the user previously provided additional constitution elements in this session, those bindings were also lost in compaction.

User-provided elements cannot be reliably recovered from a compacted summary — the compaction may have elided exactly that information. Do not attempt to reconstruct them from inference. Instead: ask the user to re-specify any elements they added during the session before this compaction. Once re-specified, load and bind them using the same full protocol and layer them on top of the base stack.

## Subagent Constitution Dispatch

The SubagentStart hook injects role-matched element names, purposes, and the oath protocol into subagents automatically — never element content. Subagents load content from source, so your dispatch prompt MUST carry the path or URL for every element without a configured source. You MAY add extra elements in dispatch prompts to augment the automatic stack.
FOOTER
} | emit_context PostCompact
