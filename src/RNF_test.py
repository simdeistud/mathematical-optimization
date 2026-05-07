import math

import gurobipy as gp
from gurobipy import GRB
from utils.data_parser import RoadNetworkFormulation

# Create model
model = gp.Model("customer-graph_formulation")
VALID_INEQUALITY_ENABLED = True

instance = RoadNetworkFormulation.parse_instance_file("C:\\Users\\simone\\source\\repos\\mathematical-optimization\\data\\200-100-2.dat")

V = instance.V
W = instance.W
A = instance.A
c = instance.c
V_rank = instance.V_rank
V_sto = instance.V_sto
M = instance.M
d = instance.d
Q = instance.Q
sigma = instance.sigma
t_sto = instance.t_sto

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
    name="1f"
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