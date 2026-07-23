import CBF
import RNF
import Heuristic
import os
from utils.formulation import CmCTPRFormulation
from utils.eulerize import reconstruct_tours
from utils.tour_satellite_export import export_tours

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, '../data/15-200-2.dat')
instance = CmCTPRFormulation.parse_instance_file(filename)
coords = instance.coords

#cbf_cost, cbf_time, _ = CBF.solve(filename)
rnf_cost, rnf_time, rnf_x = RNF.solve(filename)
#heur_cost, heur_time, heur_x = Heuristic.solve(filename)

print("Customer Based Formulation (MILP, Gurobi)")
#print(f"Execution time: {cbf_time} seconds")
#print(f"Best solution: {cbf_cost} seconds")
print("=======================================")
print("Road Network Formulation (MILP, Gurobi)")
#print(f"Execution time: {rnf_time} seconds")
#print(f"Best solution: {rnf_cost} seconds")
print("=======================================")
print("Capacitated Vehicle Routing Formulation (Genetic Algorithm, Hygese)")
#print(f"Execution time: {heur_time} seconds")
#print(f"Best solution: {heur_cost} seconds")
print("=======================================")

tours = reconstruct_tours(rnf_x, start_nodes={k : instance.sigma for k in instance.M})
tours_nodepot = []
for tour in tours:
    tours_nodepot.append(tour[1:-1])
export_tours(tours_nodepot, coords, filename_prefix="rnf")

#tours = reconstruct_tours(rnf_x)
tours_nodepot = []
for tour in heur_x[0]:
    tours_nodepot.append(tour[1:-1])
export_tours(tours_nodepot, coords, filename_prefix="heur")