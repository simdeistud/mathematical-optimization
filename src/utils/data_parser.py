from __future__ import annotations

import heapq
from math import inf
import argparse
from typing import Dict, Tuple, List, Set, Optional

class RoadNetworkFormulation:
    def __init__(self) -> None:
        self.V: Set[int] = set()
        self.W: Set[int] = set()
        self.A: set[Tuple[int, int]] = set()
        self.c: Dict[Tuple[int, int], float] = {}
        self.V_sto: Set[int] = set()
        self.V_rank: Dict[int, List[int]] = {}
        self.M: Set[int] = set()
        self.d: Dict[int, int] = {}
        self.dtot: int = 0
        self.Q: float = 0.0
        self.sigma: int = 0
        self.t_sto: float = 0
    
    @staticmethod
    def parse_instance_file(dat_path: str) -> RoadNetworkFormulation:
        formulation = RoadNetworkFormulation()
        with open(dat_path, "r") as f:
            lines = f.read().split("\n")
            c = 4 # SKIP FIRST 4 LINES OF USELESS METADATA
            while c < len(lines):
                line = lines[c]
                # PARSE HEADER
                if line.startswith("NumberOfTours"):
                    formulation.M = set(range(1, int(line.split(":")[-1].strip()) + 1))
                elif line.startswith("VehicleCapacity"):
                    formulation.Q = float(line.split(":")[-1].strip())
                elif line.startswith("TotalWaste"):
                    formulation.dtot = int(line.split(":")[-1].strip())
                elif line.startswith("WasteDepot"):
                    formulation.sigma = int(line.split(":")[-1].strip())
                # PARSE V NODES
                elif line.startswith("Nodes (V)"):
                    c += 3 # SKIP USELESS METADATA
                    while lines[c].strip() != "END":
                        node_data = lines[c].strip().split()
                        formulation.V.add(int(node_data[0]))
                        c += 1
                # PARSE ARCS
                elif line.startswith("Arcs (A)"):
                    c += 3 # SKIP USELESS METADATA
                    while lines[c].strip() != "END":
                        arc_data = lines[c].strip().split()
                        formulation.A.add((int(arc_data[0]), int(arc_data[1])))
                        # THE PAPER ASSUMES 14m/s FOR ARCS CONNECTING THE DEPOT AND 2m/s FOR ALL OTHER ARCS, AS PER SECTION 6.1
                        if int(arc_data[0]) == formulation.sigma or int(arc_data[1]) == formulation.sigma:
                            formulation.c[(int(arc_data[0]), int(arc_data[1]))] = int(arc_data[2]) / 14
                        else:
                            formulation.c[(int(arc_data[0]), int(arc_data[1]))] = int(arc_data[2]) / 2
                        c += 1
                # PARSE W NODES
                elif line.startswith("DemandNodes (W)"):
                    c += 3 # SKIP USELESS METADATA
                    while lines[c].strip() != "END":
                        node_data = lines[c].strip().split()
                        formulation.W.add(int(node_data[0]))
                        formulation.d[int(node_data[0])] = int(node_data[1])
                        formulation.V_rank[int(node_data[0])] = []
                        for rank_node in lines[c].strip().split("[")[-1].split("]")[0].split(","): # REMOVE SQUARE BRACKETS AND SPLIT BY COMMA
                            formulation.V_rank[int(node_data[0])].append(int(rank_node.strip()))
                        c += 1
                c += 1
        # SOME VALIDATIONS
        for i, rank_list in formulation.V_rank.items():
            for j in rank_list:
                if j not in formulation.V:
                    raise ValueError(f"Ranked node {j} for demand node {i} is not in V")
        if formulation.sigma not in formulation.V:
            raise ValueError(f"Depot sigma={formulation.sigma} is not in V")
        if formulation.dtot != sum(formulation.d.values()):
            raise ValueError(
                f"TotalWaste={formulation.dtot}, but sum(d_i)={sum(formulation.d.values())}"
            )
        # COMPILE V_sto
        for w in formulation.W:
            formulation.V_sto.update(formulation.V_rank[w])
        # DERIVE Q AS PER SECTION 6.1 OF THE PAPER
        formulation.Q = 1.05 * (formulation.dtot / len(formulation.M))
        # SET t_sto TO 5s AS PER SECTION 3.3 A6) OF THE PAPER
        formulation.t_sto = 5
        return formulation
    
    def rank(self, i: int, j: int) -> int:
        if j in self.V_rank[i]:
            return self.V_rank[i].index(j)
        else:
            raise ValueError(f"Node {j} is not in the rank list of node {i}")

