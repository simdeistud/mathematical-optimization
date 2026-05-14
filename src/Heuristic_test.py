from utils.data_parser import CustomerBasedFormulation
from typing import Dict, Tuple
import random
import time
import math
import hygese as hgs
import numpy as np 

class SDVRPFormulation:
    def __init__(self):
        self.V: set[int] = set()
        self.A: set[tuple[int, int]] = set()
        self.costs: dict[tuple[int, int], float] = {}
        self.depot: int = 0
        self.tours: set[int] = set()
        self.demands: dict[int, int] = {}
        self.capacity: float = 0
        self.t_sto: float = 0
    
    @staticmethod
    def from_CustomerBasedFormulation(formulation: CustomerBasedFormulation, V_sel: set[int]) -> SDVRPFormulation:
        result: SDVRPFormulation = SDVRPFormulation()
        result.V = V_sel
        result.A = {arc for arc in formulation.Ap if arc[0] in result.V and arc[1] in result.V}
        result.costs = {arc : formulation.c[arc] for arc in result.A}
        result.depot = formulation.sigma
        result.tours = formulation.M
        result.capacity = formulation.Q
        result.t_sto = formulation.t_sto
        assigned_collections: dict[int, int] = {}
        for w in formulation.W:
            favorite_collection: int
            for v in formulation.V_rank[w]:
                if v in V_sel:
                    favorite_collection = v
                    break
            assigned_collections[w] = favorite_collection
        aggregated_demands: dict[int, int] = {}
        for assignment in assigned_collections:
            if aggregated_demands.get(assigned_collections[assignment]) is None:
                aggregated_demands[assigned_collections[assignment]] = formulation.d[assignment]
            else:
                aggregated_demands[assigned_collections[assignment]] += formulation.d[assignment]
        result.demands = aggregated_demands
        return result

class CVRPFormulation:
    def __init__(self):
        self.V: set[int] = set()
        self.A: set[tuple[int, int]] = set()
        self.costs: dict[tuple[int, int], float] = {}
        self.depot: int = 0
        self.tours: set[int] = set()
        self.demands: Dict[int, int] = {}
        self.capacity: float = 0
        self.t_sto: float = 0
    
    
    @staticmethod
    def split_demand(demand: int, capacity: float) -> dict[int, int]:
        """
        Split a demand according to the 20/10/5/1 rule.

        Returns:
            {
                20: number of pieces of size 0.20 * capacity,
                10: number of pieces of size 0.10 * capacity,
                 5: number of pieces of size 0.05 * capacity,
                 1: number of pieces of size 0.01 * capacity,
            }

        Note:
            Any residual demand smaller than 0.01 * capacity is NOT represented
            by this return type. You need to handle it separately when creating
            actual CVRP pseudo-customers.
        """
        if demand < 0:
            raise ValueError("Demand must be non-negative.")
        if capacity <= 0:
            raise ValueError("Capacity must be positive.")

        remaining = float(demand)
        eps = 1e-9

        split: dict[int, int] = {}

        for pct in (20, 10, 5, 1):
            piece_size = (pct / 100.0) * capacity
            n_pieces = int(math.floor((remaining + eps) / piece_size))

            split[pct] = n_pieces
            remaining -= n_pieces * piece_size

            # Avoid tiny negative residuals due to floating point noise
            if abs(remaining) < eps:
                remaining = 0.0

        return split

    @staticmethod
    def from_SDVRPFormulation(formulation: SDVRPFormulation) -> CVRPFormulation:
        result: CVRPFormulation = CVRPFormulation()
        result.depot = formulation.depot
        result.tours = formulation.tours
        result.capacity = formulation.capacity
        result.t_sto = formulation.t_sto
        for v in formulation.V:
            if formulation.demands[v] > 0.1 * formulation.capacity:
            else:
                result.V.add(v)
                [result.A.add(arc) for arc in formulation.A if arc[0] == v or arc[1] == v]
                result.demands[v] = formulation.demands[v]
                [result.costs[arc] = formulation.costs[arc] for arc in formulation.A if arc[0] == v or arc[1] == v]
        return result



instance = CustomerBasedFormulation.parse_instance_file("C:\\Users\\simone\\source\\repos\\mathematical-optimization\\data\\15-50-1.dat")

