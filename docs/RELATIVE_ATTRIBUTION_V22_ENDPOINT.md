# Relative attribution v22 — frozen development endpoint

v22 is a negative consumed-development endpoint on seeds 17001–17010.

Authoritative evidence:
- head `dc842a03d34468eb3783fd1314da2df8a449a54f`
- workflow run `34921157441`
- aggregate artifact `10378537060`
- digest `sha256:e1ae4ba5355634d31c22cfc0ca2f4636a2953540febe7077727ff4d26379e0e8`

Frozen denominator: 122 contexts with at least two v21-supported processes, yielding 152 unordered supported-process pairs.

Pair states:
- P_favored: 17
- Q_favored: 12
- coessential: 7
- exchangeable: 42
- unresolved: 74
- unresolved rate: 0.4868

Development-only known-truth scoring after pair statuses were frozen:
- mixed true-vs-false pairs favor the true process: 0.0698
- seasonality-vs-true pairs demote seasonality: 0.0732
- true temperature-vs-water pairs retain at least one directional/nonexchangeable signal: 0.2752

Conclusion: symmetric pairwise hard-knockout necessity is not a reliable resolver of co-active supported processes. It must not be retuned on these consumed seeds. The prospectively supported v21 `supported` tier remains intact; when several processes are supported in one context, the default successor representation is a set-valued attribution rather than a forced winner. Sharpening is allowed only when genuinely new separating evidence is available.
