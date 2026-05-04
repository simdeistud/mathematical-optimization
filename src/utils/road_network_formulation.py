import gurobipy as gp
from gurobipy import GRB

# DATA DEFINITIONS
class Node:
    def __init__(self, id: int):
        self.id = id

    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Node):
            return self.id == other.id
        return False

class W_Node(Node):
    def __init__(self, id: int, waste: float, V_rank: list[int]):
        super().__init__(id)
        self.waste = waste
        # Order of preference for V nodes, from most preferred 
        # to least preferred (lower index = more preferred)
        self.V_rank = V_rank 

class V_Node(Node):
    def __init__(self, id: int):
        super().__init__(id)

class Edge:
    def __init__(self, i: int, j: int, c: int):
        self.i = i
        self.j = j
        self.c = c
    
    def __hash__(self) -> int:
        return hash((self.i, self.j))
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Edge):
            return self.i == other.i and self.j == other.j
        return False

class Graph:
    def __init__(self):
        self.nodes: set[Node] = set()
        self.edges: set[Edge] = set()

    def add_node(self, node: Node, edges_to: set[Edge] = set()):
        self.nodes.add(node)
        self.edges.update(edges_to)

    def __getitem__(self, id: int) -> Node:
        for node in self.nodes:
            if node.id == id:
                return node
        raise KeyError(f"Node with id {id} not found")

    def __iter__(self):
        return iter(self.nodes)

class CmCTPR_Instance:
    def __init__(self, graph: Graph, coordinates: dict[int, tuple[float, float]], sigma: int, gamma: int, m: int, Q: int, dtot: int):
        self._graph = graph
        self._nodes_coordinates = coordinates
        self._V_sto: set[int] = set()
        # Build V_sto (𝑉sto = ∪𝑖∈𝑊 𝑉𝑖rank)
        for node in self._graph.nodes:
            if isinstance(node, W_Node):
                self._V_sto.update(node.V_rank)
        self._depot_node: int = sigma
        self._max_walking_distance: int = gamma
        self._num_tours: int = m
        self._vehicle_capacity: int = Q
        self._total_waste: int = dtot
    
    def rank(self, i: int, j: int) -> int:
        node = self._graph[i]
        if isinstance(node, W_Node):
            return node.V_rank.index(j)
        raise TypeError(f"Node with id {i} is not a W_Node")
