import networkx as nx

def extract_eulerian_tours(x, A, M, sigma):
    """
    Extract Eulerian tours starting from node sigma.

    Parameters:
        x      : Gurobi tupledict
        A      : list of arcs [(i,j)]
        M      : list of tours
        sigma  : start node

    Returns:
        dict: k -> ordered list of edges in the tour
    """

    tours = {}

    for k in M:
        G = nx.MultiDiGraph()

        # build multigraph
        for (i, j) in A:
            val = x[i, j, k].X
            for _ in range(int(val)):
                G.add_edge(i, j)

        if G.number_of_edges() == 0:
            tours[k] = []
            continue

        # Eulerian circuit starting at sigma
        circuit = list(nx.eulerian_circuit(G, source=sigma))

        tours[k] = circuit

    return tours

def edges_to_nodes(circuit, sigma):
    """
    Convert edge list to node sequence starting from sigma
    """
    if not circuit:
        return []

    path = [sigma]

    for (_, j) in circuit:
        path.append(j)

    return path

import matplotlib.pyplot as plt

def plot_tour(x, A, k, sigma):
    G = nx.MultiDiGraph()

    # build graph
    for (i, j) in A:
        val = x[i, j, k].X
        for _ in range(int(val)):
            G.add_edge(i, j)

    pos = nx.spring_layout(G)

    # base graph
    nx.draw(G, pos, with_labels=True, node_color="lightblue", node_size=800)

    # extract Eulerian circuit
    circuit = list(nx.eulerian_circuit(G, source=sigma))
    edge_list = [(i, j) for (i, j) in circuit]

    # highlight tour
    nx.draw_networkx_edges(
        G, pos,
        edgelist=edge_list,
        edge_color='red',
        width=2
    )

    plt.title(f"Tour {k} (start = {sigma})")
    plt.show()
