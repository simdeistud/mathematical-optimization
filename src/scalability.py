import CBF
import RNF
import Heuristic
import os
import csv

TIME_LIMIT = 60 * 5 # 5 MINUTES

dirname = os.path.dirname(__file__)

cbf_cost, cbf_time = {}, {}
rnf_cost, rnf_time = {}, {}
heur_cost, heur_time = {}, {}

results = []

for nodes in [15, 50]:
    for gamma in [50, 100]:
        for tours in [1, 2, 6]:
            filename = os.path.join(dirname, f'../data/{nodes}-{gamma}-{tours}.dat')

            cbf_cost[(nodes, gamma, tours)], cbf_time[(nodes, gamma, tours)], _ = CBF.solve(filename, TIME_LIMIT)
            rnf_cost[(nodes, gamma, tours)], rnf_time[(nodes, gamma, tours)], _ = RNF.solve(filename, TIME_LIMIT)
            heur_cost[(nodes, gamma, tours)], heur_time[(nodes, gamma, tours)], _ = Heuristic.solve(filename, TIME_LIMIT)

            results.append([
                nodes, gamma, tours,
                cbf_cost[(nodes, gamma, tours)],
                cbf_time[(nodes, gamma, tours)],
                rnf_cost[(nodes, gamma, tours)],
                rnf_time[(nodes, gamma, tours)],
                heur_cost[(nodes, gamma, tours)],
                heur_time[(nodes, gamma, tours)],
            ])

csv_file = os.path.join(dirname, "../results/scalability.csv")

with open(csv_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "nodes", "gamma", "tours",
        "cbf_cost", "cbf_time",
        "rnf_cost", "rnf_time",
        "heur_cost", "heur_time"
    ])
    writer.writerows(results)

print(f"Results written to {csv_file}")