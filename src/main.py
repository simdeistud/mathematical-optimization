import math

import gurobipy as gp
from gurobipy import GRB
from utils.data_parser import RoadNetworkFormulation

# Create model
model = gp.Model("customer-graph_formulation")

instance = RoadNetworkFormulation.parse_instance_file("C:\\Users\\simone\\source\\repos\\mathematical-optimization\\data\\200-100-2.dat")

v_nodes = instance.v_nodes
w_nodes = instance.w_nodes
arcs = instance.arcs
cost = instance.cost
v_ranks = instance.v_ranks
v_sto = instance.v_sto
m = instance.M
waste = instance.demand
Q = instance.Q
sigma = instance.sigma
t_sto = instance.t_sto

# 1l
z = model.addVars([(i, j) for i in w_nodes for j in v_ranks[i]], vtype=GRB.BINARY, name="z")
# 1k
y = model.addVars([(j, k) for j in v_sto for k in m], vtype=GRB.BINARY, name="y")
# 1j
x = model.addVars([(arc[0], arc[1], k) for arc in arcs for k in m], vtype=GRB.INTEGER, lb=0, name="x")

q = model.addVars([(j, k) for j in v_sto for k in m], vtype=GRB.CONTINUOUS, lb=0, name="q")
f = model.addVars([(arc[0], arc[1], k) for arc in arcs for k in m], vtype=GRB.CONTINUOUS, lb=0, name="f")


# 1b
model.addConstrs(
    (
        gp.quicksum(z[i, j] for j in v_ranks[i]) == 1
        for i in w_nodes
    ),
    name="1b"
)
# 1c
model.addConstrs(
    (
        gp.quicksum(z[i, jp]for jp in v_ranks[i]if instance.rank(i, jp) > instance.rank(i, j))
        <= 1 - y[j, k]
        for i in w_nodes
        for j in v_ranks[i]
        for k in m
    ),
    name="1c"
)
# 1d
model.addConstrs(
    (
        gp.quicksum(waste[i]*z[i, j] for i in w_nodes if j in v_ranks[i])
        == gp.quicksum(q[j, k] for k in m)
        for j in v_sto
    ),
    name="1d"
)
# 1e
model.addConstrs(
    (
        gp.quicksum(q[j, k]for j in v_sto)
        <= Q
        for k in m
    ),
    name="1e"
)
# 1f
model.addConstrs(
    (
        gp.quicksum(x[h, j, k] for h in v_nodes if (h, j) in arcs) 
        >= y[j, k]
        for j in v_sto
        for k in m
    ),
    name="1f"
)
# 1g
model.addConstrs(
    (
        gp.quicksum(x[hp, h, k] for hp in v_nodes if (hp, h) in arcs) 
        - gp.quicksum(x[h, hp, k] for hp in v_nodes if (h, hp) in arcs) 
        == 0
        for h in v_nodes
        for k in m
    ),
    name="1f"
)
# 1h
model.addConstrs(
    (
        gp.quicksum(f[h, hp, k] for hp in v_nodes if (h, hp) in arcs)
        - gp.quicksum(f[hp, h, k] for hp in v_nodes if (hp, h) in arcs)
        == q[h, k]
        for k in m
        for h in v_sto
    ),
    name="1h_sto"
)
model.addConstrs(
    (
        gp.quicksum(f[h, hp, k] for hp in v_nodes if (h, hp) in arcs)
        - gp.quicksum(f[hp, h, k] for hp in v_nodes if (hp, h) in arcs)
        == 0
        for k in m
        for h in v_nodes.difference(v_sto.union({sigma}))
    ),
    name="1h_nonsto"
)

# 1i
model.addConstrs(
    (
        gp.quicksum(f[h, sigma, k] for h in v_nodes if (h, sigma) in arcs) 
        == gp.quicksum(q[j, k] for j in v_sto)
        for k in m
    ),
    name="1i"
)

# 1m
model.addConstrs(
    (
        q[j, k] <= Q*y[j, k]
        for j in v_sto
        for k in m
    ),
    name="1m"
)
# 1n
model.addConstrs(
    (
        f[arc[0], arc[1], k] <= Q*x[arc[0], arc[1], k]
        for arc in arcs
        for k in m
    ),
    name="1n"
)

# 1a
model.setObjective(
    gp.quicksum(cost[arc]*x[arc[0], arc[1], k] for k in m for arc in arcs) 
    + gp.quicksum(t_sto*y[j, k] for k in m for j in v_sto), 
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