import networkx as nx
import matplotlib.pyplot as plt

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

def plot_tour(x, A, k, sigma):
    G = nx.MultiDiGraph()
    print(f"Plotting tour {k}")
    # build graph
    for (i, j) in A:
        val = x[i, j, k].X
        for _ in range(int(val)):
            G.add_edge(i, j)

    if not nx.is_eulerian(G):
        print("NOT Eulerian")
        #return        

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

def plot_tour_with_order(x, A, k, sigma, coords):
    G = nx.MultiDiGraph()

    for (i, j) in A:
        val = x[i, j, k].X
        for _ in range(int(val)):
            G.add_edge(i, j)

    pos = coords
    plt.figure()

    # draw nodes
    nx.draw_networkx(G, pos,
        node_color="lightblue",
        node_size=600,
        with_labels=True,
        arrows=False
    )

    circuit = list(nx.eulerian_circuit(G, source=sigma))

    # draw ordered traversal
    for idx, (i, j) in enumerate(circuit):
        x1, y1 = pos[i]
        x2, y2 = pos[j]

        plt.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(
                arrowstyle="->",
                color="red",
                lw=2
            )
        )

        # label step
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        plt.text(mx, my, str(idx), color="black", fontsize=8)

    plt.scatter(*pos[sigma], color="orange", s=200)

    plt.axis("equal")
    plt.title(f"Tour {k} with order")
    plt.show()

def main():
    A = {(1,2), (1,3), (3,1), (2,1), (2,3)}
    x = {
        (1,3,1) : 1,
        (3,1,1) : 1,
        (1,2,1) : 1,
        (2,1,1) : 1,
        (2,3,1) : 0
    }
    sigma = 1
    M = {1}
    tours = extract_eulerian_tours(x, A, M, sigma)
    for k, circuit in tours.items():
        nodes = edges_to_nodes(circuit, sigma)

        print(f"Tour {k}:")
        print("Edges:", circuit)
        print("Nodes:", nodes)

        plot_tour(x, A, k, sigma)
    

    

if __name__ == "__main__":
    main()