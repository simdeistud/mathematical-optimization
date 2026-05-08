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

def is_a_cover_of(s1: set[int], s2: set[int]) -> bool:
    return s1.issuperset(s2)

def constructSet(Vp: set[int], W: set[int], V_rank: dict[int, list[int]], V_sto: set[int], sigma: float, Ap: dict[int, list[int]], c: dict[int, float]) -> tuple[set[int], float]:
    