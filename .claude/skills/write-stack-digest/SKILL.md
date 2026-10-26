---
name: write-stack-digest
description: "Write one stack's digest: the plain text a small model carries in place of several manifestos, composed from their digests alone. \"write the stack digest\", \"compose the stack\", \"digest the stack\", \"bind the stack for the small model\", or a project whose stack index names members with no stack digest or one older than a member's digest."
---

<take-the-members>
Take the member list from the stack index, the list in `.manifestos/config.yaml` naming the manifestos a project binds; never take members from elsewhere.
Read each member's digest, the plain text the `write-digest` skill writes, whole; never read the original manifesto.
</take-the-members>

<bind-to-the-members>
Bind to all members through the `manifesto-oath` skill, whose interplay analysis deconstructs each digest to its demands, the things it tells its reader to do or refuse, maps where they converge, maps where they pull apart, resolves each tension with one rule, and settles a priority order; never compose unbound.
</bind-to-the-members>

<merge-and-resolve>
Merge demands that converge into one sentence; never carry one concept as two sentences.
Replace both sides of each tension with its resolution; never carry a tension on both sides.
Carry every other demand as its digest states it; never reword one.
</merge-and-resolve>

<save-the-resolutions>
Save each tension and the rule that replaces it as the resolutions record through the `write-eval-record` skill; never leave a resolution in the binding output alone.
</save-the-resolutions>

<order-the-rules>
Order by the priority the binding settled; never order by member.
</order-the-rules>

<name-the-object>
Say in the sentence what it applies to, the reply, the code, or the schema, where members govern different things; never leave such a sentence unscoped.
</name-the-object>

<add-the-standing-line>
Add one line that applies the rules to every reply, including drift; never leave the digest without it.
Write it as an order telling the reader to check reply ten as it checked reply one; never write it as a forecast that the reader will drift.
</add-the-standing-line>

<write-the-sentences>
Write every sentence as the `write-digest` skill writes one, with Strunk applied; never write one another way.
</write-the-sentences>

<check-against-the-members>
Check against the member digests, every demand present, merged, resolved, or deliberately dropped, no tension carried on both sides, nothing imported; never check against memory of them.
</check-against-the-members>

<shape-the-file>
Write the body alone, in portable markdown, markdown with no feature past paragraphs and lists, under 850 words; never add a header, a frontmatter, or a title.
</shape-the-file>

<save-the-file>
Save it as `.manifestos/digests/<slugs sorted, joined by +>.md` in the project that declares the stack; never save the working copy elsewhere.
Save a tracked reference copy as `plugin/digests/stacks/<slugs sorted, joined by +>.md` in the manifesto repo when the owner rules it, as the owner ruled for the Petro stack on 2026-10-14; never save one without such a ruling.
Keep the reference copy as the cut the ruling named; never edit it without a new cut recorded.
</save-the-file>
