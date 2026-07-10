import heapq
import math
import random
import argparse
import itertools

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
                elif line.startswith("VehicleQ"):
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
    def __init__(self) -> None:
        # The RNF follows naturally from the given instance files, so no processing is needed
        super().__init__()
    
    def import_CmCTPRF(self, dat_path: str):
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
    def __init__(self) -> None:
        super().__init__()
        self.Vp: set[int] = set()
        self.Ap: set[tuple[int, int]] = set()
        
    def import_CmCTPRF(self, dat_path: str):
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

class SDVRPFormulation:
    def __init__(self):
        self.V: set[int] = set()
        self.A: set[tuple[int, int]] = set()
        self.costs: dict[tuple[int, int], float] = {}
        self.tours: set[int] = set()
        self.demands: dict[int, float] = {}
        self.Q: int = 0
        self.depot: int = 0
        self.t_sto: float = 0

    def import_CBF(self, formulation: CustomerBasedFormulation, V_sel: set[int]):
        self.V = V_sel.union({formulation.sigma})
        # We remove arcs and costs that are not related to V_sel nodes
        self.A = {arc for arc in formulation.Ap if arc[0] in self.V and arc[1] in self.V and arc[0] != arc[1]}
        self.costs = {arc : formulation.c[arc] for arc in self.A}
        self.depot = formulation.sigma
        self.tours = formulation.M
        self.Q = formulation.Q
        self.t_sto = formulation.t_sto
        # For each demand node, we take its first favourite disposal location that is also in V_sel.
        # Then, we associate and aggregate its demand to the V_sel node.
        for v in self.V:
            self.demands[v] = 0
        for w in formulation.W:
            for v in formulation.V_rank[w]:
                if v in self.V:
                    self.demands[v] += formulation.d[w]
                    break

class CVRPFormulation:
    def __init__(self):
        self.V: set[int] = set()
        self.A: set[tuple[int, int]] = set()
        self.costs: dict[tuple[int, int], float] = {}
        self.tours: set[int] = set()
        self.demands: dict[int, float] = {}
        self.Q: int = 0
        self.depot: int = 0
        self.t_sto: float = 0
        self._splits_mapping: dict[int, set[int]] = {}
    
    def import_SDVRPF(self, formulation: SDVRPFormulation):
        self.V = formulation.V.copy()
        self.A = formulation.A.copy()
        self.costs = formulation.costs.copy()
        self.depot = formulation.depot
        self.tours = formulation.tours.copy()
        self.demands = formulation.demands.copy()
        self.Q = formulation.Q
        self.t_sto = formulation.t_sto
        # For each node whose demand exceeds 0.1*Q we split it into new nodes using the heuristic
        # delineated in the paper. This means adding new nodes and new arcs, and needing to
        # keep track of the splits to convert back to the SDVRP formulation.
        for v in formulation.V:
            # We don't split nodes with small demand
            if formulation.demands[v] < 0.1*formulation.Q:
                continue
            m_20: int = math.floor((formulation.demands[v]) / (0.2*formulation.Q))
            m_10: int = math.floor((formulation.demands[v] - m_20*0.2*formulation.Q) / (0.1*formulation.Q))
            m_5: int = math.floor((formulation.demands[v] - m_20*0.2*formulation.Q - m_10*0.1*formulation.Q) / (0.05*formulation.Q))
            m_1: int = math.floor((formulation.demands[v] - m_20*0.2*formulation.Q - m_10*0.1*formulation.Q - m_5*0.05*formulation.Q) / (0.01*formulation.Q))
            residue: float = formulation.demands[v] - m_20*0.2*formulation.Q - m_10*0.1*formulation.Q - m_5*0.05*formulation.Q - m_1*0.01*formulation.Q
            # We create a LUT to create nodes and arcs easier
            splits_dict = {
                0.2 : m_20,
                0.1 : m_10,
                0.05 : m_5,
                0.01 : m_1,
                residue/formulation.Q : 1 if residue != 0 else 0 # We use this trick to use the same logic for the residual case since new_demand = residue/Q * Q = residue
            }
            # We find the node with the biggest index and create new nodes starting from that
            max_node: int = max(self.V)
            c: int = 1
            # We split the node
            for split in splits_dict:
                for _ in range(0, splits_dict[split]):
                    new_node = max_node + c
                    new_demand = split*formulation.Q
                    # Add the split to the nodes
                    self.V.add(new_node)
                    if v not in self._splits_mapping: 
                        self._splits_mapping[v] = {new_node}
                    else: 
                        self._splits_mapping[v].add(new_node)
                    # Add the split node to the split demand
                    self.demands[new_node] = new_demand
                    # Create new arcs
                    for arc in self.A.copy():
                        # We don't account for self loops as they should be impossible
                        if arc[0] == v:
                            new_arc = (new_node, arc[1])
                            self.A.add(new_arc)
                            self.costs[new_arc] = self.costs[arc]
                        if arc[1] == v:
                            new_arc = (arc[0], new_node)
                            self.A.add(new_arc)
                            self.costs[new_arc] = self.costs[arc]
                    c += 1
            # We now connect all the new nodes to eachother with cost 0
            combinations = itertools.product(self._splits_mapping[v], self._splits_mapping[v])
            for arc in combinations:
                if arc[0] != arc[1]:
                    self.A.add(arc)
                    self.costs[arc] = 0
            # Now we remove the original node and its information
            self.V.remove(v)
            self.A = {arc for arc in self.A if arc[0] != v and arc[1] != v}
            self.costs = {arc : self.costs[arc] for arc in self.A}
            self.demands.pop(v)
    
