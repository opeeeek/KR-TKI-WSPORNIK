"""Silnik materiałowy: beton (tabl. 3.1), stal zbrojeniowa (zał. C), wartości obliczeniowe.

Źródła:
* EN 1992-1-1 tabl. 3.1 — parametry wytrzymałościowe betonu;
* §3.1.6 — f_cd = α_cc·f_ck/γ_c (3.15), f_ctd = α_ct·f_ctk,0,05/γ_c (3.16);
* §3.2.2, §3.2.7, zał. C — stal zbrojeniowa;
* §6.5.2(2) (6.57N) — ν' = 1 − f_ck/250.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .core.model import MaterialsInput
from .normative_parameters import ParameterSet, TABLE_3_1, SUPPORTED_EDITION

CONCRETE_CLASSES = list(TABLE_3_1.keys())

# Zał. C, tabl. C.1 — klasy ciągliwości: (k = (f_t/f_y)_k min, ε_uk min [%])
DUCTILITY_CLASSES = {
    "A": (1.05, 2.5),
    "B": (1.08, 5.0),
    "C": (1.15, 7.5),
}

# Typowe gatunki stali (parametry wg deklaracji producenta / norm wyrobu —
# projektant potwierdza zgodność z dokumentacją dostawy).
STEEL_GRADES = {
    "B500SP": (500.0, "C"),
    "RB500W": (500.0, "C"),
    "BSt500S": (500.0, "B"),
    "B500A": (500.0, "A"),
    "B500B": (500.0, "B"),
    "B500C": (500.0, "C"),
    "B450C": (450.0, "C"),
    "RB400W": (400.0, "C"),
    "Inna": (500.0, "B"),
}

STANDARD_DIAMETERS = [6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 20.0, 25.0, 28.0, 32.0, 40.0]


class MaterialError(ValueError):
    pass


@dataclass(frozen=True)
class ConcreteProps:
    cls: str
    fck: float
    fck_cube: float
    fcm: float
    fctm: float
    fctk005: float
    fctk095: float
    Ecm: float          # MPa
    gamma_c: float
    alpha_cc: float
    alpha_ct: float
    fcd: float
    fctd: float
    nu_prime: float     # (6.57N)
    nu_shear: float     # (6.6N)
    fctd_bond: float    # f_ctd z ograniczeniem do C60/75 (8.4.2(2))

    def check_consistency(self) -> list[str]:
        """Porównanie wartości tablicowych z wzorami tabl. 3.1 (kontrola danych)."""
        issues = []
        fctm_formula = (0.30 * self.fck ** (2.0 / 3.0) if self.fck <= 50
                        else 2.12 * math.log(1.0 + self.fcm / 10.0))
        if abs(fctm_formula - self.fctm) > 0.051 + 1e-9:
            issues.append(f"f_ctm tablicowe {self.fctm} ≠ wzór {fctm_formula:.2f}")
        # wartości tablicowe zaokrąglone do 0,1 MPa — porównanie z wartością niezaokrągloną 0,7·f_ctm(wzór)
        if abs(0.7 * fctm_formula - self.fctk005) > 0.06 + 1e-9:
            issues.append(f"f_ctk,0,05 {self.fctk005} ≠ 0,7·f_ctm")
        Ecm_formula = 22.0 * (self.fcm / 10.0) ** 0.3 * 1000.0
        if abs(Ecm_formula - self.Ecm) > 600.0:
            issues.append(f"E_cm {self.Ecm} ≠ wzór {Ecm_formula:.0f}")
        if abs(self.fcm - (self.fck + 8.0)) > 1e-9:
            issues.append("f_cm ≠ f_ck + 8 MPa")
        return issues


@dataclass(frozen=True)
class SteelProps:
    name: str
    fyk: float
    ductility: str
    k_min: float
    eps_uk_min: float
    gamma_s: float
    fyd: float
    Es: float
    link_fyk: float
    link_fyd: float

    @property
    def eps_yd(self) -> float:
        return self.fyd / self.Es


@dataclass(frozen=True)
class Materials:
    concrete: ConcreteProps
    steel: SteelProps
    situation: str
    d_g: float


def concrete_props(cls: str, ps: ParameterSet, situation: str = "persistent") -> ConcreteProps:
    ps.require(SUPPORTED_EDITION)
    if cls not in TABLE_3_1:
        raise MaterialError(f"Nieznana klasa betonu: {cls}")
    fck, fck_cube, fcm, fctm, fctk005, fctk095, Ecm_gpa = TABLE_3_1[cls]
    gamma_c = ps.v("gamma_c") if situation == "persistent" else ps.v("gamma_c_acc")
    alpha_cc = ps.v("alpha_cc")
    alpha_ct = ps.v("alpha_ct")
    fcd = alpha_cc * fck / gamma_c
    fctd = alpha_ct * fctk005 / gamma_c
    nu_prime = 1.0 - fck / ps.v("nu_prime_div")
    nu_shear = ps.v("nu_shear_coef") * (1.0 - fck / 250.0)
    fctk_bond = min(fctk005, ps.v("fctk_bond_cap"))
    fctd_bond = alpha_ct * fctk_bond / gamma_c
    return ConcreteProps(cls, float(fck), float(fck_cube), float(fcm), float(fctm), float(fctk005),
                         float(fctk095), float(Ecm_gpa) * 1000.0, gamma_c, alpha_cc, alpha_ct, fcd, fctd,
                         nu_prime, nu_shear, fctd_bond)


def steel_props(m: MaterialsInput, ps: ParameterSet, situation: str = "persistent") -> SteelProps:
    ps.require(SUPPORTED_EDITION)
    if m.steel_class not in DUCTILITY_CLASSES:
        raise MaterialError(f"Nieznana klasa ciągliwości stali: {m.steel_class}")
    if not (400.0 <= m.steel_fyk <= 600.0):
        raise MaterialError("f_yk poza zakresem 400–600 MPa (EN 1992-1-1 §3.2.2(3)P, zał. C)")
    if not (400.0 <= m.link_fyk <= 600.0):
        raise MaterialError("f_yk strzemion poza zakresem 400–600 MPa")
    gamma_s = ps.v("gamma_s") if situation == "persistent" else ps.v("gamma_s_acc")
    k, eps = DUCTILITY_CLASSES[m.steel_class]
    Es = ps.v("Es")
    return SteelProps(m.steel_name, m.steel_fyk, m.steel_class, k, eps, gamma_s, m.steel_fyk / gamma_s, Es,
                      m.link_fyk, m.link_fyk / gamma_s)


def build_materials(m: MaterialsInput, ps: ParameterSet) -> Materials:
    if m.design_situation not in ("persistent", "accidental"):
        raise MaterialError("Nieznana sytuacja obliczeniowa")
    if m.d_g <= 0:
        raise MaterialError("Wymiar kruszywa d_g musi być dodatni")
    c = concrete_props(m.concrete, ps, m.design_situation)
    s = steel_props(m, ps, m.design_situation)
    return Materials(c, s, m.design_situation, m.d_g)


def node_limits(c: ConcreteProps, ps: ParameterSet, increase: bool = False) -> dict[str, float]:
    """Graniczne naprężenia w węzłach wg 6.5.4(4) [MPa]."""
    f = ps.v("node_increase") if increase else 1.0
    return {
        "CCC": f * ps.v("k1_node") * c.nu_prime * c.fcd,
        "CCT": f * ps.v("k2_node") * c.nu_prime * c.fcd,
        "CTT": f * ps.v("k3_node") * c.nu_prime * c.fcd,
    }


def strut_limit(c: ConcreteProps, ps: ParameterSet, mode: str) -> tuple[float, str, str]:
    """Graniczne naprężenie w krzyżulcu wg 6.5.2 [MPa], wzór i opis."""
    if mode == "6.55":
        return c.fcd, "σ_Rd,max = f_cd", "(6.55) — brak naprężeń poprzecznych lub ściskanie poprzeczne"
    return (ps.v("strut_cracked") * c.nu_prime * c.fcd, "σ_Rd,max = 0,6·ν'·f_cd",
            "(6.56) — strefa zarysowana / rozciąganie poprzeczne")
