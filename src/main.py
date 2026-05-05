import math

import gurobipy as gp
from gurobipy import GRB
from utils.data_parser import RoadNetworkFormulation

# Create model
model = gp.Model("customer-graph_formulation")

instance = RoadNetworkFormulation.parse_instance_file("C:\\Users\\simone\\source\\repos\\mathematical-optimization\\data\\15-0-1.dat")

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
z = model.addVars([(i, j) for i in w_nodes for j in v_nodes], vtype=GRB.BINARY, name="z")
# 1k
y = model.addVars([(j, k) for j in v_sto for k in m], vtype=GRB.BINARY, name="y")
# 1j
x = model.addVars([(arc[0], arc[1], k) for arc in arcs for k in m], vtype=GRB.INTEGER, lb=0, name="x")

q = model.addVars([(j, k) for j in v_sto for k in m], vtype=GRB.CONTINUOUS, lb=0, name="q")
f = model.addVars([(arc[0], arc[1], k) for arc in arcs for k in m], vtype=GRB.CONTINUOUS, lb=0, name="f")

# 1b
for i in w_nodes:
    model.addConstr(gp.quicksum(z[i, j] for j in v_nodes if j in v_ranks[i]) == 1, name=f"1b_{i}")
# 1c
for i in w_nodes:
    for j in v_ranks[i]:
        for k in m:
            model.addConstr(gp.quicksum(z[i, jp] for jp in v_ranks[i] if instance.rank(i, jp) > instance.rank(i, j)) <= 1 - y[j, k], name=f"1c_{i}_{j}_{k}")
# 1d
for j in v_sto:
    model.addConstr(gp.quicksum(waste[i]*z[i, j] for i in w_nodes if j in v_ranks[i]) == gp.quicksum(q[j, k] for k in m), name=f"1d_{j}")
# 1e
for k in m:
    model.addConstr(gp.quicksum(q[j, k] for j in v_sto) <= Q, name=f"1e_{k}")
# 1f
for j in v_sto:
    for k in m:
        model.addConstr(gp.quicksum(x[h, j, k] for h in v_nodes if (h, j) in arcs) >= y[j, k], name=f"1f_{j}_{k}")
# 1g
for h in v_nodes:
    for k in m:
        model.addConstr(gp.quicksum(x[hp, h, k] for hp in v_nodes if (hp, h) in arcs) - gp.quicksum(x[h, hp, k] for hp in v_nodes if (h, hp) in arcs) == 0, name=f"1g_{h}_{k}")
# 1h
for k in m:
    for h in v_sto:
        model.addConstr(gp.quicksum(f[h, hp, k] for hp in v_nodes if (h, hp) in arcs) - gp.quicksum(f[hp, h, k] for hp in v_nodes if (hp, h) in arcs) == q[h, k], name=f"1h_{h}_{k}")
    for h in v_nodes.difference(v_sto.union({sigma})):
        model.addConstr(gp.quicksum(f[h, hp, k] for hp in v_nodes if (h, hp) in arcs) - gp.quicksum(f[hp, h, k] for hp in v_nodes if (hp, h) in arcs) == 0, name=f"1h_{h}_{k}")
# 1i
for k in m:
    model.addConstr(gp.quicksum(f[h, sigma, k] for h in v_nodes if (h, sigma) in arcs) == gp.quicksum(q[j, k] for j in v_sto), name=f"1i_{k}")

# 1m
for j in v_sto:
    for k in m:
        model.addConstr(q[j, k] <= Q*y[j, k], name=f"1m_{j}_{k}")
# 1n
for arc in arcs:
    for k in m:
        model.addConstr(f[arc[0], arc[1], k] <= Q*x[arc[0], arc[1], k], name=f"1n_{arc}_{k}")

# 1a
model.setObjective(gp.quicksum(cost[arc]*x[arc[0], arc[1], k] for k in m for arc in arcs) + gp.quicksum(t_sto*y[j, k] for k in m for j in v_sto), GRB.MINIMIZE)

# Optimize
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