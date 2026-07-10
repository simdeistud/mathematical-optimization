import CBF
import RNF
import Heuristic
import os

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, '../data/15-50-2.dat')

cbf_cost, cbf_time = CBF.solve(filename)
rnf_cost, rnf_time = RNF.solve(filename)
heur_cost, heur_time = Heuristic.solve(filename)

print("Customer Based Formulation (MILP, Gurobi)")
print(f"Execution time: {cbf_time} seconds")
print(f"Best solution: {cbf_cost} seconds")
print("=======================================")
print("Road Network Formulation (MILP, Gurobi)")
print(f"Execution time: {rnf_time} seconds")
print(f"Best solution: {rnf_cost} seconds")
print("=======================================")
print("Capacitated Vehicle Routing Formulation (Genetic Algorithm, Hygese)")
print(f"Execution time: {heur_time} seconds")
print(f"Best solution: {heur_cost} seconds")
print("=======================================")