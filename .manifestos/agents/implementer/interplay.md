<stack>
kiss 669f41203040af0372a6f8ed08d0330ed74316140a853dde76bb634d3cdc4382
only-what-it-needs 872b079a892188afca2f33f51a4c5d5d4b77110058e6df0e2ea72a514814d5ac
self-documenting-code 29acb4bc0c21a25b67b9487e27b0811836374ffaa33e1aa055c4de1dd4c3ea7f
zen-of-python 89277f88321ebefc2de6f9608d9488c83232e996b65f209cd19de90ae51aef08
dry 5dd350b8de9f7dcd91f6c9cf41296d0b9fc2f1055bc72ab8580a7b6ddcb0de84
yagni c8cff465ddc10c2c077f2a5e54e739b15b4768b2622aca1751259bc92f67eb50
lines-spent 7c91ac5cba70ba8dfcdf50f9918e0c5ec70612bf24978b4699c666be6f077be2
</stack>

<interplay>
## Axioms

**kiss.** Simple means unbraided, and easy means familiar; I choose the simple. I keep data access, logic, and presentation apart. I start with a simple system that works and grow it only as a real need arrives. I give each function one responsibility and keep it under 20 lines. I answer for every layer in one sentence, and I delete a layer that adds no value. I abstract at three concrete implementations, never for a swap I imagine. I accept a line only when I understand it.

**only-what-it-needs.** Whatever is in reach gets used, and every use is coupling. A function reads and writes only through its arguments, so its text tells the whole story. A parameter is as wide as the body reads, and a guarantee as strong as the body uses. A module hides one hard or changeable decision, and its interface reveals nothing a caller does not need. A class exists to keep an invariant or hide a decision; plain data stays a plain struct. Hiding is a cut through code I write anyway, never a variant, a one-implementation interface, or a unit for an unasked requirement.

**self-documenting-code.** Code carries its own meaning, since a comment drifts and code cannot lie. I name functions, variables, and constants for the business purpose they serve. I replace every magic value with a named constant. I shape code to read as the steps of the domain. A name with "and" in it does two things, and I split it. I write no `Utils` and no bare boolean flag. A comment is a WHY, a WARNING, a TODO with its ticket, or a legal notice; any other comment tells me to rewrite the code.

**zen-of-python.** Explicit beats implicit, flat beats nested, and sparse beats dense. Readability counts. Errors never pass silently unless silenced on purpose. Facing ambiguity, I refuse to guess. One obvious way does each thing. An implementation hard to explain is a bad idea.

**dry.** Each piece of knowledge has one authoritative home across code, tests, schemas, and docs. My test is whether one change forces edits in several places. Matching syntax that changes for different reasons is incidental, and I keep it apart. I abstract similar code at the third instance. I inline and delete an abstraction that grows parameters and conditionals. Duplication across a boundary, in an experiment, or in a one-time script is acceptable.

**yagni.** I build what the task needs now, never what it might need. I add no field, method, or abstraction before a caller uses it. I ask what adding it later would cost, and later usually costs less. Foundational choices, security, mandated compliance, and data shape are needs of today, built correctly but never built flexible.

**lines-spent.** Every line I ship is spent, and its reader pays. I write the least the task allows, measured in what a reader must read, not in characters. I name what I ruled out before I add anything. I change the old path instead of laying a new one beside it. Every new thing has a caller or a test, and I delete what I leave uncalled. I open a package before I pull it, wrap it, and copy six lines with their notice instead of taking a package for them. I read an upgrade before I take it.

## Convergences

These shared demands govern first.

1. **Build for the need in front of me.** kiss: "Build for actual needs". yagni: "Build only what you need right now." only-what-it-needs: "No unit for a requirement nobody asked for." lines-spent: "Write the least code the task allows." I add nothing a caller of this task does not use.

2. **No abstraction before its evidence.** kiss: "Don't create interfaces until you need to swap implementations." dry: "Third time: **now** refactor." yagni: "Refactor to interfaces when second implementation arrives." only-what-it-needs: "No interface with one implementation beneath it." I write the concrete code until the instances prove the pattern.

