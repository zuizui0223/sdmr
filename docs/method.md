# Method: from multicollinearity filtering to transferability discovery

## Scientific question

Instead of asking only which raster variables are weakly collinear, SDMR asks:

> Which environmental rasters repeatedly improve prediction of geographically
> independent plant occurrences, and which small raster set transfers to plant
> taxa that were not used to discover it?

This is deliberately a prediction-first definition of *shared niche information*.
It does not claim that the selected variables are universally causal drivers.

## Why a random 50/50 split is not enough

GBIF occurrences are spatially autocorrelated and sampling is spatially biased.
A random point split can place nearly duplicate localities in both train and test
sets. SDMR therefore keeps the user's 50/50 intuition but splits **whole spatial
blocks**. The outer half is never consulted during predictor selection.

## Why held-out occurrences are not "100% occurrence probability"

A record is strong positive evidence that a species occurred at that place and
time. It does not mean a raster cell has a calibrated probability of 1.0, and an
unrecorded cell is not a verified absence. SDMR therefore evaluates a held-out
presence by its **rank against held-out background**. A score of 1.0 means all
held-out presences rank above all background points; 0.5 is random ranking.

## Nested hierarchy

For each discovery species:

1. Create spatial blocks from occurrences on the sphere.
2. Hold out about 50% of blocks as the untouched outer test.
3. On the remaining blocks, use inner GroupKFold CV to perform forward predictor
   selection.
4. Correlated predictors are allowed to compete. A predictor is retained only if
   it adds out-of-block information beyond those already selected.
5. Fit the selected set on all training blocks and evaluate it once on the outer
   blocks. Also fit the full candidate set as a reference.

Across species:

6. Split taxa into discovery and validation taxa (default 50/50).
7. Rank rasters by discovery-species selection frequency and median incremental
   inner-CV gain, weighting each species equally.
8. Freeze the common raster set.
9. Test that frozen set on validation species and, within each validation species,
   on spatial blocks that were also withheld from model fitting.

Thus a raster must generalize across **space and taxa** to earn the label
"common".

## Background recommendation for GBIF

Use target-group background when possible: sample background/reference points
from the spatial footprint of comparable plant records and restrict them to a
biologically defensible accessible area (M) for each focal taxon. This reduces
reward for learning collector effort alone. SDMR accepts species-specific
background tables for this reason.

## Predictor policy

VIF/correlation can still be reported as diagnostics, but they are not an
admission gate. CHELSA v2.1 BIOCLIM variables and biologically interpretable
BIOCLIM+ variables (VPD, GDD, growing-season climate, PET/CMI, radiation, wind,
snow) start as candidates. Selection is determined by nested spatial transfer.

## Interpretation boundary

The resulting set is a *predictively transferable raster basis*, not proof of a
single universal fundamental niche for all plants. Results should also be
reported by clade, growth form, biome, range size, and sampling density once
those metadata are available. A variable that is weak globally may be essential
within one ecological stratum.
