from __future__ import annotations

import re
import ast
import argparse
from typing import Dict, Tuple, List, Set, Optional

class RoadNetworkFormulation:
    def __init__(self) -> None:
        self.v_nodes: Set[int] = set()
        self.w_nodes: Set[int] = set()
        self.arcs: set[Tuple[int, int]] = set()
        self.cost: Dict[Tuple[int, int], int] = {}
        self.v_sto: Set[int] = set()
        self.v_ranks: Dict[int, List[int]] = {}
        self.M: Set[int] = set()
        self.demand: Dict[int, int] = {}
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
                        formulation.v_nodes.add(int(node_data[0]))
                        if node_data[1] == "true":
                            formulation.v_sto.add(int(node_data[0]))
                        c += 1
                # PARSE ARCS
                elif line.startswith("Arcs (A)"):
                    c += 3 # SKIP USELESS METADATA
                    while lines[c].strip() != "END":
                        arc_data = lines[c].strip().split()
                        formulation.arcs.add((int(arc_data[0]), int(arc_data[1])))
                        formulation.cost[(int(arc_data[0]), int(arc_data[1]))] = int(arc_data[2])
                        c += 1
                # PARSE W NODES
                elif line.startswith("DemandNodes (W)"):
                    c += 3 # SKIP USELESS METADATA
                    while lines[c].strip() != "END":
                        node_data = lines[c].strip().split()
                        formulation.w_nodes.add(int(node_data[0]))
                        formulation.demand[int(node_data[0])] = int(node_data[1])
                        formulation.v_ranks[int(node_data[0])] = []
                        for rank_node in lines[c].strip().split("[")[-1].split("]")[0].split(","): # REMOVE SQUARE BRACKETS AND SPLIT BY COMMA
                            formulation.v_ranks[int(node_data[0])].append(int(rank_node.strip()))
                        c += 1
                c += 1
        # DERIVE Q AS PER SECTION 6.1 OF THE PAPER
        formulation.Q = 1.05 * (formulation.dtot / len(formulation.M))
        # SET t_sto TO 5s AS PER SECTION 3.3 A6) OF THE PAPER
        formulation.t_sto = 5.0
        # Parse the content of the .dat file and populate the formulation attributes
        # This is a placeholder for the actual parsing logic, which will depend on the format of the .dat file
        return formulation
    
    def rank(self, i: int, j: int) -> int:
        if j in self.v_ranks[i]:
            return self.v_ranks[i].index(j)
        else:
            raise ValueError(f"Node {j} is not in the rank list of node {i}")

class CustomerBasedFormulation:
    def __init__(self) -> None:
        self.v_nodes: Set[int] = set()
        self.w_nodes: Set[int] = set()
        self.arcs: set[Tuple[int, int]] = set()
        self.cost: Dict[Tuple[int, int], int] = {}
        self.v_sto: Set[int] = set()
        self.v_ranks: Dict[int, List[int]] = {}
        self.M: Set[int] = set()
        self.demand: Dict[int, int] = {}
        self.dtot: int = 0
        self.Q: float = 0.0
        self.sigma: int = 0
        self.t_sto: float = 0

    @staticmethod
    def parse_instance_file(dat_path: str) -> CustomerBasedFormulation:
        RN = RoadNetworkFormulation().parse_instance_file(dat_path)
        formulation = CustomerBasedFormulation()
        formulation.v_nodes = RN.v_sto.union({RN.sigma})
        formulation.w_nodes = RN.w_nodes
        formulation.v_sto = RN.v_sto
        formulation.v_ranks = RN.v_ranks
        formulation.M = RN.M
        formulation.demand = RN.demand
        formulation.dtot = RN.dtot
        formulation.Q = RN.Q
        formulation.sigma = RN.sigma
        formulation.t_sto = RN.t_sto
        # CREATE A' AND ARC'
        return formulation

        


def main():
    ap = argparse.ArgumentParser(description="Parse Cm-CTP-R instance text file into CmCTPR_Instance.")
    ap.add_argument("path", type=str, help="Path to instance file")
    args = ap.parse_args()

    formulation = RoadNetworkFormulation.parse_instance_file(args.path)
    print("OK")
    print(f"|V ∪ W|={len(formulation.v_nodes | formulation.w_nodes)} |A|={len(formulation.arcs)} |Vsto|={len(formulation.v_sto)}")
    print(f"sigma={formulation.sigma} gamma={formulation.t_sto} m={len(formulation.M)} Q={formulation.Q} dtot={formulation.dtot}")
    print("V_ranks:")
    for w in formulation.w_nodes:
        print(f"  w{w}: {formulation.v_ranks[w]}")
    print("Costs:")
    for arc in formulation.arcs:
        print(f"  {arc}: {formulation.cost[arc]}")
    print("Demands:")
    for w in formulation.w_nodes:
        print(f"  w{w}: {formulation.demand[w]}")
    print("V_sto:", formulation.v_sto)

if __name__ == "__main__":
    main()