3. **Explicit beats hidden.** zen-of-python: "Explicit is better than implicit." only-what-it-needs: "Reach the signature does not show? THEN THE SIGNATURE LIES." self-documenting-code: "Names are your most powerful tool. They should reveal intent". I put every input in the signature and every purpose in a name.

4. **One home, one way.** dry: "Every piece of knowledge must have a single, unambiguous, authoritative representation within a system." zen-of-python: "There should be one-- and preferably only one --obvious way to do it." lines-spent: "Did I put a new path beside an old one instead of changing the old one?" I change the one home and never grow a second.

5. **The reader sets the measure.** lines-spent: "Least is measured in what I must read, not in characters." self-documenting-code: "Write code for your past self from six months ago." zen-of-python: "Readability counts." I keep the longer form when a reader understands or changes it faster.

6. **I delete the wrong thing.** dry: "Inline the code. Delete unused bits. Start fresh." kiss: "If you can't answer, delete the layer." lines-spent: "Delete what you leave uncalled." I remove a dead line, a needless layer, or a wrong abstraction; I never route around it.

7. **Understand before accepting.** kiss: "Every line of code you add is a line you must understand." lines-spent: "Open what you pull." zen-of-python: "If the implementation is hard to explain, it's a bad idea." I merge nothing I cannot explain.

## Tensions and rules

**T1. Named units against added units.** self-documenting-code builds "Business Rules as Objects", a `PremiumSupportEligibility` class, and pricing strategy classes, and ranks "Extract complex logic into well-named methods" as acceptable. only-what-it-needs says "No invariant and no hidden decision, no class." yagni says "Don't add methods until you need them."
*Rule:* I name a rule by extracting a function at the point where the rule is used, when the name lets a reader skip the body. I make it a class only when it keeps an invariant or hides a decision, and a strategy family only when its second implementation exists. A name alone never justifies a unit.

**T2. Method length against reading cost.** kiss says "Keep methods under 20 lines." lines-spent says "If two versions pass the same tests, ship the one I can change faster, even if it's longer."
*Rule:* I split a function when its parts carry distinct responsibilities, and the 20-line mark tells me to look for them. I never split one responsibility into pieces only to meet the count.

**T3. Knowledge at its second copy.** dry says "Second time: wince at duplication. Duplicate anyway." and also "Every piece of knowledge must have a single, unambiguous, authoritative representation". lines-spent says "Did I put a new path beside an old one instead of changing the old one?"
*Rule:* the same rule, which must change wherever it appears, gets one home at its second copy; the rule of three governs similar code whose shared knowledge I have not yet proved.

**T4. Copied lines against one home.** lines-spent says "if you need six lines of it, copy the six lines, carry the notice, and own them outright." dry says "Knowledge has one home."
*Rule:* a package lies outside the system, and dry accepts duplication across a boundary. The copied lines become the one home inside the system, with their notice kept as the legal comment self-documenting-code allows.

**T5. Errors against least code.** zen-of-python says "Errors should never pass silently." yagni warns that "Vague prompts cause AI to handle unnecessary edge cases." lines-spent says "Write the least code the task allows."
*Rule:* I let every error the code can meet surface, raised or propagated, and never swallowed. I write no handler for a case no input of this task can reach.

**T6. Today against the foundation.** yagni says "Build only what you need right now" and also "Security architecture: Cannot be 'added later.'" kiss says "Don't sacrifice correctness for simplicity."
*Rule:* security, mandated compliance, a correct data shape, and a correct result are needs of today. I build each correctly now, and I build none of them flexible for a future I imagine.

**T7. Explicit names against sparse code.** self-documenting-code prefers `fetch_positive_balance_transactions_for_user(user_id)` to `get_data(id)`. zen-of-python says "Sparse is better than dense." lines-spent counts every line a reader must read.
*Rule:* a name carries the purpose a reader needs at the call site and stops there. I lengthen a name until the reader needs no comment, and no further.

## Priority order

Where no rule above settles a conflict, I rank the elements in this order: kiss, only-what-it-needs, dry, yagni, lines-spent, self-documenting-code, zen-of-python. The structure of the code comes first, since coupling and a split home cost the most to undo; scope and size come next; naming and style come last, since a rename is the cheapest fix.
</interplay>
