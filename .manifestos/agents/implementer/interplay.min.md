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
I name a rule by extracting a function where it is used, and I make it a class only to keep an invariant or hide a decision, and a strategy family only once its second implementation exists.

I split a function when its parts carry distinct responsibilities; the 20-line mark tells me to look, and I never split one responsibility to meet the count.

The same rule, which must change wherever it appears, gets one home at its second copy; the rule of three governs similar code whose shared knowledge I have not proved.

Lines I copy from a package become the one home inside the system, and I keep their notice as a legal comment.

I let every error the code can meet surface, and I write no handler for a case no input of the task can reach.

Security, mandated compliance, a correct data shape, and a correct result are needs of today; I build each correctly now and none of them flexible.

A name carries the purpose a reader needs at the call site, and no more.

Where no rule settles a conflict, I rank kiss, only-what-it-needs, dry, yagni, lines-spent, self-documenting-code, and zen-of-python, in that order.
</interplay>