class CustomerBasedFormulation:
    def __init__(self) -> None:
        self.Vp: Set[int] = set()
        self.W: Set[int] = set()
        self.Ap: set[Tuple[int, int]] = set()
        self.c: Dict[Tuple[int, int], float] = {}
        self.V_sto: Set[int] = set()
        self.V_rank: Dict[int, List[int]] = {}
        self.M: Set[int] = set()
        self.d: Dict[int, int] = {}
        self.dtot: int = 0
        self.Q: float = 0.0
        self.sigma: int = 0
        self.t_sto: float = 0

    @staticmethod
    def parse_instance_file(dat_path: str) -> CustomerBasedFormulation:
        RN = RoadNetworkFormulation.parse_instance_file(dat_path)
        formulation = CustomerBasedFormulation()
        formulation.W = RN.W
        formulation.V_sto = RN.V_sto
        formulation.V_rank = RN.V_rank
        formulation.M = RN.M
        formulation.d = RN.d
        formulation.dtot = RN.dtot
        formulation.Q = RN.Q
        formulation.sigma = RN.sigma
        formulation.t_sto = RN.t_sto
        # CREATE V'
        formulation.Vp = RN.V_sto.union({RN.sigma})   
        # CREATE A' with shortest-path costs in the underlying road network
        # (ordered pairs, excluding self-loops)
        for j in formulation.Vp:
            for jp in formulation.Vp:
                formulation.Ap.add((j, jp))
                time = dijkstra_min_cost(
                        start=j,
                        end=jp,
                        nodes=RN.V | RN.W,
                        arcs=RN.A,
                        costs=RN.c,
                    )
                if time == inf:
                    raise ValueError(f"No path from {j} to {jp} in the underlying road network")   
                formulation.c[(j, jp)] = time
        return formulation
    
    def rank(self, i: int, j: int) -> int:
        if j in self.V_rank[i]:
            return self.V_rank[i].index(j)
        else:
            raise ValueError(f"Node {j} is not in the rank list of node {i}")



def dijkstra_min_cost(
    start: int,
    end: int,
    nodes: Set[int],
    arcs: Set[Tuple[int, int]],
    costs: Dict[Tuple[int, int], float],
) -> float:
    """
    Heap-based Dijkstra on a directed graph with float arc costs.

    Returns the minimum path cost from start to end, or math.inf if unreachable.
    Requires non-negative arc costs.
    """
    if start not in nodes or end not in nodes:
        return inf
    if start == end:
        return 0.0

    # adjacency list: node -> list[(neighbor, weight)]
    adj: Dict[int, List[Tuple[int, float]]] = {u: [] for u in nodes}
    for (u, v) in arcs:
        w = costs.get((u, v))
        if w is None:
            continue
        # Optional: enforce Dijkstra precondition
        if w < 0:
            raise ValueError(f"Negative arc cost on ({u},{v}) = {w}; Dijkstra requires w >= 0.")
        adj[u].append((v, float(w)))

    dist: Dict[int, float] = {u: inf for u in nodes}
    dist[start] = 0.0
    pq: List[Tuple[float, int]] = [(0.0, start)]

    while pq:
        du, u = heapq.heappop(pq)
        if du != dist[u]:
            continue  # stale entry
        if u == end:
            return du  # settled target

        for v, w in adj.get(u, []):
            nd = du + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))

    return dist[end]

      


def main():
    ap = argparse.ArgumentParser(description="Parse Cm-CTP-R instance text file into CmCTPR_Instance.")
    ap.add_argument("path", type=str, help="Path to instance file")
    args = ap.parse_args()

    formulation = RoadNetworkFormulation.parse_instance_file(args.path)
    print("RNF OK")
    print("|W| =", len(formulation.W))
    print("|V| =", len(formulation.V))
    print("|A| =", len(formulation.A))
    print("|V_sto| =", len(formulation.V_sto))

    formulation_cbf = CustomerBasedFormulation.parse_instance_file(args.path)
    print("CBF OK")
    

if __name__ == "__main__":
    main()