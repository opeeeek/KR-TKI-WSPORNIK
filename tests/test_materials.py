import pytest

from kwst.core.model import MaterialsInput, NormativeInput
from kwst.material_engine import concrete_props, build_materials, CONCRETE_CLASSES, node_limits, strut_limit
from kwst.normative_parameters import get_parameter_set, EDITIONS, EditionNotImplemented


@pytest.fixture
def ps():
    return get_parameter_set(NormativeInput())


@pytest.mark.parametrize("cls", CONCRETE_CLASSES)
def test_table_3_1_consistency(cls, ps):
    c = concrete_props(cls, ps)
    assert c.check_consistency() == []
    assert 0 < c.nu_prime < 1


def test_design_values_c30(ps):
    c = concrete_props("C30/37", ps)
    # niezależnie: f_cd = 1,0·30/1,4 ; ν' = 1 − 30/250
    assert c.fcd == pytest.approx(30 / 1.4)
    assert c.fctd == pytest.approx(2.0 / 1.4)
    assert c.nu_prime == pytest.approx(0.88)
    lim = node_limits(c, ps)
    assert lim["CCC"] == pytest.approx(1.0 * 0.88 * 30 / 1.4)
    assert lim["CCT"] == pytest.approx(0.85 * 0.88 * 30 / 1.4)
    assert lim["CTT"] == pytest.approx(0.75 * 0.88 * 30 / 1.4)
    assert strut_limit(c, ps, "6.56")[0] == pytest.approx(0.6 * 0.88 * 30 / 1.4)
    assert strut_limit(c, ps, "6.55")[0] == pytest.approx(30 / 1.4)


def test_bond_cap_c90(ps):
    c = concrete_props("C90/105", ps)
    assert c.fctd_bond == pytest.approx(3.1 / 1.4)   # ograniczenie do C60/75 (8.4.2(2))


def test_steel(ps):
    m = build_materials(MaterialsInput(), ps)
    assert m.steel.fyd == pytest.approx(500 / 1.15)
    bad = MaterialsInput(steel_fyk=700)
    with pytest.raises(ValueError):
        build_materials(bad, ps)


def test_override_and_editions():
    ni = NormativeInput(overrides={"gamma_c": 1.5})
    ps = get_parameter_set(ni)
    assert concrete_props("C30/37", ps).fcd == pytest.approx(20.0)
    with pytest.raises(EditionNotImplemented):
        get_parameter_set(NormativeInput(edition="EC2-2023"))
    # brak przenikania parametrów między edycjami
    assert EDITIONS["EC2-2023"].params == {}
    with pytest.raises(KeyError):
        get_parameter_set(NormativeInput(overrides={"nonexistent": 1.0}))


def test_every_parameter_has_source():
    for p in EDITIONS["EC2-2004-PL"].params.values():
        assert p.clause.strip(), p.key
        assert p.category in ("EN", "NDP", "INF", "ENG")
        assert p.description.strip(), p.key
