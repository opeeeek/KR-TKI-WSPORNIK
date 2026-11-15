"""Rejestr parametrów normowych z wersjonowaniem edycji Eurokodu.

Każdy parametr ma jednoznaczne źródło (punkt/wzór/tablica), kategorię
(wartość z treści normy, parametr krajowy NDP, załącznik informacyjny,
zalecenie inżynierskie) oraz status weryfikacji.

Zasady:

* edycje NIE dziedziczą parametrów od siebie — brak "przecieku" wymagań
  pomiędzy 1. i 2. generacją EN 1992-1-1;
* parametr oznaczony jako ``blocking`` (niepewna wartość tablicowa) nie jest
  stosowany automatycznie do wyniku pozytywnego, dopóki projektant go nie
  potwierdzi (``NormativeInput.confirmed_params``);
* wartości NDP wymagają potwierdzenia przez projektanta zgodności z
  obowiązującym Załącznikiem Krajowym (``NormativeInput.ndp_confirmed``) —
  do tego czasu werdykt ma charakter warunkowy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .core.model import NormativeInput


class EditionNotImplemented(RuntimeError):
    """Wybrana edycja normy nie jest zaimplementowana."""


# Kategorie parametrów
CAT_EN = "EN"     # wartość z treści normy (nie podlega wyborowi krajowemu)
CAT_NDP = "NDP"   # parametr ustalany krajowo
CAT_INF = "INF"   # załącznik informacyjny (zał. J) — wartość zalecana / NDP
CAT_ENG = "ENG"   # zalecenie inżynierskie — nie jest wymaganiem EC2

CATEGORY_LABEL = {
    CAT_EN: "wartość normatywna (treść normy)",
    CAT_NDP: "parametr krajowy (NDP)",
    CAT_INF: "załącznik informacyjny / NDP",
    CAT_ENG: "zalecenie inżynierskie (nie wymóg EC2)",
}


@dataclass(frozen=True)
class NormParam:
    key: str
    symbol: str
    value: float
    unit: str
    clause: str
    category: str
    description: str
    recommended: float | None = None
    na_note: str = ""
    status: str = "przyjęta"
    blocking: bool = False
    editable: bool = True


@dataclass(frozen=True)
class Edition:
    id: str
    title: str
    implemented: bool
    params: dict[str, NormParam] = field(default_factory=dict)
    tables: dict[str, Any] = field(default_factory=dict)
    description: str = ""


NA_PL = "PN-EN 1992-1-1:2008/NA:2010"
NA_PL_1990 = "PN-EN 1990:2004/NA:2010"


def _p(key, symbol, value, unit, clause, category, description, recommended=None,
       na_note="", status=None, blocking=False, editable=True) -> NormParam:
    if status is None:
        status = {CAT_EN: "przyjęta wg treści normy",
                  CAT_NDP: "do potwierdzenia z NA",
                  CAT_INF: "do potwierdzenia z NA",
                  CAT_ENG: "zalecenie — stosowanie decyzją projektanta"}[category]
    return NormParam(key, symbol, value, unit, clause, category, description, recommended,
                     na_note, status, blocking, editable)


_EC2_2004_PARAMS = [
    # --- współczynniki częściowe i materiałowe -------------------------------
    _p("gamma_c", "γ_c", 1.4, "-", "EN 1992-1-1 §2.4.2.4(1), tabl. 2.1N", CAT_NDP,
       "Współczynnik częściowy dla betonu — sytuacje trwałe i przejściowe.", 1.5,
       f"{NA_PL}: γ_c = 1,4 (wartość krajowa różna od zalecanej 1,5)."),
    _p("gamma_s", "γ_s", 1.15, "-", "EN 1992-1-1 §2.4.2.4(1), tabl. 2.1N", CAT_NDP,
       "Współczynnik częściowy dla stali zbrojeniowej — sytuacje trwałe i przejściowe.", 1.15,
       f"{NA_PL}: wartość zalecana."),
    _p("gamma_c_acc", "γ_c,acc", 1.2, "-", "EN 1992-1-1 §2.4.2.4(1), tabl. 2.1N", CAT_NDP,
       "Współczynnik częściowy dla betonu — sytuacje wyjątkowe.", 1.2),
    _p("gamma_s_acc", "γ_s,acc", 1.0, "-", "EN 1992-1-1 §2.4.2.4(1), tabl. 2.1N", CAT_NDP,
       "Współczynnik częściowy dla stali — sytuacje wyjątkowe.", 1.0),
    _p("alpha_cc", "α_cc", 1.0, "-", "EN 1992-1-1 §3.1.6(1)P", CAT_NDP,
       "Współczynnik efektów długotrwałych i niekorzystnego sposobu przyłożenia obciążenia (ściskanie).", 1.0),
    _p("alpha_ct", "α_ct", 1.0, "-", "EN 1992-1-1 §3.1.6(2)P", CAT_NDP,
       "Współczynnik efektów długotrwałych dla wytrzymałości na rozciąganie.", 1.0),
    _p("Es", "E_s", 200000.0, "MPa", "EN 1992-1-1 §3.2.7(4)", CAT_EN,
       "Moduł sprężystości stali zbrojeniowej (wartość obliczeniowa)."),
    # --- STM: krzyżulce i węzły --------------------------------------------
    _p("nu_prime_div", "250 w ν' = 1 − f_ck/250", 250.0, "MPa", "EN 1992-1-1 §6.5.2(2), wzór (6.57N)",
       CAT_NDP, "Mianownik we wzorze na współczynnik redukcyjny ν' (krzyżulce i węzły).", 250.0),
    _p("strut_cracked", "0,6 w (6.56)", 0.6, "-", "EN 1992-1-1 §6.5.2(2), wzór (6.56)", CAT_EN,
       "Współczynnik nośności krzyżulca w strefie zarysowanej: σ_Rd,max = 0,6·ν'·f_cd."),
    _p("k1_node", "k₁", 1.0, "-", "EN 1992-1-1 §6.5.4(4)a), wzór (6.60)", CAT_NDP,
       "Węzły ściskane bez zakotwionych cięgien (CCC): σ_Rd,max = k₁·ν'·f_cd.", 1.0),
    _p("k2_node", "k₂", 0.85, "-", "EN 1992-1-1 §6.5.4(4)b), wzór (6.61)", CAT_NDP,
       "Węzły ściskano-rozciągane z cięgnem zakotwionym w jednym kierunku (CCT).", 0.85),
    _p("k3_node", "k₃", 0.75, "-", "EN 1992-1-1 §6.5.4(4)c), wzór (6.62)", CAT_NDP,
       "Węzły ściskano-rozciągane z cięgnami w więcej niż jednym kierunku (CTT).", 0.75),
    _p("k4_node", "k₄", 3.0, "-", "EN 1992-1-1 §6.5.4(6)", CAT_NDP,
       "Górna granica dla węzłów w trójosiowym ściskaniu — NIE stosowana automatycznie.", 3.0),
    _p("node_increase", "1,10", 1.10, "-", "EN 1992-1-1 §6.5.4(5)", CAT_EN,
       "Dopuszczalne zwiększenie σ_Rd,max węzła o 10% przy spełnieniu warunków 6.5.4(5)."),
    # --- załącznik J.3 -----------------------------------------------------
    _p("J3_k1", "k₁ (J.3)", 0.25, "-", "EN 1992-1-1 zał. J.3(2)", CAT_INF,
       "Minimalne strzemiona poziome/ukośne A_s,lnk ≥ k₁·A_s,main gdy a_c < 0,5·h_c.", 0.25,
       "Zał. J jest informacyjny — status w PL wymaga potwierdzenia z NA."),
    _p("J3_k2", "k₂ (J.3)", 0.5, "-", "EN 1992-1-1 zał. J.3(3)", CAT_INF,
       "Minimalne strzemiona pionowe A_s,lnk ≥ k₂·F_Ed/f_yd gdy a_c > 0,5·h_c i F_Ed > V_Rd,c.", 0.5),
    _p("J3_tan_min", "tan θ_min", 1.0, "-", "EN 1992-1-1 zał. J.3(1)", CAT_INF,
       "Dolna granica nachylenia krzyżulca we wsporniku: 1,0 ≤ tan θ."),
    _p("J3_tan_max", "tan θ_max", 2.5, "-", "EN 1992-1-1 zał. J.3(1)", CAT_INF,
       "Górna granica nachylenia krzyżulca we wsporniku: tan θ ≤ 2,5."),
    # --- ścinanie 6.2.2 ----------------------------------------------------
    _p("CRdc_num", "0,18 w C_Rd,c = 0,18/γ_c", 0.18, "-", "EN 1992-1-1 §6.2.2(1)", CAT_NDP,
       "Współczynnik nośności na ścinanie elementów bez zbrojenia poprzecznego.", 0.18),
    _p("k1_shear", "k₁ (6.2.2)", 0.15, "-", "EN 1992-1-1 §6.2.2(1)", CAT_NDP,
       "Współczynnik wpływu naprężeń normalnych σ_cp.", 0.15),
    _p("vmin_coef", "0,035 w v_min", 0.035, "-", "EN 1992-1-1 §6.2.2(1), wzór (6.3N)", CAT_NDP,
       "v_min = 0,035·k^(3/2)·f_ck^(1/2).", 0.035),
    _p("nu_shear_coef", "0,6 w ν = 0,6(1 − f_ck/250)", 0.6, "-", "EN 1992-1-1 §6.2.2(6), wzór (6.6N)",
       CAT_NDP, "Współczynnik redukcyjny wytrzymałości betonu zarysowanego przy ścinaniu.", 0.6),
    _p("shear_max_factor", "0,5 w V_Ed ≤ 0,5·b_w·d·ν·f_cd", 0.5, "-", "EN 1992-1-1 §6.2.2(6), wzór (6.5)",
       CAT_EN, "Graniczna siła poprzeczna przy obciążeniu blisko podpory."),
    _p("sigma_cp_max", "0,2 f_cd", 0.2, "-", "EN 1992-1-1 §6.2.2(1)", CAT_EN,
       "Ograniczenie σ_cp < 0,2·f_cd."),
    # --- docisk 6.7 --------------------------------------------------------
    _p("bearing_max", "3,0 w (6.63)", 3.0, "-", "EN 1992-1-1 §6.7(2), wzór (6.63)", CAT_EN,
       "Górna granica nośności na docisk: F_Rdu ≤ 3,0·f_cd·A_c0."),
    # --- przyczepność i zakotwienie (rozdz. 8) ------------------------------
    _p("bond_coef", "2,25 w (8.2)", 2.25, "-", "EN 1992-1-1 §8.4.2(2), wzór (8.2)", CAT_EN,
       "f_bd = 2,25·η₁·η₂·f_ctd."),
    _p("eta1_poor", "η₁ (słabe warunki)", 0.7, "-", "EN 1992-1-1 §8.4.2(2)", CAT_EN,
       "Współczynnik warunków przyczepności dla 'innych' (słabych) warunków."),
    _p("fctk_bond_cap", "f_ctk,0,05 ≤ C60/75", 3.1, "MPa", "EN 1992-1-1 §8.4.2(2)", CAT_EN,
       "Ograniczenie f_ctk,0,05 do wartości dla C60/75 przy wyznaczaniu f_bd."),
    _p("lbmin_ratio", "0,3 w l_b,min", 0.3, "-", "EN 1992-1-1 §8.4.4(1), wzór (8.6)", CAT_EN,
       "l_b,min = max{0,3·l_b,rqd; 10φ; 100 mm} (rozciąganie)."),
    _p("alpha235_min", "α₂α₃α₅ ≥ 0,7", 0.7, "-", "EN 1992-1-1 §8.4.4(1), wzór (8.5)", CAT_EN,
       "Dolne ograniczenie iloczynu α₂·α₃·α₅."),
    _p("mandrel_small", "φ_m,min (φ ≤ 16)", 4.0, "φ", "EN 1992-1-1 §8.3(2), tabl. 8.1N", CAT_NDP,
       "Minimalna średnica trzpienia dla odgięć, haków i pętli: 4φ dla φ ≤ 16 mm.", 4.0),
    _p("mandrel_large", "φ_m,min (φ > 16)", 7.0, "φ", "EN 1992-1-1 §8.3(2), tabl. 8.1N", CAT_NDP,
       "Minimalna średnica trzpienia dla odgięć, haków i pętli: 7φ dla φ > 16 mm.", 7.0),
    _p("fcd_mandrel_cap", "f_cd ≤ C55/67", 55.0, "MPa", "EN 1992-1-1 §8.3(3)", CAT_EN,
       "We wzorze (8.1) nie przyjmuje się f_cd większego niż dla klasy C55/67 (f_ck = 55 MPa)."),
    _p("hook_extension", "≥ 5φ", 5.0, "φ", "EN 1992-1-1 §8.4.1, rys. 8.1b,c", CAT_EN,
       "Minimalne przedłużenie proste za odgięciem / hakiem standardowym (rys. 8.1).",
       status="do potwierdzenia z treścią rys. 8.1"),
    _p("fwd_factor", "F_wd = k·A_s·f_yd", 0.5, "-", "EN 1992-1-1 §8.6(2), wzór (8.8N)", CAT_NDP,
       "Nośność spoiny pręta poprzecznego jako ułamek A_s·f_yd pręta kotwionego (wartość przykładowa normy "
       "'np. 0,5') — wymaga potwierdzenia dla stosowanej technologii spawania.", 0.5),
    # --- rozstaw prętów 8.2 -----------------------------------------------
    _p("spacing_k1", "k₁ (8.2)", 1.0, "-", "EN 1992-1-1 §8.2(2)", CAT_NDP,
       "Minimalny odstęp w świetle: max{k₁·φ; d_g + k₂; 20 mm}.", 1.0),
    _p("spacing_k2", "k₂ (8.2)", 5.0, "mm", "EN 1992-1-1 §8.2(2)", CAT_NDP,
       "Minimalny odstęp w świetle: max{k₁·φ; d_g + k₂; 20 mm}.", 5.0),
    # --- otulina 4.4.1 -----------------------------------------------------
    _p("delta_c_dev", "Δc_dev", 10.0, "mm", "EN 1992-1-1 §4.4.1.3(1)P", CAT_NDP,
       "Odchyłka wykonawcza otuliny (wartość zalecana; redukcja możliwa przy kontroli jakości).", 10.0),
    _p("delta_c_dur_gamma", "Δc_dur,γ", 0.0, "mm", "EN 1992-1-1 §4.4.1.2(6)", CAT_NDP,
       "Dodatkowy element bezpieczeństwa otuliny.", 0.0),
    _p("delta_c_dur_st", "Δc_dur,st", 0.0, "mm", "EN 1992-1-1 §4.4.1.2(7)", CAT_NDP,
       "Redukcja otuliny przy stali nierdzewnej.", 0.0),
    _p("delta_c_dur_add", "Δc_dur,add", 0.0, "mm", "EN 1992-1-1 §4.4.1.2(8)", CAT_NDP,
       "Redukcja otuliny przy dodatkowym zabezpieczeniu.", 0.0),
    # --- zbrojenie minimalne / maksymalne -----------------------------------
    _p("As_min_coef", "0,26 w A_s,min", 0.26, "-", "EN 1992-1-1 §9.2.1.1(1), wzór (9.1N)", CAT_ENG,
       "A_s,min = 0,26·f_ctm/f_yk·b_t·d — zastosowanie do wspornika przez analogię do belek "
       "(zał. J.3 nie określa minimum zbrojenia głównego).", 0.26),
    _p("As_min_abs", "0,0013 w A_s,min", 0.0013, "-", "EN 1992-1-1 §9.2.1.1(1), wzór (9.1N)", CAT_ENG,
       "A_s,min ≥ 0,0013·b_t·d — analogia do belek.", 0.0013),
    _p("As_max_coef", "0,04 A_c", 0.04, "-", "EN 1992-1-1 §9.2.1.1(3)", CAT_ENG,
       "A_s,max = 0,04·A_c — analogia do belek.", 0.04),
    # --- połączenia prefabrykowane 10.9.5 ----------------------------------
    _p("fRd_dry", "f_Rd = 0,4 f_cd", 0.4, "-", "EN 1992-1-1 §10.9.5.2(2)", CAT_EN,
       "Wytrzymałość obliczeniowa na docisk w oparciach — połączenia 'na sucho'.",
       status="do potwierdzenia z treścią normy", blocking=True),
    _p("fRd_other", "f_Rd ≤ 0,85 f_cd", 0.85, "-", "EN 1992-1-1 §10.9.5.2(2)", CAT_EN,
       "Wytrzymałość obliczeniowa na docisk w oparciach — pozostałe przypadki (f_bed ≤ 0,85 f_cd).",
       status="do potwierdzenia z treścią normy", blocking=True),
    _p("table_10_2", "tabl. 10.2", 1.0, "-", "EN 1992-1-1 §10.9.5.2, tabl. 10.2", CAT_EN,
       "Minimalne długości oparcia netto a₁ — wartości tablicowe wbudowane w program.",
       status="do potwierdzenia z treścią normy", blocking=True, editable=False),
    # --- SGU ----------------------------------------------------------------
    _p("wmax_X0_XC1", "w_max (X0, XC1)", 0.4, "mm", "EN 1992-1-1 §7.3.1(5), tabl. 7.1N", CAT_NDP,
       "Graniczna szerokość rys — klasy X0, XC1 (kombinacja quasi-stała).", 0.4),
    _p("wmax_other", "w_max (XC2–XS3)", 0.3, "mm", "EN 1992-1-1 §7.3.1(5), tabl. 7.1N", CAT_NDP,
       "Graniczna szerokość rys — pozostałe klasy ekspozycji.", 0.3),
    # --- EN 1990 -----------------------------------------------------------
    _p("gamma_G_sup", "γ_G,sup", 1.35, "-", "EN 1990 tabl. A1.2(B)", CAT_NDP,
       "Współczynnik częściowy oddziaływań stałych niekorzystnych.", 1.35, f"{NA_PL_1990}"),
    _p("gamma_G_inf", "γ_G,inf", 1.0, "-", "EN 1990 tabl. A1.2(B)", CAT_NDP,
       "Współczynnik częściowy oddziaływań stałych korzystnych.", 1.0),
    _p("gamma_Q", "γ_Q", 1.5, "-", "EN 1990 tabl. A1.2(B)", CAT_NDP,
       "Współczynnik częściowy oddziaływań zmiennych.", 1.5),
    _p("xi", "ξ", 0.85, "-", "EN 1990 tabl. A1.2(B), wzór (6.10b)", CAT_NDP,
       "Współczynnik redukcyjny oddziaływań stałych niekorzystnych w (6.10b).", 0.85),
    # --- zalecenia inżynierskie -------------------------------------------
    _p("outer_depth_ratio", "h(x_zew)/h_c ≥ 0,5", 0.5, "-",
       "Zalecenie konstrukcyjne (por. ACI 318, rozdz. 16.5 — odniesienie porównawcze)", CAT_ENG,
       "Wysokość wspornika pod zewnętrzną krawędzią płyty oporowej nie mniejsza niż 0,5·h_c."),
    _p("h_link_zone", "strefa strzemion poziomych", 2.0 / 3.0, "d",
       "Zalecenie konstrukcyjne (por. rys. J.6a; ACI 318 rozdz. 16.5 — odniesienie porównawcze)", CAT_ENG,
       "Strzemiona poziome rozmieszczane w strefie ≈ 2/3·d poniżej zbrojenia głównego."),
    _p("tie_axis_tol", "tolerancja osi cięgna", 0.05, "d", "Kontrola modelu (6.5.3, 6.5.4(7))", CAT_ENG,
       "Dopuszczalna odchyłka osi cięgna w modelu od środka ciężkości zbrojenia."),
]


TABLE_3_1 = {
    # klasa: (fck, fck_cube, fcm, fctm, fctk_005, fctk_095, Ecm[GPa])  — EN 1992-1-1 tabl. 3.1
    "C12/15": (12, 15, 20, 1.6, 1.1, 2.0, 27),
    "C16/20": (16, 20, 24, 1.9, 1.3, 2.5, 29),
    "C20/25": (20, 25, 28, 2.2, 1.5, 2.9, 30),
    "C25/30": (25, 30, 33, 2.6, 1.8, 3.3, 31),
    "C30/37": (30, 37, 38, 2.9, 2.0, 3.8, 33),
    "C35/45": (35, 45, 43, 3.2, 2.2, 4.2, 34),
    "C40/50": (40, 50, 48, 3.5, 2.5, 4.6, 35),
    "C45/55": (45, 55, 53, 3.8, 2.7, 4.9, 36),
    "C50/60": (50, 60, 58, 4.1, 2.9, 5.3, 37),
    "C55/67": (55, 67, 63, 4.2, 3.0, 5.5, 38),
    "C60/75": (60, 75, 68, 4.4, 3.1, 5.7, 39),
    "C70/85": (70, 85, 78, 4.6, 3.2, 6.0, 41),
    "C80/95": (80, 95, 88, 4.8, 3.4, 6.3, 42),
    "C90/105": (90, 105, 98, 5.0, 3.5, 6.6, 44),
}

# Tablica 4.4N — c_min,dur [mm] dla stali zbrojeniowej; kolumny S1..S6.
TABLE_4_4N = {
    "X0": (10, 10, 10, 10, 15, 20),
    "XC1": (10, 10, 10, 15, 20, 25),
    "XC2/XC3": (10, 15, 20, 25, 30, 35),
    "XC4": (15, 20, 25, 30, 35, 40),
    "XD1/XS1": (20, 25, 30, 35, 40, 45),
    "XD2/XS2": (25, 30, 35, 40, 45, 50),
    "XD3/XS3": (30, 35, 40, 45, 50, 55),
}
EXPOSURE_GROUP = {
    "X0": "X0", "XC1": "XC1", "XC2": "XC2/XC3", "XC3": "XC2/XC3", "XC4": "XC4",
    "XD1": "XD1/XS1", "XS1": "XD1/XS1", "XD2": "XD2/XS2", "XS2": "XD2/XS2",
    "XD3": "XD3/XS3", "XS3": "XD3/XS3",
}
STRUCTURAL_CLASSES = ("S1", "S2", "S3", "S4", "S5", "S6")

# Tablica 7.2N — maksymalna średnica prętów φ*_s [mm] dla w_k = 0,4 / 0,3 / 0,2 mm
TABLE_7_2N = {
    160: (40, 32, 25), 200: (32, 25, 16), 240: (20, 16, 12), 280: (16, 12, 8),
    320: (12, 10, 6), 360: (10, 8, 5), 400: (8, 6, 4), 450: (6, 5, None),
}
# Tablica 7.3N — maksymalny rozstaw prętów [mm] dla w_k = 0,4 / 0,3 / 0,2 mm
TABLE_7_3N = {
    160: (300, 300, 200), 200: (300, 250, 150), 240: (250, 200, 100),
    280: (200, 150, 50), 320: (150, 100, None), 360: (100, 50, None),
}

# Tablica 10.2 — minimalna wartość a1 [mm]; kolumny: σEd/fcd ≤ 0,15 / 0,15–0,4 / > 0,4
TABLE_10_2 = {
    "line": (25, 30, 40),          # podparcia liniowe (stropy, dachy)
    "ribbed": (55, 70, 80),        # stropy żebrowe i płatwie
    "concentrated": (90, 110, 140),  # podparcia skupione (belki)
}

# EN 1990 tabl. A1.1 — (ψ0, ψ1, ψ2), wartości zalecane
PSI_TABLE = {
    "Q_A": ("Kat. A — mieszkalne", 0.7, 0.5, 0.3),
    "Q_B": ("Kat. B — biurowe", 0.7, 0.5, 0.3),
    "Q_C": ("Kat. C — zebrań", 0.7, 0.7, 0.6),
    "Q_D": ("Kat. D — handlowe", 0.7, 0.7, 0.6),
    "Q_E": ("Kat. E — magazynowe", 1.0, 0.9, 0.8),
    "Q_F": ("Kat. F — ruch pojazdów ≤ 30 kN", 0.7, 0.7, 0.6),
    "Q_G": ("Kat. G — ruch pojazdów 30–160 kN", 0.7, 0.5, 0.3),
    "Q_H": ("Kat. H — dachy", 0.0, 0.0, 0.0),
    "S": ("Śnieg (H ≤ 1000 m n.p.m.)", 0.5, 0.2, 0.0),
    "S_H": ("Śnieg (H > 1000 m n.p.m.)", 0.7, 0.5, 0.2),
    "W": ("Wiatr", 0.6, 0.2, 0.0),
    "T": ("Temperatura (nie pożarowa)", 0.6, 0.5, 0.0),
}

TABLE_8_1N_NOTE = "Tabl. 8.1N: φ_m,min = 4φ (φ ≤ 16 mm), 7φ (φ > 16 mm) — odgięcia, haki, pętle."

EDITIONS: dict[str, Edition] = {
    "EC2-2004-PL": Edition(
        id="EC2-2004-PL",
        title="PN-EN 1992-1-1:2008 + AC:2010 + NA:2010 (EN 1992-1-1:2004, 1. generacja)",
        implemented=True,
        params={p.key: p for p in _EC2_2004_PARAMS},
        tables={"3.1": TABLE_3_1, "4.4N": TABLE_4_4N, "7.2N": TABLE_7_2N, "7.3N": TABLE_7_3N,
                "10.2": TABLE_10_2, "psi": PSI_TABLE},
        description="Pełna implementacja: 6.5 (STM), zał. J.3, rozdz. 8, wybrane przepisy rozdz. 4, 6.2, "
                    "6.7, 7.3, 9.2, 10.9.5.",
    ),
    "EC2-2023": Edition(
        id="EC2-2023",
        title="EN 1992-1-1:2023 (2. generacja) — NIEZAIMPLEMENTOWANA",
        implemented=False,
        description="Szkielet do przyszłej implementacji. Parametry 2. generacji nie są dostępne; "
                    "program nie przenosi do niej wymagań 1. generacji.",
    ),
}


class ParameterSet:
    """Zestaw parametrów normowych dla jednej edycji z nadpisaniami projektu."""

    def __init__(self, edition: Edition, normative: NormativeInput):
        if not edition.implemented:
            raise EditionNotImplemented(
                f"Edycja '{edition.title}' nie jest zaimplementowana — obliczenia niemożliwe.")
        self.edition = edition
        self.input = normative
        self.used: set[str] = set()
        self._values: dict[str, float] = {k: p.value for k, p in edition.params.items()}
        for k, v in normative.overrides.items():
            if k not in edition.params:
                raise KeyError(f"Parametr '{k}' nie należy do edycji {edition.id}")
            if not edition.params[k].editable:
                raise ValueError(f"Parametr '{k}' nie jest edytowalny")
            self._values[k] = float(v)

    @property
    def edition_id(self) -> str:
        return self.edition.id

    def v(self, key: str) -> float:
        if key not in self._values:
            raise KeyError(f"Brak parametru '{key}' w edycji {self.edition.id}")
        self.used.add(key)
        return self._values[key]

    def param(self, key: str) -> NormParam:
        return self.edition.params[key]

    def is_overridden(self, key: str) -> bool:
        return key in self.input.overrides

    def is_confirmed(self, key: str) -> bool:
        """Czy parametr może być stosowany do wyniku pozytywnego."""
        p = self.edition.params[key]
        if p.blocking:
            return key in self.input.confirmed_params
        return True

    def table(self, name: str):
        return self.edition.tables[name]

    def require(self, edition_id: str) -> None:
        if self.edition.id != edition_id:
            raise EditionNotImplemented(
                f"Moduł obliczeniowy obsługuje edycję {edition_id}, a wybrano {self.edition.id}.")

    def describe(self, key: str) -> dict:
        p = self.edition.params[key]
        return {
            "key": key, "symbol": p.symbol, "value": self._values[key], "unit": p.unit,
            "clause": p.clause, "category": CATEGORY_LABEL[p.category], "recommended": p.recommended,
            "status": ("nadpisana przez użytkownika: " + self.input.override_notes.get(key, "—"))
            if self.is_overridden(key) else p.status,
            "na_note": p.na_note, "description": p.description, "blocking": p.blocking,
            "confirmed": self.is_confirmed(key),
        }

    def ndp_unconfirmed(self) -> bool:
        return not self.input.ndp_confirmed


def get_parameter_set(normative: NormativeInput) -> ParameterSet:
    if normative.edition not in EDITIONS:
        raise EditionNotImplemented(f"Nieznana edycja normy: {normative.edition}")
    return ParameterSet(EDITIONS[normative.edition], normative)


SUPPORTED_EDITION = "EC2-2004-PL"
