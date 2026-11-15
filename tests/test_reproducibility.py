import json

from kwst.analysis import run_analysis
from kwst.core.model import Project
from kwst.core.serialization import to_dict, from_dict, dumps


def test_deterministic_results():
    p = Project()
    r1 = run_analysis(p.current)
    r2 = run_analysis(p.current)
    assert r1.fingerprint == r2.fingerprint
    assert r1.input_hash == r2.input_hash


def test_serialization_roundtrip_same_results():
    p = Project()
    p2 = from_dict(Project, json.loads(dumps(p)))
    assert to_dict(p2) == to_dict(p)
    assert run_analysis(p2.current).fingerprint == run_analysis(p.current).fingerprint


def test_validation_items_pass_for_default():
    r = run_analysis(Project().current)
    bad = [i.name for i in r.validation if not i.ok]
    assert not bad, bad
    for c in r.checks:
        if c.eta is not None and c.R_d is not None:
            assert c.R_d >= 0
