from __future__ import annotations

import re
import ast
import argparse
from typing import Dict, Tuple, List, Set, Optional

# Adjust this import to your project layout
# from your_module_name import Node, W_Node, V_Node, Edge, Graph, CmCTPR_Instance
from .road_network_formulation import Node, W_Node, V_Node, Edge, Graph, CmCTPR_Instance


_SECTION_NODES = re.compile(r"^\s*Nodes\s*\(V\)\s*$", re.IGNORECASE)
_SECTION_ARCS = re.compile(r"^\s*Arcs\s*\(A\)\s*$", re.IGNORECASE)
_SECTION_DEMAND = re.compile(r"^\s*DemandNodes\s*\(W\)\s*$", re.IGNORECASE)

_START = re.compile(r"^\s*START\s*$", re.IGNORECASE)
_END = re.compile(r"^\s*END\s*$", re.IGNORECASE)

# header line examples:
# "VehicleCapacity (Q):    1"
# "Name:   W15-0-1"
_HEADER_KV = re.compile(r"^\s*([^:]+?)\s*:\s*(.+?)\s*$")

# nodes row:
# "18 true 2592104 1221089"
# "0 false 2592089 1221174"
_NODE_ROW = re.compile(r"^\s*(\d+)\s+(true|false)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$", re.IGNORECASE)

# arcs row:
# "0 12 39"
_ARC_ROW = re.compile(r"^\s*(\d+)\s+(\d+)\s+(-?\d+(?:\.\d+)?)\s*$")

# demand row:
# "19 4 [19, 18]"
_DEMAND_ROW = re.compile(r"^\s*(\d+)\s+(-?\d+(?:\.\d+)?)\s+(\[.*\])\s*$")


def _to_int(x: str) -> int:
    return int(float(x))  # robust vs "1.0"


def _to_float(x: str) -> float:
    return float(x)


def _parse_bool(x: str) -> bool:
    return x.strip().lower() == "true"


def _normalize_key(k: str) -> str:
    """
    Map verbose header keys to canonical names.
    We keep it permissive: match substrings.
    """
    ks = k.strip().lower()
    if "maximumwalkingdistance" in ks or "(gamma)" in ks:
        return "gamma"
    if "numberoftours" in ks or "(m)" in ks:
        return "m"
    if "vehiclecapacity" in ks or "(q)" in ks:
        return "Q"
    if "totalwaste" in ks or "(dtot)" in ks:
        return "dtot"
    if "wastedepot" in ks or "(sigma)" in ks:
        return "sigma"
    if "numberdemandnodes" in ks or "(|w|)" in ks:
        return "num_W"
    if "numbercandidatelocations" in ks or "(|vsto|)" in ks:
        return "num_Vsto"
    if "name" == ks:
        return "name"
    if "dataproblemtype" in ks:
        return "problem_type"
    return k.strip()  # fallback


