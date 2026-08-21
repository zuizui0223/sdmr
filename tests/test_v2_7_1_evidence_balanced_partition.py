import numpy as np
import pytest

from sdmr.v2_7_1_evidence_balanced_partition import (
    assign_microblocks_to_evidence_balanced_folds,
    make_evidence_balanced_spatial_partitions,
)


def _expand(counts):
    values=[]
    for block, n in counts.items():
        values.extend([block] * n)
    return np.asarray(values, dtype=int)


def test_joint_M_assignment_balances_complementary_background_resources():
    # Eight atomic spatial blocks.  Presence occurs in all blocks.  M150 has
    # support only in blocks 0..3 and M500 only in blocks 4..7.  A feasible
    # four-fold assignment therefore has to pair complementary blocks; this is
    # exactly the structure ordinary presence-only GroupKFold cannot guarantee.
    p = _expand({i: 3 for i in range(8)})
    backgrounds = {
        'buffer_150km': _expand({i: 10 for i in range(4)}),
        'buffer_300km': _expand({i: 6 for i in range(8)}),
        'buffer_500km': _expand({i: 10 for i in range(4, 8)}),
    }
    mapping, ledger, attempts, selected_attempt, selected_seed = (
        assign_microblocks_to_evidence_balanced_folds(
            p,
            backgrounds,
            outer_folds=4,
            minimum_evaluation_occurrences=2,
            minimum_evaluation_background_rows=5,
            minimum_training_background_rows=5,
            assignment_attempts=64,
            random_state=500,
        )
    )
    assert set(mapping) == set(range(8))
    assert set(mapping.values()) == {0, 1, 2, 3}
    assert ledger['structural_support_complete'].all()
    assert ledger['n_evaluation_occurrences'].min() >= 2
    for name in backgrounds:
        assert ledger[f'n_evaluation_background__{name}'].min() >= 5
        assert ledger[f'n_training_background__{name}'].min() >= 5
    assert attempts.loc[selected_attempt, 'structural_support_complete']
    assert selected_seed >= 500


def test_assignment_abstains_when_one_M_can_reach_only_three_atomic_blocks():
    p = _expand({i: 3 for i in range(8)})
    backgrounds = {
        'buffer_150km': _expand({0: 20, 1: 20, 2: 20}),
        'buffer_300km': _expand({i: 10 for i in range(8)}),
        'buffer_500km': _expand({i: 10 for i in range(8)}),
    }
    with pytest.raises(ValueError, match='no evidence-balanced spatial assignment'):
        assign_microblocks_to_evidence_balanced_folds(
            p,
            backgrounds,
            outer_folds=4,
            minimum_evaluation_occurrences=2,
            minimum_evaluation_background_rows=5,
            minimum_training_background_rows=5,
            assignment_attempts=32,
            random_state=900,
        )


def test_coordinate_partition_reuses_one_occurrence_fold_assignment_across_M():
    rng=np.random.default_rng(8)
    centers=np.array([[-120,35],[-80,42],[-10,50],[40,35],[90,45],[135,35]],dtype=float)
    p_lon=[]; p_lat=[]
    for lon,lat in centers:
        p_lon.extend(lon+rng.normal(0,0.3,12)); p_lat.extend(lat+rng.normal(0,0.3,12))
    backgrounds={}
    for name,scale in [('m150',1.0),('m300',1.2),('m500',1.5)]:
        lon=[]; lat=[]
        for x,y in centers:
            lon.extend(x+rng.normal(0,scale,30)); lat.extend(y+rng.normal(0,scale,30))
        backgrounds[name]=(np.asarray(lon),np.asarray(lat))
    result=make_evidence_balanced_spatial_partitions(
        p_lon,p_lat,backgrounds,
        n_microblocks=12,
        outer_folds=4,
        minimum_evaluation_occurrences=2,
        minimum_evaluation_background_rows=5,
        minimum_training_background_rows=5,
        assignment_attempts=32,
        random_state=1200,
    )
    assert set(np.unique(result.presence_folds)) == {0,1,2,3}
    assert result.support_ledger['structural_support_complete'].all()
    for name in backgrounds:
        part=result.for_M(name)
        assert np.array_equal(part.presence_blocks,result.presence_folds)
        assert np.array_equal(part.background_blocks,result.background_folds[name])
        assert set(np.unique(part.presence_blocks)) == {0,1,2,3}
