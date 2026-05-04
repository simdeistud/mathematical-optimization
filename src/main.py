import math

import gurobipy as gp
from gurobipy import GRB
from utils.data_importer import parse_instance_file
from utils.road_network_formulation import *

# Create model
model = gp.Model("customer-graph_formulation")

instance = parse_instance_file("data\\15-50-1.dat")

v_nodes = set(node.id for node in instance._graph.nodes)
w_nodes = set(node.id for node in instance._graph.nodes if isinstance(node, W_Node))
arcs, cost = gp.multidict({(edge.i, edge.j): edge.c for edge in instance._graph.edges})
v_ranks = {node.id: node.V_rank for node in instance._graph.nodes if isinstance(node, W_Node)}
v_sto = instance._V_sto
m = list(range(1, instance._num_tours + 1))
waste = {node.id: node.waste for node in instance._graph.nodes if isinstance(node, W_Node)}
Q = max(instance._vehicle_capacity, math.ceil(1.05 * instance._total_waste / len(m)))

sigma = instance._depot_node
t_sto = 5

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
    for h in v_nodes.difference(v_sto.union({instance._depot_node})):
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