import heapq
import math
import random
import argparse

# Class modeling a generic instance of the C𝑚-CTP-R problem
class CmCTPRFormulation:
    def __init__(self) -> None:
        self.V: set[int] = set()
        self.coords: dict[int, tuple[int, int]] = {}
        self.W: set[int] = set()
        self.A: set[tuple[int, int]] = set()
        self.c: dict[tuple[int, int], float] = {} # The cost is not the length of the arc, but its travel time in seconds
        self.V_sto: set[int] = set()
        self.V_rank: dict[int, list[int]] = {}
        self.M: set[int] = set()
        self.d: dict[int, int] = {}
        self.dtot: int = 0
        self.Q: int = 0
        self.sigma: int = 0
        self.t_sto: float = 0
    
    def rank(self, i: int, j: int) -> int:
        if j in self.V_rank[i]:
            return self.V_rank[i].index(j)
        else:
            raise ValueError(f"Node {j} is not in the rank list of node {i}")
    
    @staticmethod
    # Parser to take a .dat instance file and instance a formulation from it
    def parse_instance_file(dat_path: str) -> CmCTPRFormulation:
        formulation = CmCTPRFormulation()
        with open(dat_path, "r") as f:
            lines = f.read().split("\n")
            c = 4 # SKIP FIRST 4 LINES OF USELESS METADATA
            while c < len(lines):
                line = lines[c]
                # PARSE HEADER
                if line.startswith("NumberOfTours"):
                        formulation.M = set(range(1, int(line.split(":")[-1].strip()) + 1))
                elif line.startswith("VehicleCapacity"):
                    formulation.Q = int(line.split(":")[-1].strip())
                elif line.startswith("TotalWaste"):
                    formulation.dtot = int(line.split(":")[-1].strip())
                elif line.startswith("WasteDepot"):
                    formulation.sigma = int(line.split(":")[-1].strip())
                # PARSE V NODES
                elif line.startswith("Nodes (V)"):
                    c += 3 # SKIP USELESS METADATA
                    while lines[c].strip() != "END":
                        node_data = lines[c].strip().split()
                        node = int(node_data[0])
                        xcoord = int(node_data[2])
                        ycoord = int(node_data[3])
                        formulation.V.add(node)
                        formulation.coords[node] = (xcoord, ycoord)
                        # ADD TO V_sto IF IsCandidateLocation IS "true"
                        if node_data[1] == "true":
                            formulation.V_sto.add(node)
                        c += 1
                # PARSE ARCS
                elif line.startswith("Arcs (A)"):
                    c += 3 # SKIP USELESS METADATA
                    while lines[c].strip() != "END":
                        arc_data = lines[c].strip().split()
                        arc = (int(arc_data[0]), int(arc_data[1]))
                        length = int(arc_data[2])
                        formulation.A.add(arc)
                        # THE PAPER ASSUMES 14m/s FOR ARCS CONNECTING THE DEPOT AND 2m/s FOR ALL OTHER ARCS, AS PER SECTION 6.1
                        if arc[0] == formulation.sigma or arc[1] == formulation.sigma:
                            formulation.c[arc] = length / 14.0
                        else:
                            formulation.c[arc] = length / 2.0
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
        # DERIVE Q AS PER SECTION 6.1 OF THE PAPER
        formulation.Q = math.ceil(1.05 * (formulation.dtot / len(formulation.M)))
        # set t_sto TO 5s AS PER SECTION 3.3 A6) OF THE PAPER
        formulation.t_sto = 5
        return formulation

# Class modeling the Road Network Formulation (RNF) from the paper
class RoadNetworkFormulation(CmCTPRFormulation):
    def __init__(self, dat_path: str) -> None:
        # The RNF follows naturally from the given instance files, so no processing is needed
        super().__init__()
        formulation = CmCTPRFormulation.parse_instance_file(dat_path)
        self.V = formulation.V
        self.coords = formulation.coords
        self.W = formulation.W
        self.A = formulation.A
        self.c = formulation.c
        self.V_sto = formulation.V_sto
        self.V_rank = formulation.V_rank
        self.M = formulation.M
        self.d = formulation.d
        self.dtot = formulation.dtot
        self.Q = formulation.Q
        self.sigma = formulation.sigma
        self.t_sto = formulation.t_sto
        

