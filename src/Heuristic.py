from utils.formulation import CustomerBasedFormulation, CVRPFormulation, SDVRPFormulation, HygeseFormulation
import random
import time
import math
import hygese as hgs

def solve(dat_path: str, TIME_LIMIT:int = 300):
    instance = CustomerBasedFormulation()
    instance.import_CmCTPRF(dat_path)

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
            i = random.choice(tuple(W.difference(W_cov)))  # Get a random uncovered node
            j_star = -1
            best_coverage = -1
            # We search for the stop node j* that covers demand node i
            # and which covers the most demand nodes than the others
            for j in V_rank[i]:
                W_j = {ip for ip in W if j in V_rank[ip]}  # Nodes in W that j can cover
                coverage = len(W_cov.union(W_j))
                if coverage > best_coverage:
                    best_coverage = coverage
                    j_star = j
            # Add the best candidate to the solution and update covered nodes
            V_sel.add(j_star)
            W_j_star = {ip for ip in W if j_star in V_rank[ip]}
            W_cov.update(W_j_star)  # Update covered nodes

        # We remove redundant stop nodes if there are any
        for j in V_sel.copy():
            if is_set_cover(V_sel.difference({j})):
                V_sel.remove(j)

        # W_compl[j] is the subset of demand nodes whose favorite stop node in V_sel is j
        W_compl: dict[int, set[int]] = {}
        for j in V_sel:
            W_compl[j] = set()
        for i in W:
            for j in V_rank[i]:
                # Since V_rank is an ordered list, we just need to find 
                # the first stop node in V_sel to find the best
                if j in V_sel:
                    W_compl[j].add(i)
                    break
        # V_alt[j] is the set of alternative stop nodes != j which cover W_compl[j]
        V_alt: dict[int, set[int]] = {}
        for j in V_sel:
            V_alt[j] = set()
            for jp in V_sto.difference({j}):
                W_j_p = {i for i in W if jp in V_rank[i]}
                if W_compl[j].issubset(W_j_p):
                    V_alt[j].add(jp)

        g: dict[int, frozenset[int]] = {j : frozenset({j}.union(V_alt[j])) for j in V_sel}
        G_avail: set[frozenset[int]] = set()
        for j in V_sel:
            G_avail.add(g[j])

        j = random.choice(tuple(V_sel))
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
                l: dict[frozenset[int], float] = {}
                for group in G_avail:
                    shortest: float = math.inf
                    for z in group:
                        current: float = c[(sigma, z)] + c[(z, sigma)]
                        if current < shortest:
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
                l: dict[frozenset[int], float] = {}
                for group in G_avail:
                    shortest: float = math.inf
                    for z in group:
                        current: float = c[(sigma, z)] + c[(z, sigma)]
                        if current < shortest:
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
        # We return the nodes selected into the giant tour
        final_V_sel = frozenset(giantTour[1:-1])
        return set(final_V_sel), giantTour_c

    best_set_covers: dict[frozenset[int], float] = {}
    treated_set_covers: dict[frozenset[int], float] = {}
    consecutive_without_improvement = 0
    elapsed_time = 0
    bestSol = (None, None, math.inf)
    while elapsed_time < TIME_LIMIT and consecutive_without_improvement < 100:
        iteration_start_time = time.time()
        # PHASE 1
        s, V_sel_cost = constructSet(Vp, W, V_rank, V_sto, sigma, Ap, c)
        V_sel = frozenset(s)
        if V_sel in treated_set_covers:
            if random.choice([0, 1]) == 0: continue # We penalize by skipping resolution with a random chance
        else:
            for cover in best_set_covers:
                if V_sel_cost < best_set_covers[cover]:
                    best_set_covers[V_sel] = V_sel_cost
                    break
        if len(best_set_covers) == 0:
            best_set_covers[V_sel] = V_sel_cost
        # PHASE 2
        V_sel: frozenset[int] = frozenset()
        V_sel_cost = math.inf
        for cover in best_set_covers:
            if best_set_covers[cover] < V_sel_cost:
                V_sel = cover
                V_sel_cost = best_set_covers[cover]
        V_sel_cost = best_set_covers.pop(V_sel)
        treated_set_covers[V_sel] = V_sel_cost

        # TransformSDVRPassociatedwith𝑉sel intoaCVRP
        SDVR = SDVRPFormulation()
        SDVR.import_CBF(instance, set(V_sel))
        CVRP = CVRPFormulation()
        CVRP.import_SDVRPF(SDVR)

        # Findsolutionof theCVRPwithHGS-CVRP:CVRPSol
        data = dict()
        HGS = HygeseFormulation()
        HGS.import_CVRPF(CVRP)
        data['distance_matrix'] = HGS.distance_matrix
        data['num_vehicles']  = HGS.num_vehicles
        data['depot'] = HGS.depot
        data['demands'] = HGS.demands
        data['vehicle_capacity'] = HGS.vehicle_capacity
        data['service_times'] = HGS.service_times
        ap = hgs.AlgorithmParameters(nbIter=10000) # N. of iterations without improvement
        hgs_solver = hgs.Solver(parameters=ap, verbose=True)
        CVRPSol = hgs_solver.solve_cvrp(data)
        #if CVRPSol.cost < bestSol[1]:
         #   bestSol = (CVRPSol, CVRPSol.cost)
          #  consecutive_without_improvement = 0
        # TransformCVRPSol intoaSDVRPsolution:SDVRPSol
        solution = instance.SDVRPF_solution_to_CBF(CVRP.solution_to_SDVRPF(HGS.solution_to_CVRPF(CVRPSol)))
        if solution[2] < bestSol[2]:
            bestSol = solution
            consecutive_without_improvement = 0
        else:
            consecutive_without_improvement += 1
        iteration_end_time = time.time()
        elapsed_time += iteration_end_time - iteration_start_time
    

    return bestSol[2], elapsed_time, bestSol
            



