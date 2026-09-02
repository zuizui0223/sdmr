import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from sdmr.model import DETERMINISTIC_RANDOM_STATE_ENV, fit_relative_suitability_model


def _frames():
    presence=pd.DataFrame({
        'x':[0.9,1.1,1.3,1.5,1.7,1.9],
        'z':[1.8,1.6,1.5,1.2,1.0,0.8],
    })
    background=pd.DataFrame({
        'x':[-1.8,-1.2,-0.8,-0.2,0.2,0.5,0.7,1.0],
        'z':[-1.0,-0.5,0.0,0.4,0.8,1.1,1.3,1.5],
    })
    return presence, background


def test_execution_seed_is_opt_in_and_does_not_change_model_label(monkeypatch):
    presence,background=_frames()
    monkeypatch.delenv(DETERMINISTIC_RANDOM_STATE_ENV, raising=False)
    legacy=fit_relative_suitability_model(presence,background,['x','z'])
    assert legacy.named_steps['logisticregression'].random_state is None

    monkeypatch.setenv(DETERMINISTIC_RANDOM_STATE_ENV,'271')
    deterministic=fit_relative_suitability_model(presence,background,['x','z'])
    assert deterministic.named_steps['logisticregression'].random_state == 271


def test_execution_seed_makes_repeated_fit_exact_after_unrelated_rng_use(monkeypatch):
    presence,background=_frames()
    monkeypatch.setenv(DETERMINISTIC_RANDOM_STATE_ENV,'271')
    first=fit_relative_suitability_model(presence,background,['x','z'])
    _=np.random.default_rng(999).normal(size=10000)
    second=fit_relative_suitability_model(presence,background,['x','z'])
    np.testing.assert_array_equal(
        first.named_steps['logisticregression'].coef_,
        second.named_steps['logisticregression'].coef_,
    )
    np.testing.assert_array_equal(
        first.named_steps['logisticregression'].intercept_,
        second.named_steps['logisticregression'].intercept_,
    )


def test_execution_seed_is_exact_across_independent_python_processes(tmp_path):
    script=tmp_path/'probe.py'
    script.write_text('''\nimport json, os\nimport numpy as np\nimport pandas as pd\nfrom sdmr.model import fit_relative_suitability_model\nnp.random.seed(int(os.environ["UNRELATED_NUMPY_SEED"]))\npresence=pd.DataFrame({"x":[0.9,1.1,1.3,1.5,1.7,1.9],"z":[1.8,1.6,1.5,1.2,1.0,0.8]})\nbackground=pd.DataFrame({"x":[-1.8,-1.2,-0.8,-0.2,0.2,0.5,0.7,1.0],"z":[-1.0,-0.5,0.0,0.4,0.8,1.1,1.3,1.5]})\nmodel=fit_relative_suitability_model(presence,background,["x","z"])\nlogit=model.named_steps["logisticregression"]\nprint(json.dumps({"coef":logit.coef_.tolist(),"intercept":logit.intercept_.tolist(),"n_iter":logit.n_iter_.tolist()},sort_keys=True,separators=(",",":")))\n''')
    outputs=[]
    for hash_seed,numpy_seed in [('1','111'),('987654','999')]:
        env=os.environ.copy()
        env[DETERMINISTIC_RANDOM_STATE_ENV]='271'
        env['PYTHONHASHSEED']=hash_seed
        env['UNRELATED_NUMPY_SEED']=numpy_seed
        outputs.append(subprocess.check_output([sys.executable,str(script)],env=env,text=True).strip())
    assert outputs[0] == outputs[1]
    payload=json.loads(outputs[0])
    assert payload['n_iter']


@pytest.mark.parametrize('value',['not-an-int','-1',str(2**32)])
def test_invalid_execution_seed_fails_closed(monkeypatch,value):
    presence,background=_frames()
    monkeypatch.setenv(DETERMINISTIC_RANDOM_STATE_ENV,value)
    with pytest.raises(ValueError, match=DETERMINISTIC_RANDOM_STATE_ENV):
        fit_relative_suitability_model(presence,background,['x','z'])
