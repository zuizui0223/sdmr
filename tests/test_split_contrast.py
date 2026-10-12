import sys
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/'experiments'))
from split_contrast import split_by_frozen_location, contrast_eligibility


def test_location_split_avoids_same_location_leakage():
    loc=np.array([9,1,9,5,1,4,4,1,6,8,8,2,7,3,2,7,6,5])
    folds=split_by_frozen_location(loc,seed=0,n_splits=3)
    assert len(folds)==3
    assert sorted(np.concatenate([te for _,te in folds]).tolist())==list(range(len(loc)))
    for tr,te in folds:
        assert set(loc[tr]).isdisjoint(set(loc[te]))
        assert len(tr) and len(te)


def test_invalid_duplicates_or_too_few_locations():
    with pytest.raises(ValueError):split_by_frozen_location(np.array([1,1,1]),seed=0,n_splits=3)


def test_overlap_is_not_reported_as_zero_percent_agreement():
    outcomes={
        'linear':{'A':True,'B':False,'C':False},
        'hgb':{'A':False,'B':True,'C':True},
    }
    c=contrast_eligibility(outcomes,'linear','hgb')
    assert c['both_authorized']==0
    assert c['union_authorized']==3
    assert c['conditional_comparison_evaluable'] is False
    assert c['conditional_agreement'] is None


def test_failed_newton_certificate_abstains_without_removing_taxon():
    from split_contrast import authorization_with_certificates
    outcome={'score':-.5,'gain_over_constant':.193,'p_value':.001,'authorized':True}
    reported=authorization_with_certificates(outcome,[True,False,True])
    assert reported['authorized'] is False
    assert reported['authorized_before_numerical_check'] is True
    assert reported['numerically_certified'] is False
    assert reported['failed_numeric_folds']==1
    good=authorization_with_certificates(outcome,[True,True,True])
    assert good['authorized'] is True