Vp = instance.Vp
W = instance.W
Ap = instance.Ap
c = instance.c
V_rank = instance.V_rank
V_sto = instance.V_sto
M = instance.M
d = instance.d
Q = instance.Q
sigma = instance.sigma
t_sto = instance.t_sto

def is_set_cover(V_sel: set[int]) -> bool:
    cover_candidate: set[int] = set()
    # For each node in V_sel, add the corresponding nodes in W whose demand it satisfies
    for j in V_sel:
        for i in W:
            if j in V_rank[i]:
                cover_candidate.add(i)
    return cover_candidate.issuperset(W)

def constructSet(Vp: set[int], W: set[int], V_rank: dict[int, list[int]], V_sto: set[int], sigma: int, Ap: set[tuple[int, int]], c: dict[tuple[int, int], float]) -> tuple[set[int], float]:
    V_sel: set[int] = set()
    W_cov: set[int] = set()

    while not is_set_cover(V_sel):
        i = W.difference(W_cov).pop()  # Get an uncovered node
        j_star = -1
        W_j_star: set[int] = set()
        most_candidates_n = -1
        for j in V_rank[i]:
            W_j = {ip for ip in W if j in V_rank[ip]}  # Nodes in W that j can cover
            candidates_n = len(W_cov.union(W_j))
            if candidates_n > most_candidates_n:
                most_candidates_n = candidates_n
                j_star = j
                W_j_star = W_j
        # Add the best candidate to the solution and update covered nodes
        V_sel.add(j_star)
        W_cov.update(W_j_star)  # Update covered nodes
    
    for j in V_sel:
        if is_set_cover(V_sel.difference({j})):
            V_sel.remove(j)  # Remove redundant nodes
    
    W_compl: dict[int, set[int]] = {j : {i for i in W if V_rank[i][0] == j} for j in V_sel}
    V_alt: dict[int, set[int]] = {j : {jp for jp in V_sto.difference({j}) if W_compl[j].issubset({ip for ip in W if jp in V_rank[ip]})} for j in V_sel}
    
    g: dict[int, set[int]] = {j : {j}.union(V_alt[j]) for j in V_sel}
    G_avail: set[set[int]] = set()
    for j in V_sel:
        G_avail.add(g[j])

    j = V_sel.pop()
    V_sel.add(j)
    giantTour = [sigma, j, sigma]
    giantTour_c = c[(sigma, j)] + c[(j, sigma)]
    for group in G_avail.copy():
        if j in group:
            G_avail.remove(group)
    while len(G_avail) > 0:
        position = random.choice(["before", "after"])
        
        if position == "before":
            j = giantTour[1]
            s: dict[tuple[int, int], float] = {}
            l: dict[set[int], float] = {}
            for group in G_avail:
                shortest: float = -1
                for z in group:
                    current: float = c[(sigma, z)] + c[(z, sigma)]
                    if current < current:
                        shortest = current
                        l[group] = shortest
                for jp in group:
                    s[(jp, j)] = - l[group] - c[(sigma, j)] + c[(sigma, jp)] + c[(jp, j)]
            j_star = -1
            cost = math.inf
            for arc in s:
                if s[arc] < cost:
                    cost = s[arc]
                    j_star = arc[0]
            giantTour.insert(giantTour.index(j), j_star)
            giantTour_c += s[j_star, j]
            for group in G_avail.copy():
                if j_star in group:
                    G_avail.remove(group)

        if position == "after":
            j = giantTour[-2]
            s: dict[tuple[int, int], float] = {}
            l: dict[set[int], float] = {}
            for group in G_avail:
                shortest: float = -1
                for z in group:
                    current: float = c[(sigma, z)] + c[(z, sigma)]
                    if current < current:
                        shortest = current
                        l[group] = shortest
                for jp in group:
                    s[(j, jp)] = - l[group] - c[(j, sigma)] + c[(j, jp)] + c[(jp, sigma)]
            j_star = -1
            cost = math.inf
            for arc in s:
                if s[arc] < cost:
                    cost = s[arc]
                    j_star = arc[1]
            giantTour.insert(giantTour.index(j) + 1, j_star)
            giantTour_c += s[j, j_star]
            for group in G_avail.copy():
                if j_star in group:
                    G_avail.remove(group)
    cost_V_sel = giantTour_c
    return V_sel, cost_V_sel

