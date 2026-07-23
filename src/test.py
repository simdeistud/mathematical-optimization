import CBF
import RNF
import Heuristic
import os
from utils.eulerize import reconstruct_tours

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, '../data/15-0-2.dat')

#cbf_cost, cbf_time, _ = CBF.solve(filename)
rnf_cost, rnf_time, x = RNF.solve(filename)
#heur_cost, heur_time, _ = Heuristic.solve(filename)

print("Customer Based Formulation (MILP, Gurobi)")
#print(f"Execution time: {cbf_time} seconds")
#print(f"Best solution: {cbf_cost} seconds")
print("=======================================")
print("Road Network Formulation (MILP, Gurobi)")
print(f"Execution time: {rnf_time} seconds")
print(f"Best solution: {rnf_cost} seconds")
print(f"Tours: {reconstruct_tours(x)}")
print("=======================================")
print("Capacitated Vehicle Routing Formulation (Genetic Algorithm, Hygese)")
#print(f"Execution time: {heur_time} seconds")
#print(f"Best solution: {heur_cost} seconds")
print("=======================================")