# Class modeling the Road Network Formulation (CBF) from the paper
class CustomerBasedFormulation(CmCTPRFormulation):
    def __init__(self, dat_path: str) -> None:
        super().__init__()
        self.Vp: set[int] = set()
        self.Ap: set[tuple[int, int]] = set()
        formulation = CmCTPRFormulation.parse_instance_file(dat_path)
        self.coords = formulation.coords
        self.W = formulation.W
        self.c = formulation.c
        self.V_sto = formulation.V_sto
        self.V_rank = formulation.V_rank
        self.M = formulation.M
        self.d = formulation.d
        self.dtot = formulation.dtot
        self.Q = formulation.Q
        self.sigma = formulation.sigma
        self.t_sto = formulation.t_sto
        # DERIVE Vp
        self.Vp = formulation.V_sto.union({formulation.sigma})
        # DERIVE A' with shortest-path costs
        for j in self.Vp:
            for jp in self.Vp:
                self.Ap.add((j, jp))
                time = dijkstra_min_cost(
                        start=j,
                        end=jp,
                        nodes=formulation.V | formulation.W,
                        arcs=formulation.A,
                        costs=formulation.c,
                    )
                if time == math.inf:
                    raise ValueError(f"No path from {j} to {jp} in the underlying road network")   
                self.c[(j, jp)] = time

# Helper function to calculate shortest path between nodes using Dijkstra
def dijkstra_min_cost(
    start: int,
    end: int,
    nodes: set[int],
    arcs: set[tuple[int, int]],
    costs: dict[tuple[int, int], float],
) -> float:
    """
    Heap-based Dijkstra on a directed graph with float arc costs.

    Returns the minimum path cost from start to end, or math.inf if unreachable.
    Requires non-negative arc costs.
    """
    if start not in nodes or end not in nodes:
        return math.inf
    if start == end:
        return 0.0

    # adjacency list: node -> list[(neighbor, weight)]
    adj: dict[int, list[tuple[int, float]]] = {u: [] for u in nodes}
    for (u, v) in arcs:
        w = costs.get((u, v))
        if w is None:
            continue
        # Optional: enforce Dijkstra precondition
        if w < 0:
            raise ValueError(f"Negative arc cost on ({u},{v}) = {w}; Dijkstra requires w >= 0.")
        adj[u].append((v, float(w)))

    dist: dict[int, float] = {u: math.inf for u in nodes}
    dist[start] = 0.0
    pq: list[tuple[float, int]] = [(0.0, start)]

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

    formulation = RoadNetworkFormulation(args.path)
    print("RNF OK")
    print("|W| =", len(formulation.W))
    sampleWnode = random.choice(list(formulation.W))
    print(f"W nodes keep an ordered list: W_{sampleWnode}'s favorites are: {formulation.V_rank[sampleWnode]} and produces {formulation.d[sampleWnode]} units of waste")
    n, m = random.choices(formulation.V_rank[sampleWnode], k=2)
    favorite = n if formulation.rank(sampleWnode, n) < formulation.rank(sampleWnode, m) else m
    print(f"Citizens at W_{sampleWnode} between V_{n} (position {formulation.rank(sampleWnode, n)}) and V_{m} (position {formulation.rank(sampleWnode, m)}) prefer V_{favorite}")
    print("|V| =", len(formulation.V))
    print("|A| =", len(formulation.A))
    print("|V_sto| =", len(formulation.V_sto))

    formulation_cbf = CustomerBasedFormulation(args.path)
    print("CBF OK")
    

if __name__ == "__main__":
    main()