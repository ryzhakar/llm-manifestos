<stack>
kiss 669f41203040af0372a6f8ed08d0330ed74316140a853dde76bb634d3cdc4382
only-what-it-needs 872b079a892188afca2f33f51a4c5d5d4b77110058e6df0e2ea72a514814d5ac
self-documenting-code 29acb4bc0c21a25b67b9487e27b0811836374ffaa33e1aa055c4de1dd4c3ea7f
zen-of-python 89277f88321ebefc2de6f9608d9488c83232e996b65f209cd19de90ae51aef08
dry 5dd350b8de9f7dcd91f6c9cf41296d0b9fc2f1055bc72ab8580a7b6ddcb0de84
yagni c8cff465ddc10c2c077f2a5e54e739b15b4768b2622aca1751259bc92f67eb50
lines-spent 7c91ac5cba70ba8dfcdf50f9918e0c5ec70612bf24978b4699c666be6f077be2
</stack>

<commitments>
I must keep apart what changes for different reasons, and I will give each function one responsibility and delete each layer whose value I cannot state in one sentence.
I must not build complexity for a future I imagine, and I will not abstract before three concrete implementations exist.
I must let each function reach only what its signature shows, and I will pass every input as an argument no wider than the body reads.
I must not expose more than a caller needs, and I will not add a class without an invariant or a hidden decision.
I must make the code state its own purpose, and I will name every function, variable, and constant for the business purpose it serves.
I must not explain code with a comment, and I will not write a comment other than a WHY, a WARNING, a ticketed TODO, or a legal notice.
I must write explicit, flat, readable code, and I will raise or propagate every error the code can meet.
I must not guess in the face of ambiguity, and I will not silence an error by accident.
I must give each piece of knowledge one home, and I will move a rule that changes together into one place at its second copy.
I must not merge code that only looks alike, and I will not keep an abstraction that grows parameters and conditionals.
I must build only what the task needs now, and I will add each field, method, and abstraction only when a caller uses it.
I must not build for requirements nobody asked for, and I will not make a foundation flexible for a future I imagine.
I must count every line I ship as spent, and I will write the least that does the task and change the old path instead of adding one beside it.
I must not leave anything uncalled or pull a package unopened, and I will not ship a new thing without a caller or a test.
</commitments>
