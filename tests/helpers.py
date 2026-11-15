"""Pomocnicze konstruktory wariantów do testów."""
from kwst.core.model import Variant, LoadAction


def direct_variant(V=400e3, H=0.0, **geo) -> Variant:
    """Wariant z jedną wartością obliczeniową (bez współczynników częściowych)."""
    v = Variant()
    v.loads.actions = [LoadAction(name="Ed", nature="design", category="G", V=V, H=H)]
    for k, val in geo.items():
        setattr(v.geometry.right, k, val)
    v.normative.ndp_confirmed = True
    return v


def check(res, cid):
    for c in res.checks:
        if c.id == cid:
            return c
    raise KeyError(cid)
