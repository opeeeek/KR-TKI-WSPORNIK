"""Ogólny solver płaskiej kratownicy przegubowej dla modeli Strut-and-Tie.

Metoda: macierz równowagi węzłów ``A·f = −P`` (f — siły w prętach, dodatnie
przy rozciąganiu, oraz reakcje podporowe). Analiza rzędu (SVD) rozstrzyga:

* układ statycznie wyznaczalny i geometrycznie niezmienny → rozwiązanie
  wprost z równowagi;
* układ statycznie niewyznaczalny (niezmienny) → metoda sztywności przy
  jawnie podanych sztywnościach osiowych EA (wynik zależy od sztywności —
  zgłaszane ostrzeżenie);
* mechanizm (rank(A) < liczba równań) → model ZMIENNY geometrycznie —
  wynik pozytywny jest blokowany.

Po rozwiązaniu wyznaczane są residua równowagi każdego węzła oraz globalna
równowaga sił i momentów.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


class StmModelError(ValueError):
    pass


@dataclass
class TrussNode:
    id: str
    x: float
    y: float


@dataclass
class TrussMember:
    id: str
    n1: str
    n2: str
    kind: str = "any"        # strut | tie | any
    EA: float | None = None  # sztywność osiowa [N] (tylko dla układów niewyznaczalnych)


@dataclass
class TrussSupport:
    node: str
    ux: bool = True
    uy: bool = True


@dataclass
class TrussLoad:
    node: str
    Fx: float = 0.0
    Fy: float = 0.0


@dataclass
class TrussModel:
    nodes: list[TrussNode] = field(default_factory=list)
    members: list[TrussMember] = field(default_factory=list)
    supports: list[TrussSupport] = field(default_factory=list)
    loads: list[TrussLoad] = field(default_factory=list)

    def node(self, nid: str) -> TrussNode:
        for n in self.nodes:
            if n.id == nid:
                return n
        raise KeyError(nid)


@dataclass
class TrussSolution:
    forces: dict[str, float]                 # N (+ rozciąganie)
    reactions: dict[str, tuple[float, float]]
    status: str                              # determinate | indeterminate | mechanism | error
    method: str                              # equilibrium | stiffness | none
    rank: int
    n_equations: int
    n_unknowns: int
    degree: int                              # stopień statycznej niewyznaczalności (m + r − 2j)
    node_residuals: dict[str, float]
    max_residual: float
    global_residual: tuple[float, float, float]  # ΣFx, ΣFy, ΣM (względem 0,0)
    tolerance: float
    messages: list[str] = field(default_factory=list)

    @property
    def stable(self) -> bool:
        return self.status in ("determinate", "indeterminate")

    @property
    def equilibrium_ok(self) -> bool:
        return (self.stable and self.max_residual <= self.tolerance
                and max(abs(v) for v in self.global_residual[:2]) <= self.tolerance
                and abs(self.global_residual[2]) <= self.tolerance * self._lever)

    _lever: float = 1.0


def _validate(model: TrussModel) -> dict[str, int]:
    ids = [n.id for n in model.nodes]
    if len(set(ids)) != len(ids):
        raise StmModelError("Powtórzone identyfikatory węzłów.")
    idx = {nid: i for i, nid in enumerate(ids)}
    mids = [m.id for m in model.members]
    if len(set(mids)) != len(mids):
        raise StmModelError("Powtórzone identyfikatory prętów.")
    for m in model.members:
        if m.n1 not in idx or m.n2 not in idx:
            raise StmModelError(f"Pręt {m.id}: nieistniejący węzeł.")
        if m.n1 == m.n2:
            raise StmModelError(f"Pręt {m.id}: oba końce w tym samym węźle.")
        a, b = model.nodes[idx[m.n1]], model.nodes[idx[m.n2]]
        if math.hypot(b.x - a.x, b.y - a.y) < 1e-6:
            raise StmModelError(f"Pręt {m.id}: zerowa długość.")
    for s in model.supports:
        if s.node not in idx:
            raise StmModelError(f"Podpora w nieistniejącym węźle {s.node}.")
    for ld in model.loads:
        if ld.node not in idx:
            raise StmModelError(f"Obciążenie w nieistniejącym węźle {ld.node}.")
        if not (math.isfinite(ld.Fx) and math.isfinite(ld.Fy)):
            raise StmModelError("Nieskończona wartość obciążenia.")
    return idx


def _equilibrium_matrix(model: TrussModel, idx: dict[str, int]):
    nn = len(model.nodes)
    m = len(model.members)
    rdofs: list[tuple[str, int]] = []
    for s in model.supports:
        if s.ux:
            rdofs.append((s.node, 0))
        if s.uy:
            rdofs.append((s.node, 1))
    A = np.zeros((2 * nn, m + len(rdofs)))
    for k, mem in enumerate(model.members):
        i, j = idx[mem.n1], idx[mem.n2]
        a, b = model.nodes[i], model.nodes[j]
        L = math.hypot(b.x - a.x, b.y - a.y)
        cx, cy = (b.x - a.x) / L, (b.y - a.y) / L
        # siła rozciągająca ciągnie węzeł i w kierunku j
        A[2 * i, k] += cx
        A[2 * i + 1, k] += cy
        A[2 * j, k] -= cx
        A[2 * j + 1, k] -= cy
    for r, (nid, dof) in enumerate(rdofs):
        A[2 * idx[nid] + dof, m + r] = 1.0
    P = np.zeros(2 * nn)
    for ld in model.loads:
        P[2 * idx[ld.node]] += ld.Fx
        P[2 * idx[ld.node] + 1] += ld.Fy
    return A, P, rdofs


def solve(model: TrussModel, rel_tol: float = 1e-9) -> TrussSolution:
    idx = _validate(model)
    A, P, rdofs = _equilibrium_matrix(model, idx)
    n_eq, n_unk = A.shape
    m = len(model.members)
    scale = max(1.0, float(np.max(np.abs(P))) if P.size else 1.0)
    tol = rel_tol * scale * 1e3  # tolerancja residuum [N]
    xs = [n.x for n in model.nodes]
    ys = [n.y for n in model.nodes]
    lever = max(1.0, max(xs) - min(xs), max(ys) - min(ys))
    if n_unk == 0:
        rank = 0
    else:
        sv = np.linalg.svd(A, compute_uv=False)
        rank = int(np.sum(sv > 1e-10 * max(1.0, sv[0])))
    degree = n_unk - n_eq
    msgs: list[str] = []
    f = np.zeros(n_unk)
    method = "none"
    if rank < n_eq:
        status = "mechanism"
        # sprawdzenie, czy obciążenie jest zgodne z mechanizmem (informacyjnie)
        if n_unk:
            f, *_ = np.linalg.lstsq(A, -P, rcond=None)
        res = A @ f + P
        if float(np.max(np.abs(res))) > tol:
            msgs.append("Model ZMIENNY geometrycznie (mechanizm) — obciążenie nie może zostać zrównoważone.")
        else:
            msgs.append("Model ZMIENNY geometrycznie (mechanizm) — równowaga istnieje tylko dla bieżącego "
                        "układu obciążeń; model niedopuszczalny do weryfikacji.")
        method = "lstsq"
    elif rank == n_unk:
        status = "determinate"
        f = np.linalg.solve(A, -P) if n_eq == n_unk else np.linalg.lstsq(A, -P, rcond=None)[0]
        method = "equilibrium"
    else:
        status = "indeterminate"
        msgs.append(f"Model statycznie niewyznaczalny (stopień {n_unk - rank}) — siły wyznaczono metodą "
                    "sztywności; wynik zależy od przyjętych sztywności EA.")
        f = _solve_stiffness(model, idx, rdofs, P)
        method = "stiffness"
    res = A @ f + P
    node_res = {model.nodes[i].id: float(math.hypot(res[2 * i], res[2 * i + 1])) for i in range(len(model.nodes))}
    forces = {mem.id: float(f[k]) for k, mem in enumerate(model.members)}
    reactions: dict[str, tuple[float, float]] = {}
    for r, (nid, dof) in enumerate(rdofs):
        rx, ry = reactions.get(nid, (0.0, 0.0))
        if dof == 0:
            rx += float(f[m + r])
        else:
            ry += float(f[m + r])
        reactions[nid] = (rx, ry)
    # równowaga globalna (obciążenia + reakcje)
    sfx = sum(ld.Fx for ld in model.loads) + sum(r[0] for r in reactions.values())
    sfy = sum(ld.Fy for ld in model.loads) + sum(r[1] for r in reactions.values())
    smz = 0.0
    for ld in model.loads:
        n = model.nodes[idx[ld.node]]
        smz += n.x * ld.Fy - n.y * ld.Fx
    for nid, (rx, ry) in reactions.items():
        n = model.nodes[idx[nid]]
        smz += n.x * ry - n.y * rx
    sol = TrussSolution(forces, reactions, status, method, rank, n_eq, n_unk, degree, node_res,
                        float(max(node_res.values()) if node_res else 0.0), (sfx, sfy, smz), tol, msgs)
    sol._lever = lever
    if status != "mechanism" and sol.max_residual > tol:
        sol.messages.append(f"Residuum równowagi {sol.max_residual:.3e} N przekracza tolerancję {tol:.3e} N.")
    return sol


def _solve_stiffness(model: TrussModel, idx, rdofs, P) -> np.ndarray:
    nn = len(model.nodes)
    m = len(model.members)
    K = np.zeros((2 * nn, 2 * nn))
    geom = []
    for mem in model.members:
        if mem.EA is None or mem.EA <= 0:
            raise StmModelError(f"Model niewyznaczalny: pręt {mem.id} wymaga dodatniej sztywności EA.")
        i, j = idx[mem.n1], idx[mem.n2]
        a, b = model.nodes[i], model.nodes[j]
        L = math.hypot(b.x - a.x, b.y - a.y)
        c, s = (b.x - a.x) / L, (b.y - a.y) / L
        k = mem.EA / L
        kl = k * np.array([[c * c, c * s], [c * s, s * s]])
        for (p, q), sgn in (((i, i), 1), ((j, j), 1), ((i, j), -1), ((j, i), -1)):
            K[2 * p:2 * p + 2, 2 * q:2 * q + 2] += sgn * kl
        geom.append((i, j, c, s, k))
    fixed = {2 * idx[nid] + dof for nid, dof in rdofs}
    free = [d for d in range(2 * nn) if d not in fixed]
    u = np.zeros(2 * nn)
    Kff = K[np.ix_(free, free)]
    u[free] = np.linalg.solve(Kff, P[free])
    f = np.zeros(m + len(rdofs))
    for k_, (i, j, c, s, k) in enumerate(geom):
        du = (u[2 * j] - u[2 * i]) * c + (u[2 * j + 1] - u[2 * i + 1]) * s
        f[k_] = k * du
    R = K @ u - P
    for r, (nid, dof) in enumerate(rdofs):
        f[m + r] = R[2 * idx[nid] + dof]
    return f