def parse_instance_file(path: str) -> CmCTPR_Instance:
    """
    Generic parser for the provided plain-text instance format.
    Returns an initialized CmCTPR_Instance.
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]

    # ---------
    # Parse header until Nodes(V)
    # ---------
    params: Dict[str, str] = {}
    i = 0
    while i < len(lines) and not _SECTION_NODES.match(lines[i]):
        m = _HEADER_KV.match(lines[i])
        if m:
            key = _normalize_key(m.group(1))
            params[key] = m.group(2).strip()
        i += 1

    # Mandatory (for CmCTPR_Instance)
    if "sigma" not in params or "gamma" not in params or "m" not in params or "Q" not in params or "dtot" not in params:
        missing = [k for k in ["sigma", "gamma", "m", "Q", "dtot"] if k not in params]
        raise ValueError(f"Missing mandatory header fields: {missing}")

    sigma = _to_int(params["sigma"])
    gamma = _to_int(params["gamma"])
    m_tours = _to_int(params["m"])
    Q = _to_int(params["Q"])
    dtot = _to_int(params["dtot"])

    # Optional counts (sanity checks only)
    declared_num_W = _to_int(params["num_W"]) if "num_W" in params else None
    declared_num_Vsto = _to_int(params["num_Vsto"]) if "num_Vsto" in params else None

    # ---------
    # Parse sections with a simple state machine
    # ---------
    coordinates: Dict[int, Tuple[float, float]] = {}
    candidate_set: Set[int] = set()
    arcs: List[Tuple[int, int, float]] = []
    demands: List[Tuple[int, float, List[int]]] = []

    # Move i to "Nodes (V)"
    while i < len(lines) and not _SECTION_NODES.match(lines[i]):
        i += 1
    if i == len(lines):
        raise ValueError("Section 'Nodes (V)' not found")
    i += 1  # consume section title

    # Expect START then table header then rows until END
    while i < len(lines) and not _START.match(lines[i]):
        i += 1
    if i == len(lines):
        raise ValueError("START marker for Nodes(V) not found")
    i += 1

    # Skip possible table header lines until we hit a data row or END
    while i < len(lines) and not _END.match(lines[i]) and _NODE_ROW.match(lines[i]) is None:
        i += 1

    # Nodes rows
    while i < len(lines) and not _END.match(lines[i]):
        row = lines[i].strip()
        mrow = _NODE_ROW.match(row)
        if mrow:
            nid = int(mrow.group(1))
            is_cand = _parse_bool(mrow.group(2))
            x = _to_float(mrow.group(3))
            y = _to_float(mrow.group(4))
            coordinates[nid] = (x, y)
            if is_cand:
                candidate_set.add(nid)
        # else: tolerate noise lines
        i += 1

    if i == len(lines):
        raise ValueError("END marker for Nodes(V) not found")
    i += 1  # consume END

    # ---------
    # Arcs (A)
    # ---------
    while i < len(lines) and not _SECTION_ARCS.match(lines[i]):
        i += 1
    if i == len(lines):
        raise ValueError("Section 'Arcs (A)' not found")
    i += 1  # consume section title

    while i < len(lines) and not _START.match(lines[i]):
        i += 1
    if i == len(lines):
        raise ValueError("START marker for Arcs(A) not found")
    i += 1

    # Skip header
    while i < len(lines) and not _END.match(lines[i]) and _ARC_ROW.match(lines[i]) is None:
        i += 1

    while i < len(lines) and not _END.match(lines[i]):
        row = lines[i].strip()
        mrow = _ARC_ROW.match(row)
        if mrow:
            src = int(mrow.group(1))
            dst = int(mrow.group(2))
            c = _to_float(mrow.group(3))
            arcs.append((src, dst, c))
        i += 1

    if i == len(lines):
        raise ValueError("END marker for Arcs(A) not found")
    i += 1  # consume END

    # ---------
    # DemandNodes (W)
    # ---------
    while i < len(lines) and not _SECTION_DEMAND.match(lines[i]):
        i += 1
    if i == len(lines):
        raise ValueError("Section 'DemandNodes (W)' not found")
    i += 1  # consume section title

    while i < len(lines) and not _START.match(lines[i]):
        i += 1
    if i == len(lines):
        raise ValueError("START marker for DemandNodes(W) not found")
    i += 1

    # Skip header
    while i < len(lines) and not _END.match(lines[i]) and _DEMAND_ROW.match(lines[i]) is None:
        i += 1

    while i < len(lines) and not _END.match(lines[i]):
        row = lines[i].strip()
        mrow = _DEMAND_ROW.match(row)
        if mrow:
            wid = int(mrow.group(1))
            waste = _to_float(mrow.group(2))
            # safe parse list literal
            vrank = ast.literal_eval(mrow.group(3))
            if not isinstance(vrank, list) or not all(isinstance(v, int) for v in vrank):
                raise ValueError(f"Invalid V_rank list at demand node {wid}: {vrank}")
            demands.append((wid, waste, vrank))
        i += 1

    if i == len(lines):
        raise ValueError("END marker for DemandNodes(W) not found")

    # ---------
    # Build Graph
    # ---------
    g = Graph()

    # Demand nodes
    W_ids: Set[int] = set()
    derived_Vsto: Set[int] = set()
    for wid, waste, vrank in demands:
        W_ids.add(wid)
        derived_Vsto.update(vrank)
        g.add_node(W_Node(wid, waste=waste, V_rank=vrank), set())

    # Candidate V nodes: union of "IsCandidateLocation == true" and those referenced in V_rank
    V_ids = set(candidate_set) | set(derived_Vsto)

    # Add V nodes (unless already W)
    for vid in V_ids:
        if vid not in W_ids:
            g.add_node(V_Node(vid), set())

    # Ensure depot exists as V node if missing
    try:
        _ = g[sigma]
    except KeyError:
        g.add_node(V_Node(sigma), set())

    # Add remaining nodes referenced by coordinates or arcs (as base Node)
    referenced: Set[int] = set(coordinates.keys())
    for a, b, _c in arcs:
        referenced.add(a)
        referenced.add(b)

    for nid in referenced:
        try:
            _ = g[nid]
        except KeyError:
            g.add_node(Node(nid), set())

    # Add edges
    for a, b, c in arcs:
        g.edges.add(Edge(a, b, c))

    # ---------
    # Sanity checks (non-fatal unless you want strict mode)
    # ---------
    if declared_num_W is not None and declared_num_W != len(demands):
        raise ValueError(f"Declared |W|={declared_num_W}, parsed |W|={len(demands)}")

    if declared_num_Vsto is not None and declared_num_Vsto != len(derived_Vsto):
        # note: dataset says |Vsto| is union of V_rank; we check that, not candidate_set size
        raise ValueError(f"Declared |Vsto|={declared_num_Vsto}, derived |Vsto|={len(derived_Vsto)} from V_rank")

    # ---------
    # Build instance
    # ---------
    inst = CmCTPR_Instance(
        graph=g,
        coordinates=coordinates,
        sigma=sigma,
        gamma=gamma,
        m=m_tours,
        Q=Q,
        dtot=dtot,
    )
    return inst


def main():
    ap = argparse.ArgumentParser(description="Parse Cm-CTP-R instance text file into CmCTPR_Instance.")
    ap.add_argument("path", type=str, help="Path to instance file")
    args = ap.parse_args()

    inst = parse_instance_file(args.path)
    print("OK")
    print(f"|V ∪ W|={len(inst._graph.nodes)} |A|={len(inst._graph.edges)} |Vsto|={len(inst._V_sto)}")
    print(f"sigma={inst._depot_node} gamma={inst._max_walking_distance} m={inst._num_tours} Q={inst._vehicle_capacity} dtot={inst._total_waste}")


if __name__ == "__main__":
    main()