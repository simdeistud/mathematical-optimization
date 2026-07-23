import gurobipy as gp
from gurobipy import GRB
from utils.formulation import CustomerBasedFormulation

def solve(dat_path: str, TIME_LIMIT:int = 300):
    # Create model
    model = gp.Model("customer-based_formulation")
    VALID_INEQUALITY_ENABLED = True

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

    # 4l
    z = model.addVars([(i, j) for i in W for j in V_rank[i]], vtype=GRB.BINARY, name="z")
    # 4k
    y = model.addVars([(j, k) for j in V_sto for k in M], vtype=GRB.BINARY, name="y")
    # 4j
    x = model.addVars([(j, jp, k) for j in Vp for jp in Vp for k in M], vtype=GRB.INTEGER, lb=0, name="x")

    q = model.addVars([(j, k) for j in V_sto for k in M], vtype=GRB.CONTINUOUS, lb=0, name="q")
    f = model.addVars([(j, jp, k) for j in Vp for jp in Vp for k in M], vtype=GRB.CONTINUOUS, lb=0, name="f")


    # 4b
    model.addConstrs(
        (
            gp.quicksum(z[i, j] for j in V_rank[i]) == 1
            for i in W
        ),
        name="4b"
    )
    # 4c
    model.addConstrs(
        (
            gp.quicksum(z[i, jp] for jp in V_rank[i] if instance.rank(i, jp) > instance.rank(i, j))
            <= 1 - y[j, k]
            for i in W
            for j in V_rank[i]
            for k in M
        ),
        name="4c"
    )
    # 4d
    model.addConstrs(
        (
            gp.quicksum(d[i]*z[i, j] for i in W if j in V_rank[i])
            == gp.quicksum(q[j, k] for k in M)
            for j in V_sto
        ),
        name="4d"
    )
    # 4e
    model.addConstrs(
        (
            gp.quicksum(q[j, k] for j in V_sto)
            <= Q
            for k in M
        ),
        name="4e"
    )
    # 4f
    model.addConstrs(
        (
            gp.quicksum(x[jp, j, k] for jp in Vp) 
            == y[j, k]
            for j in V_sto
            for k in M
        ),
        name="4f"
    )
    # 4g
    model.addConstrs(
        (
            gp.quicksum(x[jp, j, k] for jp in Vp) 
            - gp.quicksum(x[j, jp, k] for jp in Vp) 
            == 0
            for j in Vp
            for k in M
        ),
        name="4g"
    )
    # 4h
    model.addConstrs(
        (
            gp.quicksum(f[j, jp, k] for jp in Vp)
            - gp.quicksum(f[jp, j, k] for jp in Vp)
            == q[j, k]
            for j in V_sto
            for k in M
        ),
        name="4h"
    )

    # 4i
    model.addConstrs(
        (
            gp.quicksum(f[jp, sigma, k] for jp in Vp) 
            == gp.quicksum(q[j, k] for j in V_sto)
            for k in M
        ),
        name="4i"
    )

    # 4m
    model.addConstrs(
        (
            q[j, k] <= Q*y[j, k]
            for j in V_sto
            for k in M
        ),
        name="4m"
    )
    # 4n
    model.addConstrs(
        (
            f[j, jp, k] <= Q*x[j, jp, k]
            for j in Vp
            for jp in Vp
            for k in M
        ),
        name="4n"
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

    # 4a
    model.setObjective(
        gp.quicksum(c[arc]*x[arc[0], arc[1], k] for k in M for arc in Ap) 
        + gp.quicksum(t_sto*y[j, k] for k in M for j in V_sto), 
        GRB.MINIMIZE
    )

    # Optimize
    model.setParam("TimeLimit", TIME_LIMIT)
    model.optimize()

    # Copy the optimized x values into an ordinary Python dictionary.
    # Only positive arcs are required for Eulerian reconstruction.
    x_values = {
        key: int(round(var.X))
        for key, var in x.items()
        if var.X > 1e-6
    }
    
    return model.objVal, model.Runtime, x_values