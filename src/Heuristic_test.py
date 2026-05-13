from utils.data_parser import CustomerBasedFormulation
from typing import Dict, Tuple
import random
import time
import math

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

best_set_covers: dict[set[int], float] = {}
treated_set_covers: dict[set[int], float] = {}
consecutive_without_improvement = 0
elapsed_time = 0
TIME_LIMIT: int = 10800
bestSol: tuple[set[int], float]
while elapsed_time < TIME_LIMIT and consecutive_without_improvement < 100:
    iteration_start_time = time.time()
    # PHASE 1
    V_sel, V_sel_cost = constructSet(Vp, W, V_rank, V_sto, sigma, Ap, c)
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

        

    
            
        



