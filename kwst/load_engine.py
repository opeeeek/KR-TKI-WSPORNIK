"""Silnik obciążeń: kombinacje SGN/SGU wg EN 1990, wartości obliczeniowe na wsporniku.

Zasady bezpieczeństwa danych:
* oddziaływania mają jawny charakter: ``characteristic`` albo ``design``;
* współczynniki częściowe γ stosuje się WYŁĄCZNIE do wartości charakterystycznych;
* wartości obliczeniowe (``design``) wchodzą do kombinacji typu ``ULS_DIRECT``
  z mnożnikiem 1,0 — każda inna konfiguracja jest odrzucana jako ryzyko
  podwójnego zastosowania współczynników;
* minimalna siła pozioma H_min = k·V_Ed jest stosowana tylko jako świadome
  założenie użytkownika z podanym źródłem.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from .core.model import LoadAction, LoadCombination, LoadsInput, GeometryInput, active_sides
from .core.results import Message, Level
from .normative_parameters import ParameterSet, PSI_TABLE

CATEGORIES = {
    "G": "Stałe (G)",
    **{k: v[0] for k, v in PSI_TABLE.items()},
    "A": "Wyjątkowe (A)",
}
SOURCES = {
    "beam_reaction": "Reakcja belki prefabrykowanej",
    "support_reaction": "Reakcja podparcia elementu",
    "point": "Siła skupiona",
    "other": "Inne",
}
COMB_KINDS = {
    "ULS": "SGN — trwała/przejściowa",
    "ULS_ACC": "SGN — wyjątkowa",
    "ULS_DIRECT": "SGN — wartości obliczeniowe podane bezpośrednio",
    "SLS_QP": "SGU — quasi-stała",
    "SLS_CHAR": "SGU — charakterystyczna",
}


class LoadError(ValueError):
    pass


@dataclass
class SideActions:
    side: str
    V: float = 0.0
    H: float = 0.0
    M: float = 0.0          # suma momentów (wraz z V·e_x) [N·mm]
    e_y_moment: float = 0.0  # Σ V·e_y
    H_min_applied: bool = False

    @property
    def e_x(self) -> float:
        """Mimośród podłużny wypadkowej (łącznie z M) względem a_c."""
        return self.M / self.V if self.V > 0 else 0.0

    @property
    def e_y(self) -> float:
        return self.e_y_moment / self.V if self.V > 0 else 0.0


@dataclass
class DesignCombination:
    name: str
    kind: str
    factors: dict[str, float]
    description: str
    sides: dict[str, SideActions] = field(default_factory=dict)

    @property
    def is_uls(self) -> bool:
        return self.kind.startswith("ULS")

    @property
    def is_sls(self) -> bool:
        return self.kind.startswith("SLS")


def psi(category: str) -> tuple[float, float, float]:
    if category in PSI_TABLE:
        _, p0, p1, p2 = PSI_TABLE[category]
        return p0, p1, p2
    return 1.0, 1.0, 1.0


def generate_combinations(loads: LoadsInput, ps: ParameterSet) -> list[LoadCombination]:
    """Automatyczne kombinacje wg EN 1990 (6.10) lub (6.10a)/(6.10b), (6.14b), (6.16b)."""
    st = loads.settings
    chars = [a for a in loads.actions if a.nature == "characteristic"]
    designs = [a for a in loads.actions if a.nature == "design"]
    G = [a for a in chars if a.category == "G"]
    Q = [a for a in chars if a.category in PSI_TABLE]
    A = [a for a in chars if a.category == "A"]
    gG = st.gamma_G_sup
    gQ = st.gamma_Q
    xi = st.xi
    combos: list[LoadCombination] = []
    if G or Q:
        leads = Q if Q else [None]

        def facs(gfac: float, lead) -> dict[str, float]:
            f = {g.name: gfac for g in G}
            for q in Q:
                f[q.name] = gQ if q is lead else gQ * psi(q.category)[0]
            return f

        if st.method == "6.10":
            for lead in leads:
                tag = lead.name if lead is not None else "G"
                combos.append(LoadCombination(f"SGN {tag} (6.10)", "ULS", facs(gG, lead),
                                              "Σγ_G·G + γ_Q·Q_1 + Σγ_Q·ψ_0·Q_i"))
        else:
            combos.append(LoadCombination("SGN (6.10a)", "ULS",
                                          {**{g.name: gG for g in G},
                                           **{q.name: gQ * psi(q.category)[0] for q in Q}},
                                          "Σγ_G·G + Σγ_Q·ψ_0·Q_i"))
            for lead in leads:
                tag = lead.name if lead is not None else "G"
                combos.append(LoadCombination(f"SGN {tag} (6.10b)", "ULS", facs(xi * gG, lead),
                                              "Σξ·γ_G·G + γ_Q·Q_1 + Σγ_Q·ψ_0·Q_i"))
    for a in A:
        f = {g.name: 1.0 for g in G}
        f[a.name] = 1.0
        for q in Q:
            f[q.name] = psi(q.category)[1] if q is (Q[0] if Q else None) else psi(q.category)[2]
        combos.append(LoadCombination(f"SGN-W {a.name} (6.11b)", "ULS_ACC", f,
                                      "ΣG + A_d + ψ_1,1·Q_1 + Σψ_2,i·Q_i"))
    if designs:
        combos.append(LoadCombination("SGN — wartości obliczeniowe", "ULS_DIRECT",
                                      {d.name: 1.0 for d in designs},
                                      "Wartości obliczeniowe podane bezpośrednio (bez współczynników)"))
    if st.include_sls and (G or Q):
        combos.append(LoadCombination("SGU quasi-stała (6.16b)", "SLS_QP",
                                      {**{g.name: 1.0 for g in G},
                                       **{q.name: psi(q.category)[2] for q in Q}},
                                      "ΣG + Σψ_2,i·Q_i"))
        if Q:
            combos.append(LoadCombination("SGU charakterystyczna (6.14b)", "SLS_CHAR",
                                          {**{g.name: 1.0 for g in G},
                                           **{q.name: (1.0 if i == 0 else psi(q.category)[0])
                                              for i, q in enumerate(Q)}},
                                          "ΣG + Q_1 + Σψ_0,i·Q_i"))
    return combos


def validate_combination(c: LoadCombination, actions: dict[str, LoadAction]) -> list[Message]:
    msgs: list[Message] = []
    for name, f in c.factors.items():
        if name not in actions:
            msgs.append(Message(Level.ERROR, f"Kombinacja '{c.name}': nieznane oddziaływanie '{name}'.", c.name))
            continue
        a = actions[name]
        if a.nature == "design":
            if c.kind != "ULS_DIRECT":
                msgs.append(Message(Level.ERROR,
                                    f"Kombinacja '{c.name}' ({c.kind}) zawiera wartość OBLICZENIOWĄ '{name}' — "
                                    "niedopuszczalne ponowne stosowanie współczynników częściowych.", c.name))
            elif abs(f - 1.0) > 1e-12:
                msgs.append(Message(Level.ERROR,
                                    f"Kombinacja '{c.name}': wartość obliczeniowa '{name}' z mnożnikiem {f} ≠ 1,0 "
                                    "— ryzyko podwójnego stosowania współczynników.", c.name))
        else:
            if c.kind == "ULS_DIRECT":
                msgs.append(Message(Level.ERROR,
                                    f"Kombinacja '{c.name}' (wartości obliczeniowe) zawiera oddziaływanie "
                                    f"charakterystyczne '{name}'.", c.name))
        if f < 0:
            msgs.append(Message(Level.ERROR, f"Kombinacja '{c.name}': ujemny mnożnik dla '{name}'.", c.name))
    return msgs


def evaluate_combinations(loads: LoadsInput, geo: GeometryInput, ps: ParameterSet
                          ) -> tuple[list[DesignCombination], list[Message], list[str]]:
    """Zwraca listę kombinacji z sumarycznymi oddziaływaniami na każdą stronę wspornika."""
    msgs: list[Message] = []
    assumptions: list[str] = []
    names = [a.name for a in loads.actions]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        msgs.append(Message(Level.ERROR, f"Powtórzone nazwy oddziaływań: {', '.join(sorted(dup))}."))
    actions = {a.name: a for a in loads.actions}
    sides = active_sides(geo)
    for a in loads.actions:
        if a.side not in ("R", "L"):
            msgs.append(Message(Level.ERROR, f"Oddziaływanie '{a.name}': nieznana strona '{a.side}'."))
        elif a.side not in sides:
            msgs.append(Message(Level.WARNING,
                                f"Oddziaływanie '{a.name}' przypisane do strony {a.side}, której nie ma w układzie "
                                "jednostronnym — pominięte."))
        if a.nature not in ("characteristic", "design"):
            msgs.append(Message(Level.ERROR, f"Oddziaływanie '{a.name}': nieznany charakter '{a.nature}'."))
        if a.nature == "characteristic" and a.category not in CATEGORIES:
            msgs.append(Message(Level.ERROR, f"Oddziaływanie '{a.name}': nieznana kategoria '{a.category}'."))
    if loads.combination_mode == "manual":
        combos = list(loads.combinations)
        assumptions.append("Kombinacje obciążeń zdefiniowane ręcznie przez użytkownika.")
    else:
        combos = generate_combinations(loads, ps)
        st = loads.settings
        assumptions.append(
            f"Kombinacje SGN generowane automatycznie wg EN 1990 wzór {'(6.10)' if st.method == '6.10' else '(6.10a)/(6.10b)'}"
            f"; γ_G,sup = {st.gamma_G_sup}, γ_Q = {st.gamma_Q}, ξ = {st.xi}; ψ wg EN 1990 tabl. A1.1 "
            "(wartości zalecane — zgodność z NA do potwierdzenia). Oddziaływania stałe przyjęto jako niekorzystne.")
    out: list[DesignCombination] = []
    for c in combos:
        msgs += validate_combination(c, actions)
        dc = DesignCombination(c.name, c.kind, dict(c.factors), c.note or COMB_KINDS.get(c.kind, c.kind))
        for sd in sides:
            sa = SideActions(sd)
            for name, f in c.factors.items():
                a = actions.get(name)
                if a is None or a.side != sd:
                    continue
                sa.V += f * a.V
                sa.H += f * a.H
                sa.M += f * (a.M + a.V * a.e_x)
                sa.e_y_moment += f * a.V * a.e_y
            st = loads.settings
            if st.H_min_enabled and dc.is_uls and sa.V > 0:
                h_min = st.H_min_ratio * sa.V
                if sa.H < h_min:
                    sa.H = h_min
                    sa.H_min_applied = True
            dc.sides[sd] = sa
        out.append(dc)
    st = loads.settings
    if st.H_min_enabled:
        src = st.H_min_source.strip()
        if not src:
            msgs.append(Message(Level.ERROR, "Włączono minimalną siłę poziomą H_min bez wskazania źródła/uzasadnienia "
                                             "— wymagane jawne wskazanie podstawy założenia."))
        assumptions.append(f"Założenie użytkownika: H_Ed ≥ {st.H_min_ratio:.3g}·V_Ed w kombinacjach SGN. "
                           f"Źródło: {src or 'BRAK'}. Nie jest to wymaganie EN 1992-1-1.")
    if not any(d.is_uls for d in out):
        msgs.append(Message(Level.ERROR, "Brak kombinacji SGN — brak danych do wymiarowania."))
    return out, msgs, assumptions


# ---------------------------------------------------------------------------
# Import obciążeń
# ---------------------------------------------------------------------------
IMPORT_COLUMNS = ["name", "side", "category", "nature", "source", "V_kN", "H_kN", "M_kNm", "e_x_mm", "e_y_mm", "note"]


def _row_to_action(row: dict) -> LoadAction:
    def num(key: str) -> float:
        v = row.get(key, "")
        if v is None or str(v).strip() == "":
            return 0.0
        return float(str(v).replace(",", "."))
    name = str(row.get("name", "")).strip()
    if not name:
        raise LoadError("Brak nazwy oddziaływania w wierszu importu.")
    nature = str(row.get("nature") or "characteristic").strip()
    if nature not in ("characteristic", "design"):
        raise LoadError(f"'{name}': nieprawidłowy charakter '{nature}' (characteristic|design).")
    return LoadAction(name=name, side=str(row.get("side") or "R").strip().upper(),
                      category=str(row.get("category") or "G").strip(), nature=nature,
                      source=str(row.get("source") or "other").strip(),
                      V=num("V_kN") * 1e3, H=num("H_kN") * 1e3, M=num("M_kNm") * 1e6,
                      e_x=num("e_x_mm"), e_y=num("e_y_mm"), note=str(row.get("note") or ""))


def import_actions_csv(text: str) -> list[LoadAction]:
    """Import z CSV (separator ; lub ,). Kolumny: :data:`IMPORT_COLUMNS`. Jednostki: kN, kNm, mm."""
    sample = text[:2048]
    delim = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    if reader.fieldnames is None or "name" not in [f.strip() for f in reader.fieldnames]:
        raise LoadError("Plik CSV musi zawierać nagłówek z kolumną 'name'. Wymagane kolumny: "
                        + ", ".join(IMPORT_COLUMNS))
    out = []
    for row in reader:
        row = {k.strip(): v for k, v in row.items() if k}
        if not any(str(v).strip() for v in row.values() if v is not None):
            continue
        out.append(_row_to_action(row))
    return out


def import_actions_excel(path: str) -> list[LoadAction]:
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise LoadError("Pusty arkusz.")
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    if "name" not in header:
        raise LoadError("Arkusz musi zawierać nagłówek z kolumną 'name'.")
    out = []
    for r in rows[1:]:
        if r is None or all(v is None or str(v).strip() == "" for v in r):
            continue
        out.append(_row_to_action(dict(zip(header, r))))
    return out


def export_actions_csv(actions: list[LoadAction]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(IMPORT_COLUMNS)
    for a in actions:
        w.writerow([a.name, a.side, a.category, a.nature, a.source, f"{a.V / 1e3:.4g}", f"{a.H / 1e3:.4g}",
                    f"{a.M / 1e6:.4g}", f"{a.e_x:.4g}", f"{a.e_y:.4g}", a.note])
    return buf.getvalue()