class HygeseFormulation:
    def __init__(self):
        self.nodes: list[int] = []
        self.distance_matrix: list[list[float]] = []
        self.num_vehicles: int = 0
        self.depot: int = 0
        self.demands: list[float] = []
        self.vehicle_capacity = 0
        self.service_times = []
        self._depot_swap: int = 0

    def import_CVRPF(self, formulation: CVRPFormulation):
        # Hygese wants the depot at 0, so we need to perform a swap if the 0 index is already occupied by a node
        self.depot = 0
        if formulation.depot != 0:
            swapped_formulation = CVRPFormulation()
            swapped_formulation.V = formulation.V
            self._depot_swap = formulation.depot

            # We set the depot demand
            swapped_formulation.demands = formulation.demands
            if 0 in formulation.V:
                swapped_demand = formulation.demands[0]
                swapped_formulation.demands[self._depot_swap] = swapped_demand
            else:
                swapped_formulation.V.remove(self._depot_swap)
                swapped_formulation.V.add(0)
            swapped_formulation.demands[0] = 0

            # We swap the arcs and their costs
            swapped_formulation.A = set()
            swapped_formulation.costs = {}
            for arc in formulation.A:
                new_arc = arc
                if arc[0] == 0 and arc[1] == self._depot_swap or arc[1] == 0 and arc[0] == self._depot_swap:
                    new_arc = (arc[1], arc[0])
                elif arc[0] == 0:
                    new_arc = (self._depot_swap, arc[1])
                elif arc[1] == 0:
                    new_arc = (arc[0], self._depot_swap)
                elif arc[0] == self._depot_swap:
                    new_arc = (0, arc[1])
                elif arc[1] == self._depot_swap:
                    new_arc = (arc[0], 0)
                swapped_formulation.A.add(new_arc)
                swapped_formulation.costs[new_arc] = formulation.costs[arc]

            swapped_formulation.tours = formulation.tours
            swapped_formulation.Q = formulation.Q
            swapped_formulation.depot = 0
            swapped_formulation.t_sto = formulation.t_sto
            swapped_formulation._splits_mapping = {}
            
            formulation = swapped_formulation
            pass # FIX IF NEEDED
        # We turn the nodes into an ordered list
        self.nodes = sorted(list(formulation.V))
        # We add their demands and service times in order, depot demand and t_sto must be zero
        for node in self.nodes:
            demand = 0
            service_time = 0
            if node != 0:
                demand = formulation.demands[node]
                service_time = formulation.t_sto
            self.demands.append(demand)
            self.service_times.append(service_time)
        # We build the distance matrix
        for src in self.nodes:
            distance_vector: list[float] = []
            for dst in self.nodes:
                distance: float = 0
                if dst != src:
                    distance = formulation.costs[(src, dst)]
                distance_vector.append(distance)
            self.distance_matrix.append(distance_vector)
        self.num_vehicles = len(formulation.tours)
        self.vehicle_capacity = formulation.Q        

def main():
    #ap = argparse.ArgumentParser(description="Parse Cm-CTP-R instance text file into CmCTPR_Instance.")
    #ap.add_argument("path", type=str, help="Path to instance file")
    #args = ap.parse_args()

    formulation = RoadNetworkFormulation()
    formulation.import_CmCTPRF("C:\\Users\\simon\\source\\repos\\mathematical-optimization\\data\\15-100-6.dat")
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

    formulation_cbf = CustomerBasedFormulation()
    formulation_cbf.import_CmCTPRF("C:\\Users\\simon\\source\\repos\\mathematical-optimization\\data\\15-100-6.dat")
    print("CBF OK")
    formulation_sdvrp =  SDVRPFormulation()
    formulation_sdvrp.import_CBF(formulation_cbf, {5, 6, 7, 153})
    formulation_cvrp = CVRPFormulation()
    formulation_cvrp.import_SDVRPF(formulation_sdvrp)
    formulation_hgs = HygeseFormulation()
    formulation_hgs.import_CVRPF(formulation_cvrp)
    formulation_hgs.distance_matrix
    import hygese as hgs
    data = dict()
    data['distance_matrix'] = formulation_hgs.distance_matrix
    data['num_vehicles']  = formulation_hgs.num_vehicles
    data['depot'] = formulation_hgs.depot
    data['demands'] = formulation_hgs.demands
    data['vehicle_capacity'] = formulation_hgs.vehicle_capacity
    data['service_times'] = formulation_hgs.service_times
    ap = hgs.AlgorithmParameters(nbIter=10000) # N. of iterations without improvement
    hgs_solver = hgs.Solver(parameters=ap, verbose=True)

    # Solve
    result = hgs_solver.solve_cvrp(data)
    print(result.cost)
    print(result.routes)

if __name__ == "__main__":
    main()