# v26 odds-scale observation standardization

Freeze before outcomes. Preserve v25's learner, occurrence/background data,
152 pairs, spatial splits, source omissions, observation weighting, full
prediction guardrail, four-route classifier and all margins/screen values.

Change ecological score construction only. For each evaluation environment,
average fitted occurrence/background odds over the same up-to-64 deterministic
training observation-reference combinations. Normalize those odds by their
mean over **all training background ecological rows** under that same observation
reference. Convert normalized odds to balanced probabilities for ecological
rank and density scoring. Evaluation rows do not enter normalization.

The exact identity in `OBSERVATION_STANDARDIZATION_DIAGNOSTIC.md` motivates
this change under multiplicative observation effects and the stated reference
assumptions. It is not a blanket calibration claim for unrestricted interactions
or arbitrary observation/environment dependence. Test its actual behavior on
all six consumed families. Use the inherited probability clipping epsilon 1e-6.

The nonlinear classifier settings are unchanged from v25. No oracle truth or
generating labels enter fitting or classification. Parallelize independent
pairs to balance runtime, and sort all output identities deterministically.
Source omissions, not scheduler tasks, remain the uncertainty units.

The development screen remains >=95% specific precision, >=20% correct mixed
pair specificity, <=5% mixed false inclusion. v25 remains a failed-coverage
endpoint. No fresh seeds or empirical validation are authorized by this stage.
