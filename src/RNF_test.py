import gurobipy as gp
from gurobipy import GRB
from utils.formulation import RoadNetworkFormulation
import utils.circuits

# Create model
model = gp.Model("road-network_formulation")
VALID_INEQUALITY_ENABLED = True

instance = RoadNetworkFormulation()
instance.import_CmCTPRF("C:\\Users\\simon\\source\\repos\\mathematical-optimization\\data\\15-50-1.dat")

M = instance.M
d = instance.d
Q = instance.Q
sigma = instance.sigma
t_sto = instance.t_sto
V = instance.V
W = instance.W
A = instance.A
c = instance.c
V_rank = instance.V_rank
V_sto = instance.V_sto


# 1l
z = model.addVars([(i, j) for i in W for j in V_rank[i]], vtype=GRB.BINARY, name="z")
# 1k
y = model.addVars([(j, k) for j in V_sto for k in M], vtype=GRB.BINARY, name="y")
# 1j
x = model.addVars([(arc[0], arc[1], k) for arc in A for k in M], vtype=GRB.INTEGER, lb=0, name="x")

q = model.addVars([(j, k) for j in V_sto for k in M], vtype=GRB.CONTINUOUS, lb=0, name="q")
f = model.addVars([(arc[0], arc[1], k) for arc in A for k in M], vtype=GRB.CONTINUOUS, lb=0, name="f")


# 1b
model.addConstrs(
    (
        gp.quicksum(z[i, j] for j in V_rank[i]) == 1
        for i in W
    ),
    name="1b"
)
# 1c
model.addConstrs(
    (
        gp.quicksum(z[i, jp] for jp in V_rank[i] if instance.rank(i, jp) > instance.rank(i, j))
        <= 1 - y[j, k]
        for i in W
        for j in V_rank[i]
        for k in M
    ),
    name="1c"
)
# 1d
model.addConstrs(
    (
        gp.quicksum(d[i]*z[i, j] for i in W if j in V_rank[i])
        == gp.quicksum(q[j, k] for k in M)
        for j in V_sto
    ),
    name="1d"
)
# 1e
model.addConstrs(
    (
        gp.quicksum(q[j, k] for j in V_sto)
        <= Q
        for k in M
    ),
    name="1e"
)
# 1f
model.addConstrs(
    (
        gp.quicksum(x[h, j, k] for h in V if (h, j) in A) 
        >= y[j, k]
        for j in V_sto
        for k in M
    ),
    name="1f"
)
# 1g
model.addConstrs(
    (
        gp.quicksum(x[hp, h, k] for hp in V if (hp, h) in A) 
        - gp.quicksum(x[h, hp, k] for hp in V if (h, hp) in A) 
        == 0
        for h in V
        for k in M
    ),
    name="1g"
)
# 1h
model.addConstrs(
    (
        gp.quicksum(f[h, hp, k] for hp in V if (h, hp) in A)
        - gp.quicksum(f[hp, h, k] for hp in V if (hp, h) in A)
        == q[h, k]
        for k in M
        for h in V_sto
    ),
    name="1h_sto"
)
model.addConstrs(
    (
        gp.quicksum(f[h, hp, k] for hp in V if (h, hp) in A)
        - gp.quicksum(f[hp, h, k] for hp in V if (hp, h) in A)
        == 0
        for k in M
        for h in V.difference(V_sto.union({sigma}))
    ),
    name="1h_nonsto"
)

# 1i
model.addConstrs(
    (
        gp.quicksum(f[h, sigma, k] for h in V if (h, sigma) in A) 
        == gp.quicksum(q[j, k] for j in V_sto)
        for k in M
    ),
    name="1i"
)

# 1m
model.addConstrs(
    (
        q[j, k] <= Q*y[j, k]
        for j in V_sto
        for k in M
    ),
    name="1m"
)
# 1n
model.addConstrs(
    (
        f[arc[0], arc[1], k] <= Q*x[arc[0], arc[1], k]
        for arc in A
        for k in M
    ),
    name="1n"
)

# VALID INEQUALITIES
if VALID_INEQUALITY_ENABLED:
    s = model.addVars(V_sto, vtype=GRB.BINARY, name="s")

    # 2a
    model.addConstrs(
        (
            s[j] <= gp.quicksum(y[j, k] for k in M)
            for j in V_sto
        ),
        name="2a"
    )

    # 2b
    model.addConstrs(
        (
            s[j] >= y[j, k]
            for j in V_sto
            for k in M
        ),
        name="2b"
    )

    # 2c
    model.addConstr(
        (
            gp.quicksum(y[j, k] - s[j] for j in V_sto for k in M) <= len(M) - 1
        ),
        name="2c"
    )

# 1a
model.setObjective(
    gp.quicksum(c[arc]*x[arc[0], arc[1], k] for k in M for arc in A) 
    + gp.quicksum(t_sto*y[j, k] for k in M for j in V_sto), 
    GRB.MINIMIZE
)

# Optimize
TimeLimit = 60 * 60 * 3 # 3 HOURS
model.setParam("TimeLimit", TimeLimit)
model.optimize()


if model.status == GRB.INFEASIBLE:
    model.computeIIS()
    model.write("model.ilp")   # human-readable IIS
    print("Wrote IIS to model.ilp / model.iis")


# Print result
if model.status == GRB.OPTIMAL:
    print(f"Optimal objective value: {model.objVal}")
else:
    print("No optimal solution found.")


print("file name actually parsed")
print("|V_sto parsed|", len(instance.V_sto))
print("|rank union|", len(set().union(*instance.V_rank.values())))
print("Q", instance.Q)
print("sigma", instance.sigma)
print("c[153,11]", instance.c.get((153,11)))
print("c[11,153]", instance.c.get((11,153)))


print("Objective:", model.ObjVal)

if model.SolCount > 0:
    travel = sum(
        c[(h, hp)] * x[h, hp, k].X
        for (h, hp) in A
        for k in M
    )

    stops = sum(
        t_sto * y[j, k].X
        for j in V_sto
        for k in M
    )

    print("travel =", travel)
    print("stops =", stops)
    print("total =", travel + stops)
    print("number of stops =", sum(y[j, k].X for j in V_sto for k in M))

print("Selected stops:")
for j in sorted(V_sto):
    if sum(y[j, k].X for k in M) > 0.5:
        collected = sum(q[j, k].X for k in M)
        print(j, "collected =", collected)

print("Allocations:")
for i in sorted(W):
    for j in V_rank[i]:
        if z[i, j].X > 0 :
            print(
                f"demand {i} -> stop {j}, "
                f"demand={d[i]}, rank={instance.rank(i, j)}"
            )

print("Positive x arcs:")
for k in M:
    print("Tour", k)
    for (h, hp) in sorted(A):
        val = x[h, hp, k].X
        if val > 0.5:
            print((h, hp), "x =", val, "cost =", c[(h, hp)])

print("|V| =", len(instance.V))      # RN only
print("|A| =", len(instance.A))      # RN only
print("|W| =", len(instance.W))

tours = utils.circuits.extract_eulerian_tours(x, A, M, sigma)

for k, circuit in tours.items():
    nodes = utils.circuits.edges_to_nodes(circuit, sigma)

    print(f"Tour {k}:")
    print("Edges:", circuit)
    print("Nodes:", nodes)

    utils.circuits.plot_tour_with_order(x, A, k, sigma, instance.coords)