def constructSet_LLM(Vp, W, V_rank, V_sto, sigma, Ap, c):
    # Precompute W_j = demand nodes coverable by stop j
    W_by_stop = {
        j: {i for i in W if j in V_rank[i]}
        for j in V_sto
    }

    def is_set_cover_local(V_sel):
        covered = set()
        for j in V_sel:
            covered |= W_by_stop[j]
        return covered >= W

    V_sel = set()
    W_cov = set()

    # 1) Build initial set cover
    while not is_set_cover_local(V_sel):
        i = random.choice(list(W - W_cov))

        j_star = max(
            V_rank[i],
            key=lambda j: len(W_cov | W_by_stop[j])
        )

        V_sel.add(j_star)
        W_cov |= W_by_stop[j_star]

    # 2) Remove redundant nodes
    for j in list(V_sel):
        if is_set_cover_local(V_sel - {j}):
            V_sel.remove(j)

    # 3) Compute demand assigned to each selected stop:
    #    j is selected if it is the best-ranked node among V_sel
    W_assigned = {j: set() for j in V_sel}

    for i in W:
        best_j = min(
            (j for j in V_sel if j in V_rank[i]),
            key=lambda j: V_rank[i].index(j)
        )
        W_assigned[best_j].add(i)

    # 4) Alternatives
    V_alt = {
        j: {
            jp for jp in V_sto - {j}
            if W_assigned[j] <= W_by_stop[jp]
        }
        for j in V_sel
    }

    groups = {
        j: {j} | V_alt[j]
        for j in V_sel
    }

    G_avail = list(groups.values())

    # 5) Start giant tour
    start = random.choice(list(V_sel))
    giantTour = [sigma, start, sigma]
    giantTour_c = c[(sigma, start)] + c[(start, sigma)]

    G_avail = [group for group in G_avail if start not in group]

    # Helper: l_g = min_z in group c[sigma,z] + c[z,sigma]
    def ell_group(group):
        return min(c[(sigma, z)] + c[(z, sigma)] for z in group)

    # 6) Insert one node per remaining group
    while G_avail:
        position = random.choice(["before", "after"])

        best_node = None
        best_delta = math.inf

        if position == "before":
            first = giantTour[1]

            for group in G_avail:
                ell_g = ell_group(group)

                for jp in group:
                    delta = (
                        -ell_g
                        - c[(sigma, first)]
                        + c[(sigma, jp)]
                        + c[(jp, first)]
                    )

                    if delta < best_delta:
                        best_delta = delta
                        best_node = jp

            giantTour.insert(1, best_node)

        else:
            last = giantTour[-2]

            for group in G_avail:
                ell_g = ell_group(group)

                for jp in group:
                    delta = (
                        -ell_g
                        - c[(last, sigma)]
                        + c[(last, jp)]
                        + c[(jp, sigma)]
                    )

                    if delta < best_delta:
                        best_delta = delta
                        best_node = jp

            giantTour.insert(len(giantTour) - 1, best_node)

        giantTour_c += best_delta

        # Remove all groups containing inserted node
        G_avail = [group for group in G_avail if best_node not in group]

    # Paper redefines V_sel as the nodes visited in the giant tour
    V_sel_final = set(giantTour[1:-1])

    return V_sel_final, giantTour_c

def SDVRPtoCVRP(formulation: CustomerBasedFormulation, V_sel: set[int]):
    formulation.Vp = V_sel.union({sigma})
    formulation.Ap = {arc for arc in formulation.Ap if arc[0] in formulation.Vp and arc[1] in formulation.Vp}
    formulation.c = {arc : formulation.c[arc] for arc in formulation.Ap}

def arcs_to_distance_matrix(nodes: set[int], costs: dict[tuple[int, int], float]) -> list[list[float]]:
    matrix: list[list[float]] = []
    for node in nodes:

    return matrix


