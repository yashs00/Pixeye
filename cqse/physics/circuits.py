"""DC circuits from a netlist: the computer writes, solves AND proves the equations.

Formal state (kind = "circuit_dc"):
{
  "kind": "circuit_dc",
  "components": [
    {"id": "V1", "type": "vsource",  "value": "12", "unit": "V",   "nodes": ["A", "G"]},   # nodes[0] is +
    {"id": "R1", "type": "resistor", "value": "2",  "unit": "ohm", "nodes": ["A", "B"]},
    {"id": "R2", "type": "resistor", "value": "3",  "unit": "ohm", "nodes": ["B", "G"]},
    {"id": "R3", "type": "resistor", "value": "6",  "unit": "ohm", "nodes": ["B", "G"]},
    {"id": "C1", "type": "capacitor","value": "2",  "unit": "uF",  "nodes": ["B", "G"]}
  ],
  "target": {"quantity": "current|voltage|power|charge|energy|equivalent_resistance",
             "element": "R2"            # or "terminals": ["A", "G"] for equivalent_resistance
            }
}
Types: resistor, vsource (ideal battery, nodes[0] = positive terminal), isource (current flows
from nodes[0] through the source to nodes[1]), capacitor (open in DC steady state), inductor
(short in DC steady state, ideal). Magnitudes are asked, so no sign-convention ambiguity.

Verification:
  primary      Modified Nodal Analysis, exact rationals.
  uniqueness   MNA matrix must be non-singular (floating nodes, source loops, series
               capacitors with undefined charge -> FAILED, never guessed).
  certificate  separately coded check that the solution satisfies KCL at EVERY node and the
               element law of EVERY component, plus Tellegen power balance. A solution that
               passes all of these for a non-singular network IS the circuit's unique solution.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord, guarded
from cqse.generic.system import unit_info
from cqse.math.expr import parse

TOOL = f"cqse-circuits 0.1; sympy {sp.__version__}"
EXPECTED_UNIT = {"resistor": "ohm", "vsource": "V", "isource": "A", "capacitor": "F", "inductor": "H"}
QUANTITY_UNIT = {"current": "A", "voltage": "V", "power": "W", "charge": "C", "energy": "J",
                 "equivalent_resistance": "ohm"}


class CircuitError(ValueError):
    pass


@dataclass
class Comp:
    id: str
    type: str
    value: sp.Rational  # SI
    a: str
    b: str


@dataclass
class Circuit:
    comps: list[Comp]
    nodes: list[str]
    ground: str


def parse_circuit(formal: dict) -> Circuit:
    comps, seen = [], set()
    for c in formal.get("components", []):
        cid, typ = c.get("id", ""), c.get("type", "")
        if not cid or cid in seen:
            raise CircuitError(f"missing or duplicate component id {cid!r}")
        seen.add(cid)
        if typ not in EXPECTED_UNIT:
            raise CircuitError(f"{cid}: unknown component type {typ!r}")
        nodes = c.get("nodes", [])
        if len(nodes) != 2 or nodes[0] == nodes[1]:
            raise CircuitError(f"{cid}: needs two different nodes")
        factor, dim = unit_info(c.get("unit", EXPECTED_UNIT[typ]))
        _, want = unit_info(EXPECTED_UNIT[typ])
        if sp.expand(dim - want) != 0:
            raise CircuitError(f"{cid}: unit {c.get('unit')!r} is not a unit of {typ}")
        v = sp.nsimplify(parse(str(c["value"])), rational=True) * factor
        if not v.is_number or (typ in ("resistor", "capacitor", "inductor") and not v.is_positive):
            raise CircuitError(f"{cid}: value must be a positive number")
        comps.append(Comp(cid, typ, sp.nsimplify(v, rational=True), str(nodes[0]), str(nodes[1])))
    if not comps:
        raise CircuitError("empty circuit")
    nodes = sorted({n for c in comps for n in (c.a, c.b)})
    ground = formal.get("ground") or ("G" if "G" in nodes else nodes[0])
    if ground not in nodes:
        raise CircuitError("ground node not in circuit")
    # connectivity
    adj = {n: set() for n in nodes}
    for c in comps:
        adj[c.a].add(c.b)
        adj[c.b].add(c.a)
    stack, reach = [ground], {ground}
    while stack:
        for nb in adj[stack.pop()] - reach:
            reach.add(nb)
            stack.append(nb)
    if reach != set(nodes):
        raise CircuitError(f"circuit is not connected: {sorted(set(nodes) - reach)} unreachable")
    return Circuit(comps, nodes, ground)


@dataclass
class DCSolution:
    V: dict[str, sp.Rational]               # node potentials (ground = 0)
    I: dict[str, sp.Rational]               # current through each component, from nodes[0] to nodes[1]


def solve_mna(ckt: Circuit) -> DCSolution:
    """Exact MNA. Capacitors open; inductors are 0 V sources. Raises on singular networks."""
    nn = [n for n in ckt.nodes if n != ckt.ground]
    idx = {n: i for i, n in enumerate(nn)}
    vs = [c for c in ckt.comps if c.type in ("vsource", "inductor")]
    N = len(nn) + len(vs)
    A = sp.zeros(N, N)
    z = sp.zeros(N, 1)

    def stamp(r, c_, val):
        if r is not None and c_ is not None:
            A[r, c_] += val

    for c in ckt.comps:
        ia, ib = idx.get(c.a), idx.get(c.b)
        if c.type == "resistor":
            g = 1 / c.value
            stamp(ia, ia, g); stamp(ib, ib, g); stamp(ia, ib, -g); stamp(ib, ia, -g)
        elif c.type == "isource":   # current leaves node a through the source into node b
            if ia is not None:
                z[ia] -= c.value
            if ib is not None:
                z[ib] += c.value
    for k, c in enumerate(vs):
        row = len(nn) + k
        ia, ib = idx.get(c.a), idx.get(c.b)
        # extra unknown: current through the source from a to b (internally)
        if ia is not None:
            A[ia, row] += 1; A[row, ia] += 1
        if ib is not None:
            A[ib, row] -= 1; A[row, ib] -= 1
        z[row] = c.value if c.type == "vsource" else 0
    if N == 0:
        raise CircuitError("nothing to solve")
    if A.rank() < N:
        raise CircuitError("network is singular: a floating node (e.g. only capacitors), a loop of ideal "
                           "voltage sources/inductors, or a cut-set of current sources - the question is "
                           "ill-posed or needs charge analysis")
    x = A.LUsolve(z)
    V = {ckt.ground: sp.Integer(0)}
    V.update({n: sp.nsimplify(x[idx[n]]) for n in nn})
    I: dict[str, sp.Rational] = {}
    for k, c in enumerate(vs):
        # The MNA unknown is the current leaving node a INTO the source, i.e. through it from a to b
        # (negative for a battery that is delivering power). Verified by certify().
        I[c.id] = sp.nsimplify(x[len(nn) + k])
    for c in ckt.comps:
        if c.type == "resistor":
            I[c.id] = (V[c.a] - V[c.b]) / c.value
        elif c.type == "isource":
            I[c.id] = c.value
        elif c.type == "capacitor":
            I[c.id] = sp.Integer(0)
    return DCSolution(V, I)


def certify(ckt: Circuit, sol: DCSolution) -> list[str]:
    """Independent check: KCL at every node + every element law + Tellegen. Returns problems."""
    probs = []
    for n in ckt.nodes:
        out = sum((sol.I[c.id] for c in ckt.comps if c.a == n), sp.Integer(0)) - \
              sum((sol.I[c.id] for c in ckt.comps if c.b == n), sp.Integer(0))
        if sp.simplify(out) != 0:
            probs.append(f"KCL fails at node {n}: net outflow {out}")
    for c in ckt.comps:
        vab = sol.V[c.a] - sol.V[c.b]
        if c.type == "resistor" and sp.simplify(vab - sol.I[c.id] * c.value) != 0:
            probs.append(f"Ohm's law fails for {c.id}")
        if c.type == "vsource" and sp.simplify(vab - c.value) != 0:
            probs.append(f"{c.id} terminal voltage {vab} != {c.value}")
        if c.type == "inductor" and sp.simplify(vab) != 0:
            probs.append(f"{c.id} (ideal inductor, DC) has voltage {vab}")
        if c.type == "isource" and sp.simplify(sol.I[c.id] - c.value) != 0:
            probs.append(f"{c.id} current mismatch")
        if c.type == "capacitor" and sol.I[c.id] != 0:
            probs.append(f"{c.id} carries DC current")
    # Tellegen: sum of power absorbed (V_ab * I_ab, passive convention) over all elements is 0
    tel = sum(((sol.V[c.a] - sol.V[c.b]) * sol.I[c.id] for c in ckt.comps), sp.Integer(0))
    if sp.simplify(tel) != 0:
        probs.append(f"Tellegen power balance fails: {tel}")
    return probs


def evaluate_target(ckt: Circuit, sol: DCSolution, target: dict) -> sp.Expr:
    q = target.get("quantity")
    if q == "equivalent_resistance":
        raise CircuitError("equivalent_resistance handled separately")
    el = next((c for c in ckt.comps if c.id == target.get("element")), None)
    if el is None:
        raise CircuitError(f"target element {target.get('element')!r} not in circuit")
    vab = sol.V[el.a] - sol.V[el.b]
    if q == "current":
        return sp.Abs(sol.I[el.id])
    if q == "voltage":
        return sp.Abs(vab)
    if q == "power":
        if el.type != "resistor":
            raise CircuitError("power is asked only for resistors (dissipated power)")
        return sp.simplify(sol.I[el.id] ** 2 * el.value)
    if q in ("charge", "energy"):
        if el.type != "capacitor":
            raise CircuitError(f"{q} is asked only for capacitors")
        return sp.Abs(el.value * vab) if q == "charge" else el.value * vab ** 2 / 2
    raise CircuitError(f"unknown target quantity {q!r}")


def equivalent_resistance(formal: dict) -> sp.Expr:
    """Resistors only between terminals: inject 1 A test current, R = V/1."""
    ckt = parse_circuit(formal)
    if any(c.type != "resistor" for c in ckt.comps):
        raise CircuitError("equivalent resistance questions must contain resistors only")
    a, b = formal["target"]["terminals"]
    test = Circuit(ckt.comps + [Comp("_TEST", "isource", sp.Integer(1), b, a)], ckt.nodes, b)
    sol = solve_mna(test)
    if certify(test, sol):
        raise CircuitError("certificate failed for equivalent-resistance solve")
    return sp.simplify(sol.V[a] - sol.V[b])


def equivalent_resistance_reduction(formal: dict) -> Optional[sp.Expr]:
    """Independent method for Req: repeated series/parallel reduction (None if not reducible,
    e.g. a bridge)."""
    edges = [[c["nodes"][0], c["nodes"][1], sp.nsimplify(parse(str(c["value"])), rational=True)
              * unit_info(c.get("unit", "ohm"))[0]] for c in formal["components"]]
    a, b = formal["target"]["terminals"]
    changed = True
    while changed:
        changed = False
        # parallel: same unordered node pair
        groups: dict[frozenset, list[int]] = {}
        for i, (x, y, _) in enumerate(edges):
            groups.setdefault(frozenset((x, y)), []).append(i)
        for key, ids in groups.items():
            if len(ids) > 1:
                g = sum(1 / edges[i][2] for i in ids)
                x, y = tuple(key)
                edges = [e for i, e in enumerate(edges) if i not in ids] + [[x, y, 1 / g]]
                changed = True
                break
        if changed:
            continue
        # series: internal node (not a terminal) of degree 2
        deg: dict[str, list[int]] = {}
        for i, (x, y, _) in enumerate(edges):
            deg.setdefault(x, []).append(i)
            deg.setdefault(y, []).append(i)
        for n, ids in deg.items():
            if n in (a, b) or len(ids) != 2:
                continue
            e1, e2 = edges[ids[0]], edges[ids[1]]
            o1 = e1[1] if e1[0] == n else e1[0]
            o2 = e2[1] if e2[0] == n else e2[0]
            if o1 == o2:
                continue
            edges = [e for i, e in enumerate(edges) if i not in ids] + [[o1, o2, e1[2] + e2[2]]]
            changed = True
            break
        if changed:
            continue
        # dangling resistor (degree-1 non-terminal node) carries no current
        for n, ids in deg.items():
            if n not in (a, b) and len(ids) == 1:
                edges = [e for i, e in enumerate(edges) if i != ids[0]]
                changed = True
                break
    if len(edges) == 1 and {edges[0][0], edges[0][1]} == {a, b}:
        return sp.simplify(edges[0][2])
    return None


@dataclass
class CircuitResult:
    value: Optional[sp.Expr] = None
    unit: str = ""
    records: list[VerificationRecord] = field(default_factory=list)
    solution: Optional[DCSolution] = None


def solve_and_verify(formal: dict) -> CircuitResult:
    out = CircuitResult()
    st: dict = {}
    tgt = formal.get("target", {})
    q = tgt.get("quantity")

    def _parse():
        st["ckt"] = parse_circuit(formal)
        if q not in QUANTITY_UNIT:
            raise CircuitError(f"unknown target quantity {q!r}")
        return VerificationRecord(check_id="circuit.structure", status=CheckStatus.EXACT_CHECKED,
                                  method="netlist parse, units, connectivity", tool=TOOL,
                                  assumptions=["ideal sources and wires", "DC steady state",
                                               "capacitors open, inductors short"],
                                  result=f"{len(st['ckt'].comps)} components, {len(st['ckt'].nodes)} nodes")

    out.records.append(guarded("circuit.structure", _parse))
    if "ckt" not in st:
        return out
    ckt: Circuit = st["ckt"]
    out.unit = QUANTITY_UNIT[q]

    if q == "equivalent_resistance":
        def _req():
            st["val"] = equivalent_resistance(formal)
            return VerificationRecord(check_id="circuit.solve.primary", status=CheckStatus.EXACT_CHECKED,
                                      method="MNA with 1 A test source + KCL/Ohm certificate", tool=TOOL,
                                      result=f"Req = {st['val']} ohm")

        def _red():
            r = equivalent_resistance_reduction(formal)
            if r is None:
                return VerificationRecord(check_id="circuit.solve.independent", status=CheckStatus.NOT_APPLICABLE,
                                          method="series/parallel reduction", hard=False,
                                          result="network not series-parallel reducible (e.g. bridge); "
                                                 "certificate is the cross-check")
            ok = sp.simplify(r - st["val"]) == 0
            return VerificationRecord(check_id="circuit.solve.independent",
                                      status=CheckStatus.EXACT_CHECKED if ok else CheckStatus.UNRESOLVED,
                                      method="series/parallel reduction", tool=TOOL,
                                      result=f"reduction gives {r}; agreement={ok}")

        out.records.append(guarded("circuit.solve.primary", _req))
        if "val" in st:
            out.records.append(guarded("circuit.solve.independent", _red))
            out.value = st["val"]
        return out

    def _mna():
        sol = solve_mna(ckt)
        st["sol"] = sol
        st["val"] = sp.simplify(evaluate_target(ckt, sol, tgt))
        return VerificationRecord(check_id="circuit.solve.primary", status=CheckStatus.EXACT_CHECKED,
                                  method="exact modified nodal analysis (non-singular)", tool=TOOL,
                                  result=f"{q} of {tgt.get('element')} = {st['val']} {out.unit}")

    out.records.append(guarded("circuit.solve.primary", _mna))
    if "sol" not in st:
        return out

    def _cert():
        probs = certify(ckt, st["sol"])
        return VerificationRecord(check_id="circuit.certificate",
                                  status=CheckStatus.FAILED if probs else CheckStatus.EXACT_CHECKED,
                                  method="KCL at every node + every element law + Tellegen (separate code)",
                                  tool=TOOL, result="; ".join(probs) if probs else
                                  f"KCL at {len(ckt.nodes)} nodes, {len(ckt.comps)} element laws, power balance")

    out.records.append(guarded("circuit.certificate", _cert))
    out.value, out.solution = st["val"], st["sol"]
    return out


# ------------------------------------------------------------------ misconceptions
def misconceptions(formal: dict) -> list[tuple[str, sp.Expr, list[str], str, str]]:
    """Realistic, executable student errors; each is re-solved exactly."""
    out = []
    tgt = formal["target"]

    def resolve(f2) -> Optional[sp.Expr]:
        r = solve_and_verify(f2)
        return r.value if r.value is not None and all(x.is_affirmative() for x in r.records if x.hard) else None

    comps = formal["components"]
    if tgt["quantity"] == "equivalent_resistance":
        vals = [sp.nsimplify(parse(str(c["value"])), rational=True) * unit_info(c.get("unit", "ohm"))[0]
                for c in comps]
        out.append(("CIRC.REQ.ALL_SERIES", sp.Add(*vals), ["Add every resistance as if all were in series"],
                    "Students add all resistances without checking how they are connected.",
                    "Only resistors carrying the same current are in series."))
        out.append(("CIRC.REQ.ALL_PARALLEL", 1 / sp.Add(*[1 / v for v in vals]),
                    ["Combine every resistance as if all were in parallel"],
                    "Students treat every resistor as connected across the same two points.",
                    "Only resistors across the same pair of nodes are in parallel."))
        return out

    for i, c in enumerate(comps):
        if c["type"] == "vsource" and sum(1 for x in comps if x["type"] in ("vsource", "isource")) > 1:
            f2 = {**formal, "components": [dict(x) for x in comps]}
            f2["components"][i]["nodes"] = list(reversed(c["nodes"]))
            v = resolve(f2)
            if v is not None:
                out.append(("CIRC.SOURCE.POLARITY", v, [f"Battery {c['id']} taken with reversed polarity"],
                            "Students misread which terminal of a battery is positive.",
                            "Use the stated polarity of every source."))
        if c["type"] == "capacitor":
            f2 = {**formal, "components": [dict(x) for x in comps]}
            f2["components"][i] = {**c, "type": "resistor", "value": "0.000001", "unit": "ohm"}
            if tgt.get("element") != c["id"]:
                v = resolve(f2)
                if v is not None:
                    out.append(("CIRC.CAP.SHORT_IN_DC", v, [f"Treat capacitor {c['id']} as a wire in DC steady state"],
                                "Students think a charged capacitor conducts.",
                                "In DC steady state a capacitor carries no current (open circuit)."))
        if c["type"] == "resistor" and c["id"] != tgt.get("element"):
            f2 = {**formal, "components": [dict(x) for j, x in enumerate(comps) if j != i]}
            v = resolve(f2)
            if v is not None:
                out.append(("CIRC.BRANCH.IGNORED", v, [f"Ignore the branch containing {c['id']}"],
                            "Students overlook a branch of the circuit.",
                            f"{c['id']} carries current and changes the distribution."))
    # parallel pair treated as series (very common)
    for i, c in enumerate(comps):
        for j, d in enumerate(comps):
            if j <= i or c["type"] != "resistor" or d["type"] != "resistor":
                continue
            if set(c["nodes"]) != set(d["nodes"]):
                continue
            f2 = {**formal, "components": [dict(x) for x in comps]}
            mid = f"_{c['id']}{d['id']}"
            a, b = c["nodes"]
            f2["components"][i]["nodes"] = [a, mid]
            f2["components"][j]["nodes"] = [mid, b]
            v = resolve(f2)
            if v is not None:
                out.append(("CIRC.PARALLEL_AS_SERIES", v, [f"Treat {c['id']} and {d['id']} (in parallel) as series"],
                            "Students judge 'series' from the drawing order instead of the connection points.",
                            f"{c['id']} and {d['id']} connect the same two nodes, so they are in parallel."))
            # current divider inverted, when the target is one of the pair
            if tgt["quantity"] == "current" and tgt.get("element") in (c["id"], d["id"]):
                base = solve_and_verify(formal)
                if base.solution is not None:
                    Ic, Id = sp.Abs(base.solution.I[c["id"]]), sp.Abs(base.solution.I[d["id"]])
                    Rc = sp.nsimplify(parse(str(c["value"])), rational=True) * unit_info(c.get("unit", "ohm"))[0]
                    Rd = sp.nsimplify(parse(str(d["value"])), rational=True) * unit_info(d.get("unit", "ohm"))[0]
                    Rt = Rc if tgt["element"] == c["id"] else Rd
                    out.append(("CIRC.DIVIDER_INVERTED", sp.simplify((Ic + Id) * Rt / (Rc + Rd)),
                                [f"Split the total current {Ic + Id} A in proportion to resistance"],
                                "Students think the larger resistor takes the larger current.",
                                "In parallel, current divides inversely with resistance."))
    out = [m for m in out if m[1] != 0]  # a zero answer is not a plausible distractor
    # Ohm's law with the source voltage across the target resistor
    el = next((c for c in comps if c["id"] == tgt.get("element")), None)
    src = next((c for c in comps if c["type"] == "vsource"), None)
    if el and src and el["type"] == "resistor" and tgt["quantity"] in ("current", "power"):
        R = sp.nsimplify(parse(str(el["value"])), rational=True) * unit_info(el.get("unit", "ohm"))[0]
        E = sp.nsimplify(parse(str(src["value"])), rational=True) * unit_info(src.get("unit", "V"))[0]
        v = E / R if tgt["quantity"] == "current" else E ** 2 / R
        out.append(("CIRC.OHM.FULL_EMF_ACROSS_ONE", v,
                    [f"Assume the full {src['id']} voltage appears across {el['id']}"],
                    "Students apply V = IR to one resistor with the whole battery voltage.",
                    "The battery voltage is shared among the elements in its path."))
    return out


# ------------------------------------------------------------------ rendering
_TYPE_WORD = {"resistor": "resistor", "vsource": "ideal battery", "isource": "ideal current source",
              "capacitor": "capacitor", "inductor": "ideal inductor"}
_UNIT_TXT = {"ohm": "Ω", "uF": "μF", "microfarad": "μF"}


def render_stem(formal: dict) -> str:
    parts = []
    for c in formal["components"]:
        u = _UNIT_TXT.get(c.get("unit", ""), c.get("unit", EXPECTED_UNIT[c["type"]]))
        if c["type"] == "vsource":
            parts.append(f"an {_TYPE_WORD[c['type']]} {c['id']} of emf {c['value']} {u} with its positive "
                         f"terminal at {c['nodes'][0]} and negative terminal at {c['nodes'][1]}")
        elif c["type"] == "isource":
            parts.append(f"an {_TYPE_WORD[c['type']]} {c['id']} of {c['value']} {u} driving current from "
                         f"{c['nodes'][0]} to {c['nodes'][1]} through itself")
        else:
            parts.append(f"a {c['value']} {u} {_TYPE_WORD[c['type']]} {c['id']} between {c['nodes'][0]} "
                         f"and {c['nodes'][1]}")
    t = formal["target"]
    ask = {"current": f"the magnitude of the current through {t.get('element')}",
           "voltage": f"the magnitude of the potential difference across {t.get('element')}",
           "power": f"the power dissipated in {t.get('element')}",
           "charge": f"the magnitude of the charge on {t.get('element')} in steady state",
           "energy": f"the energy stored in {t.get('element')} in steady state",
           "equivalent_resistance": f"the equivalent resistance between {t.get('terminals', ['?', '?'])[0]} "
                                    f"and {t.get('terminals', ['?', '?'])[1]}"}[t["quantity"]]
    return ("A circuit (see figure) consists of " + "; ".join(parts) +
            ". Wires are ideal and the circuit is in steady state. Find " + ask + ".")


def _best_order(nodes: list[str], pairs: list[tuple[str, str]], ground: str) -> list[str]:
    """Circle order with the fewest chord crossings (exhaustive for <= 8 nodes)."""
    import itertools
    if len(nodes) <= 3:
        return nodes

    def crossings(order):
        at = {n: i for i, n in enumerate(order)}
        ch = [tuple(sorted((at[a], at[b]))) for a, b in pairs]
        cnt = 0
        for (a1, b1), (a2, b2) in itertools.combinations(set(ch), 2):
            if len({a1, b1, a2, b2}) == 4 and (a1 < a2 < b1 < b2 or a2 < a1 < b2 < b1):
                cnt += 1
        return cnt

    first, rest = nodes[0], nodes[1:]
    best, best_c = nodes, None
    perms = itertools.permutations(rest) if len(nodes) <= 8 else [tuple(rest)]
    for perm in perms:
        order = [first, *perm]
        c = crossings(order)
        if best_c is None or c < best_c:
            best, best_c = order, c
            if c == 0:
                break
    return best


def render_svg(formal: dict, size: int = 480) -> str:
    """Schematic drawn FROM the netlist, so the figure cannot disagree with the formal state.
    Node order minimises crossings; parallel branches are arcs; every component uses its
    standard symbol at the middle of its own branch; labels sit on the outer side."""
    comps = formal["components"]
    nodes = sorted({n for c in comps for n in c["nodes"]})
    ground = formal.get("ground") or ("G" if "G" in nodes else nodes[0])
    order = _best_order(nodes, [tuple(c["nodes"]) for c in comps], ground)
    k0 = order.index(ground)
    cx = cy = size / 2
    rad = size / 2 - 80
    n_ = len(order)
    pos = {}
    for i, n in enumerate(order):
        ang = math.pi / 2 + 2 * math.pi * (i - k0) / n_   # ground at the bottom
        pos[n] = (cx + rad * math.cos(ang), cy + rad * math.sin(ang))
    groups: dict[frozenset, list[int]] = {}
    for i, c in enumerate(comps):
        groups.setdefault(frozenset(c["nodes"]), []).append(i)

    # Chords that would cross are routed as arcs OUTSIDE the circle (textbook bridge style).
    at = {n: i for i, n in enumerate(order)}

    def interleave(p1, p2):
        a1, b1 = sorted((at[x] for x in p1))
        a2, b2 = sorted((at[x] for x in p2))
        return len({a1, b1, a2, b2}) == 4 and (a1 < a2 < b1 < b2 or a2 < a1 < b2 < b1)

    def priority(pair):  # reroute sources first, then single-component pairs
        types = {comps[i]["type"] for i in groups[pair]}
        return (0 if types & {"vsource", "isource"} else 1, len(groups[pair]))

    outer: set[frozenset] = set()
    while True:
        straight = [g for g in groups if g not in outer]
        bad = [(g1, g2) for k, g1 in enumerate(straight) for g2 in straight[k + 1:] if interleave(g1, g2)]
        if not bad:
            break
        counts: dict[frozenset, int] = {}
        for g1, g2 in bad:
            counts[g1] = counts.get(g1, 0) + 1
            counts[g2] = counts.get(g2, 0) + 1
        outer.add(min(counts, key=lambda g: (priority(g), -counts[g])))

    def fmt(pt):
        return f"{pt[0]:.1f},{pt[1]:.1f}"

    body, labels = [], []
    xs_all: list[float] = [x for x, _ in pos.values()]
    ys_all: list[float] = [y for _, y in pos.values()]
    for key, idxs in groups.items():
        for rank, i in enumerate(idxs):
            c = comps[i]
            a, b = sorted(c["nodes"])                 # stable geometry per node pair
            (x1, y1), (x2, y2) = pos[a], pos[b]
            L = math.hypot(x2 - x1, y2 - y1) or 1
            nx, ny = -(y2 - y1) / L, (x2 - x1) / L
            off = (rank - (len(idxs) - 1) / 2) * min(80, L / 2)
            if key in outer:
                mxc, myc = (x1 + x2) / 2, (y1 + y2) / 2
                side = 1 if (mxc - cx) * nx + (myc - cy) * ny >= 0 else -1
                if math.hypot(mxc - cx, myc - cy) < 1:   # a diameter: bulge to the emptier side
                    side = 1 if sum(1 for (px_, py_) in pos.values()
                                    if (px_ - cx) * nx + (py_ - cy) * ny > 1) <= 1 else -1
                reach = rad + 55 - abs((mxc - cx) * nx + (myc - cy) * ny)
                off = side * (reach + rank * 45)
            # quadratic Bezier whose midpoint is displaced by `off`
            ctrl = ((x1 + x2) / 2 + nx * 2 * off, (y1 + y2) / 2 + ny * 2 * off)
            N = 240
            pts = [((1 - t) ** 2 * x1 + 2 * (1 - t) * t * ctrl[0] + t * t * x2,
                    (1 - t) ** 2 * y1 + 2 * (1 - t) * t * ctrl[1] + t * t * y2)
                   for t in (k / N for k in range(N + 1))]
            mid = N // 2
            h = 22
            i1 = mid
            acc = 0.0
            while i1 > 0 and acc < h:
                acc += math.dist(pts[i1], pts[i1 - 1]); i1 -= 1
            i2, acc = mid, 0.0
            while i2 < N and acc < h:
                acc += math.dist(pts[i2], pts[i2 + 1]); i2 += 1
            m = pts[mid]
            ux, uy = pts[i2][0] - pts[i1][0], pts[i2][1] - pts[i1][1]
            ul = math.hypot(ux, uy) or 1
            ux, uy = ux / ul, uy / ul
            vx, vy = -uy, ux
            out_sign = 1 if (m[0] - cx) * vx + (m[1] - cy) * vy >= 0 else -1
            xs_all.extend(pt[0] for pt in pts); ys_all.extend(pt[1] for pt in pts)
            # orient so that d<0 is toward the component's nodes[0] (battery + side)
            sgn_dir = 1 if c["nodes"][0] == a else -1
            q = lambda d, w: (m[0] + ux * d * sgn_dir + vx * w, m[1] + uy * d * sgn_dir + vy * w)  # noqa: E731
            body.append('<polyline points="' + " ".join(fmt(pt) for pt in pts[:i1 + 1]) + '"/>')
            body.append('<polyline points="' + " ".join(fmt(pt) for pt in pts[i2:]) + '"/>')
            t = c["type"]
            line = lambda p1, p2, extra="": body.append(  # noqa: E731
                f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}"{extra}/>')
            if t == "resistor":
                zz = [q(-h, 0)] + [q(-h + (k + 0.5) * (2 * h / 6), 7 if k % 2 == 0 else -7) for k in range(6)] + [q(h, 0)]
                body.append('<polyline points="' + " ".join(fmt(pt) for pt in zz) + '"/>')
            elif t == "vsource":   # long thin plate = + terminal (nodes[0] side), short thick = -
                line(q(-h, 0), q(-4, 0)); line(q(4, 0), q(h, 0))
                line(q(-4, 15), q(-4, -15)); line(q(4, 8), q(4, -8), ' stroke-width="4"')
                pp = q(-13, -20 * out_sign)  # "+" on the side away from the label
                labels.append(f'<text x="{pp[0]:.1f}" y="{pp[1] + 5:.1f}" text-anchor="middle" '
                              f'font-weight="bold">+</text>')
            elif t == "capacitor":
                line(q(-h, 0), q(-4, 0)); line(q(4, 0), q(h, 0))
                line(q(-4, 13), q(-4, -13)); line(q(4, 13), q(4, -13))
            elif t == "inductor":
                coil = [q(-h + 2 * h * k / 48, 8 * abs(math.sin(math.pi * 4 * k / 48))) for k in range(49)]
                body.append('<polyline points="' + " ".join(fmt(pt) for pt in coil) + '"/>')
            elif t == "isource":
                body.append(f'<circle cx="{m[0]:.1f}" cy="{m[1]:.1f}" r="13" fill="white"/>')
                line(q(-h, 0), q(-13, 0)); line(q(13, 0), q(h, 0))
                line(q(-7, 0), q(7, 0))
                body.append(f'<polyline points="{fmt(q(2, 4))} {fmt(q(7, 0))} {fmt(q(2, -4))}"/>')
            # label on the outer side
            lx, ly = m[0] + vx * 30 * out_sign, m[1] + vy * 30 * out_sign
            u = _UNIT_TXT.get(c.get("unit", ""), c.get("unit", EXPECTED_UNIT[t]))
            xs_all.extend((lx - 45, lx + 45)); ys_all.extend((ly - 10, ly + 10))
            labels.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" '
                          f'paint-order="stroke" stroke="white" stroke-width="4">{c["id"]} = {c["value"]} {u}</text>')
    x0, y0 = min(xs_all) - 35, min(ys_all) - 35
    w, hgt = max(xs_all) + 35 - x0, max(ys_all) + 35 - y0
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{hgt:.0f}" '
           f'viewBox="{x0:.1f} {y0:.1f} {w:.1f} {hgt:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="13">',
           f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{hgt:.1f}" fill="white"/>',
           '<g stroke="black" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round">',
           *body, "</g>"]
    for n, (x, y) in pos.items():
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="black"/>')
        svg.append(f'<text x="{x + dx / d * 22:.1f}" y="{y + dy / d * 22 + 5:.1f}" text-anchor="middle" '
                   f'font-weight="bold" font-size="15">{n}</text>')
    svg += labels
    svg.append("</svg>")
    return "\n".join(svg)
