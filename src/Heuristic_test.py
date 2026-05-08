from utils.data_parser import CustomerBasedFormulation

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

def constructSet(Vp: set[int], W: set[int], V_rank: dict[int, list[int]], V_sto: set[int], sigma: float, Ap: dict[int, list[int]], c: dict[int, float]) -> tuple[set[int], float]:
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
    G_avail: set[int] = set()
    for j in g:
        if j in V_sel:
            G_avail.update(g[j])

    
            
        



