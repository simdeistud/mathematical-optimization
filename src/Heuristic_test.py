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

