---
name: compile-commitments
description: >
  Write the interplay file and the commitments file that a session's system prompt carries, and their min pair, from the stack the session binds to, or from one subagents key's stack.
  "/compile-commitments", "/compile-commitments <key>", "compile the commitments", "precompile the oath", or a change to the stack.
---

<read-the-stack>
Take the optional argument `<key>`, a key under `subagents:` in the config, `.manifestos/config.yaml` in the working folder, which lists the stack, the ordered elements, each a manifesto, a skill, or a file, that a session binds to; without `<key>`, compile the main stack under `you:`.

Accept `<key>` only when it equals a key under `subagents:` exactly as written, `other` included; for any other word, stop and name the keys in config order, since `unharness` would map an agent type to another key's folder; never compile for a word that is no key.

Set the target folder: `.manifestos/agents/<key>/` with `<key>`, creating it, and `.manifestos/` without; write every file below there and never elsewhere.

Run `${CLAUDE_PLUGIN_ROOT}/bin/unharness stack --config <path>`, adding `--agent <key>` with `<key>`, into a temporary file, where `<path>` is the config; never send the command's output into the conversation.

Read the temporary file whole, the `<stack>` block and then the full text of every element; never read a part of it.

Take each element's demands from its text in that file; never paraphrase an element from memory.
</read-the-stack>

<deconstruct-each-element>
Reduce each element to its axioms, the demands on behavior that remain once you strip its prose; never carry the prose forward as a demand.
</deconstruct-each-element>

<map-convergence-and-tension>
Mark each convergence, a demand two or more elements share, as a constraint that governs first; never leave a shared demand unmarked.

List each tension, a point where two elements pull in opposing directions, with the conflicting sentence quoted from each element; never list a tension without both quotations.

Resolve each tension with an explicit rule that states which demand governs and when; never leave a tension for the moment to settle.

Where no rule resolves a tension, set a priority order among the elements in conflict; never leave two elements level.
</map-convergence-and-tension>

<write-the-interplay-file>
Write `interplay.md` in the target folder; never write it elsewhere.

Open the file with the `<stack>` block copied verbatim from the temporary file; never alter, drop, or reorder a line of it.

After the block, write `<interplay>` ... `</interplay>` holding the axioms, the convergences, the tensions, the rules, and the priority order, in the session's own voice, the first person; never in a voice that reports on the session from outside.

Keep every seam, a sentence that names the config, the file, the tool, or the way the prompt was made, out of the analysis; never let one in.
</write-the-interplay-file>

<write-the-commitments-file>
Write `commitments.md` in the target folder; never write it elsewhere.

Open the file with the same `<stack>` block copied verbatim; never open it with anything else.

After the block, write `<commitments>` ... `</commitments>` holding, for each element in the stack's order, one `I must ..., and I will ...` line and one `I must not ..., and I will not ...` line; never skip an element or change the order.

Fill each line with the element's own demand and the behavior that meets it; never with a seam.

<never_do_this reason="the commitment names the config and the tool that made the prompt">
I must read every element in .manifestos/config.yaml, and I will run unharness stack before each compile.
</never_do_this>

<do_exactly_this>
I must count every line I ship as spent, and I will write the least that does the task.
</do_exactly_this>
</write-the-commitments-file>

<write-the-minified-pair>
Write `interplay.min.md` and `commitments.min.md` in the target folder, in the same run and after the full pair; never write one without its full counterpart or from the elements' texts instead of that counterpart.

Open each with the same `<stack>` block copied verbatim; never alter, drop, or reorder a line of it.

Condense the interplay to the rules that resolve tensions and the priority order, inside `<interplay>` ... `</interplay>`, in the first person; never keep an axiom, a convergence, or a quotation.

Condense the commitments to one `I must ..., and I will ...` line per element in the stack's order, inside `<commitments>` ... `</commitments>`, with the prohibition folded into the line; never write a second line for an element.

Hold each min body, the text after the `<stack>` block, to at most one third of the words of its full counterpart's body, a word being a whitespace-separated token; never ship a body over that budget.

Count each min body and its full counterpart's body with `sed '1,/^<\/stack>$/d' <file> | wc -w`, divide the full count by three, and cut the lowest-ranked rule or the longest line until the min count fits; never report a file without both counts.
</write-the-minified-pair>

<report-the-files>
After writing each file, report its path; never print its content to the conversation.
</report-the-files>

<confirm-the-compile>
Run `${CLAUDE_PLUGIN_ROOT}/bin/unharness prompt --config <path> > /dev/null` and `${CLAUDE_PLUGIN_ROOT}/bin/unharness prompt --minified --config <path> > /dev/null`, adding `--agent <key>` to both with `<key>`; never report the files as done without both runs.

Report the exit code of each run; never report a pass on a code other than 0.

On a code other than 0, correct the file that the printed message names and run both commands again; never stop at a failing run.
</confirm-the-compile>