def solve_CVRP(formulation: CustomerBasedFormulation) -> hgs.RoutingSolution:
    data = dict()
    data['distance_matrix'] = arcs_to_distance_matrix(formulation.Vp, formulation.c)
    [
        [0, 548, 776, 696, 582, 274, 502, 194, 308, 194, 536, 502, 388, 354, 468, 776, 662],
        [548, 0, 684, 308, 194, 502, 730, 354, 696, 742, 1084, 594, 480, 674, 1016, 868, 1210],
        [776, 684, 0, 992, 878, 502, 274, 810, 468, 742, 400, 1278, 1164, 1130, 788, 1552, 754],
        [696, 308, 992, 0, 114, 650, 878, 502, 844, 890, 1232, 514, 628, 822, 1164, 560, 1358],
        [582, 194, 878, 114, 0, 536, 764, 388, 730, 776, 1118, 400, 514, 708, 1050, 674, 1244],
        [274, 502, 502, 650, 536, 0, 228, 308, 194, 240, 582, 776, 662, 628, 514, 1050, 708],
        [502, 730, 274, 878, 764, 228, 0, 536, 194, 468, 354, 1004, 890, 856, 514, 1278, 480],
        [194, 354, 810, 502, 388, 308, 536, 0, 342, 388, 730, 468, 354, 320, 662, 742, 856],
        [308, 696, 468, 844, 730, 194, 194, 342, 0, 274, 388, 810, 696, 662, 320, 1084, 514],
        [194, 742, 742, 890, 776, 240, 468, 388, 274, 0, 342, 536, 422, 388, 274, 810, 468],
        [536, 1084, 400, 1232, 1118, 582, 354, 730, 388, 342, 0, 878, 764, 730, 388, 1152, 354],
        [502, 594, 1278, 514, 400, 776, 1004, 468, 810, 536, 878, 0, 114, 308, 650, 274, 844],
        [388, 480, 1164, 628, 514, 662, 890, 354, 696, 422, 764, 114, 0, 194, 536, 388, 730],
        [354, 674, 1130, 822, 708, 628, 856, 320, 662, 388, 730, 308, 194, 0, 342, 422, 536],
        [468, 1016, 788, 1164, 1050, 514, 514, 662, 320, 274, 388, 650, 536, 342, 0, 764, 194],
        [776, 868, 1552, 560, 674, 1050, 1278, 742, 1084, 810, 1152, 274, 388, 422, 764, 0, 798],
        [662, 1210, 754, 1358, 1244, 708, 480, 856, 514, 468, 354, 844, 730, 536, 194, 798, 0]
    ]
    data['num_vehicles'] = len(formulation.M)
    data['depot'] = formulation.sigma
    data['demands'] = [0, 1, 1, 2, 4, 2, 4, 8, 8, 1, 2, 1, 2, 4, 4, 8, 8]
    data['vehicle_capacity'] = formulation.Q
    data['service_times'] = np.full(shape=(1,len(data['demands'])), fill_value=formulation.t_sto)

    # Solver initialization
    TimeLimit = 60 * 60 * 3 # 3 HOURS
    ap = hgs.AlgorithmParameters(timeLimit=TimeLimit)
    hgs_solver = hgs.Solver(parameters=ap, verbose=True)

    # Solve
    result = hgs_solver.solve_cvrp(data)
    print(result.cost)
    print(result.routes)
    return result



best_set_covers: dict[set[int], float] = {}
treated_set_covers: dict[set[int], float] = {}
consecutive_without_improvement = 0
elapsed_time = 0
TIME_LIMIT: int = 10800
bestSol: tuple[set[int], float]
while elapsed_time < TIME_LIMIT and consecutive_without_improvement < 100:
    iteration_start_time = time.time()
    # PHASE 1
    V_sel, V_sel_cost = constructSet_LLM(Vp, W, V_rank, V_sto, sigma, Ap, c)
    if V_sel in treated_set_covers:
        treated_set_covers[V_sel] # penalized (how???)
    else:
        if V_sel_cost < max(best_set_covers, key=best_set_covers.get):
            best_set_covers[V_sel] = V_sel_cost
    # PHASE 2
    V_sel: set[int] = min(best_set_covers, key=best_set_covers.get)
    V_sel_cost = best_set_covers.pop(V_sel)
    treated_set_covers[V_sel] = V_sel_cost
    # TransformSDVRPassociatedwith𝑉sel intoaCVRP
    CVRP: set[int] = set()
    # Findsolutionof theCVRPwithHGS-CVRP:CVRPSol
    SDVRPSol: set[int] = set()
    SDVRPSol_cost: float = 0
    # TransformCVRPSol intoaSDVRPsolution:SDVRPSol
    if SDVRPSol_cost < bestSol[1]:
        bestSol = (SDVRPSol, SDVRPSol_cost)
    iteration_end_time = time.time()
    elapsed_time += iteration_end_time - iteration_start_time

        

    
            
        



