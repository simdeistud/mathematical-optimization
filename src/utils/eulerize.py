"""Eulerian tour reconstruction utilities for Gurobi solutions.

This module converts integer-valued Gurobi arc variables

    x[i, j, k] = number of times directed arc (i, j) is traversed
                 by tour/vehicle k

into ordered node sequences such as

    [[0, 2, 4, 2, 0], [0, 3, 5, 0]]

The implementation uses Hierholzer's algorithm on a directed multigraph.
Repeated visits to a node and repeated traversals of the same arc are
therefore supported.

Typical usage
-------------
After optimizing a Gurobi model:

    from gurobi_tour_reconstruction import reconstruct_tours

    model.optimize()
    tours = reconstruct_tours(x)

The returned value is a list of lists, ordered by ascending tour index k.
If the correspondence with k must be retained explicitly, use
``reconstruct_tours_by_id`` instead.

Important assumptions
---------------------
For every active tour k, the positive-multiplicity arcs must form one
connected Eulerian directed multigraph. In particular:

* an Eulerian cycle has equal in-degree and out-degree at every node;
* an open Eulerian path has exactly one node with out-degree = in-degree + 1
  and one node with in-degree = out-degree + 1;
* all positive-multiplicity arcs must belong to the same weakly connected
  component.

The module does not import gurobipy, so it can also be tested with plain
numbers or small mock variable objects.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from numbers import Real
from typing import Any, Dict, Hashable, Iterable, List, Mapping, Optional, Tuple


Node = Hashable
TourId = Hashable
Arc = Tuple[Node, Node]
NodeSequence = List[Node]


class TourReconstructionError(ValueError):
    """Raised when selected arcs cannot represent one Eulerian tour."""


def _read_solution_value(variable: Any) -> float:
    """Read a numeric value from a Gurobi variable or a plain number.

    Gurobi variables normally expose the incumbent solution through ``.X``.
    Plain numeric values are accepted as well, which is useful in unit tests.
    """
    if isinstance(variable, Real):
        return float(variable)

    try:
        return float(variable.X)
    except (AttributeError, TypeError, ValueError) as exc:
        raise TypeError(
            "Each x value must be a number or an object exposing a numeric .X "
            "attribute. Ensure that the Gurobi model has been optimized and "
            "has a feasible solution."
        ) from exc


def _integer_multiplicity(value: float, tolerance: float) -> int:
    """Convert a solver value to a non-negative integer multiplicity.

    Integer Gurobi variables can be returned as values such as 1.999999999.
    The tolerance handles this normal floating-point behavior while rejecting
    values that are genuinely fractional or negative.
    """
    if value < -tolerance:
        raise TourReconstructionError(
            f"Negative arc multiplicity {value} is not valid."
        )

    # Treat tiny values around zero as exactly zero.
    if abs(value) <= tolerance:
        return 0

    rounded = round(value)
    if abs(value - rounded) > tolerance:
        raise TourReconstructionError(
            f"Arc multiplicity {value} is not integer within tolerance "
            f"{tolerance}."
        )

    return int(rounded)


def _choose_eulerian_start(
    edge_counts: Mapping[Arc, int],
    requested_start: Optional[Node] = None,
) -> Node:
    """Validate directed degree conditions and choose the start node."""
    indegree: Counter[Node] = Counter()
    outdegree: Counter[Node] = Counter()

    for (source, target), multiplicity in edge_counts.items():
        outdegree[source] += multiplicity
        indegree[target] += multiplicity

    nodes = set(indegree) | set(outdegree)
    start_candidates: List[Node] = []
    end_candidates: List[Node] = []

    for node in nodes:
        difference = outdegree[node] - indegree[node]
        if difference == 1:
            start_candidates.append(node)
        elif difference == -1:
            end_candidates.append(node)
        elif difference != 0:
            raise TourReconstructionError(
                "Directed Eulerian degree condition violated at node "
                f"{node!r}: out-degree={outdegree[node]}, "
                f"in-degree={indegree[node]}."
            )

    is_open_path = len(start_candidates) == 1 and len(end_candidates) == 1
    is_cycle = len(start_candidates) == 0 and len(end_candidates) == 0

    if not (is_open_path or is_cycle):
        raise TourReconstructionError(
            "The selected arcs do not have valid Eulerian path/cycle degree "
            "conditions."
        )

    if requested_start is not None:
        if outdegree[requested_start] == 0:
            raise TourReconstructionError(
                f"Requested start node {requested_start!r} has no outgoing arc."
            )
        if is_open_path and requested_start != start_candidates[0]:
            raise TourReconstructionError(
                f"Open Eulerian path must start at {start_candidates[0]!r}, "
                f"not at {requested_start!r}."
            )
        return requested_start

    if is_open_path:
        return start_candidates[0]

    # For a cycle, any node with an outgoing arc is a valid start. The first
    # source encountered preserves the iteration order of the input mapping.
    return next(iter(edge_counts))[0]


def reconstruct_eulerian_tour(
    edge_counts: Mapping[Arc, int],
    *,
    start_node: Optional[Node] = None,
) -> NodeSequence:
    """Reconstruct one directed Eulerian path or cycle.

    Parameters
    ----------
    edge_counts:
        Mapping ``(i, j) -> multiplicity`` for one tour. Multiplicity is the
        number of times directed arc ``i -> j`` is traversed.
    start_node:
        Optional start node. For a cycle, this controls where the returned
        sequence begins. For an open Eulerian path, it must be the unique
        degree-valid start node.

    Returns
    -------
    list
        Nodes in traversal order. If M arc traversals are present, the list
        contains exactly M + 1 nodes.

    Notes
    -----
    Hierholzer's algorithm runs in O(M) time and O(M) memory, where M counts
    arc traversals including multiplicity.
    """
    positive_counts = {
        edge: int(count) for edge, count in edge_counts.items() if count > 0
    }
    if not positive_counts:
        return []

    start = _choose_eulerian_start(positive_counts, start_node)

    # Expand multiplicities into adjacency entries. This intentionally keeps
    # duplicate destinations: two traversals of i -> j are two distinct edge
    # occurrences in the directed multigraph.
    adjacency: Dict[Node, List[Node]] = defaultdict(list)
    total_traversals = 0
    for (source, target), multiplicity in positive_counts.items():
        adjacency[source].extend([target] * multiplicity)
        total_traversals += multiplicity

    # Hierholzer's algorithm: walk unused arcs; when stuck, append the current
    # node to the final route. Reversing the backtracking order gives the tour.
    stack: List[Node] = [start]
    reverse_route: NodeSequence = []

    while stack:
        current = stack[-1]
        if adjacency[current]:
            stack.append(adjacency[current].pop())
        else:
            reverse_route.append(stack.pop())

    route = list(reversed(reverse_route))

    # Degree balance alone does not exclude disconnected subtours. If the walk
    # did not consume every selected traversal, the solution contains multiple
    # disconnected Eulerian components for this k.
    used_traversals = len(route) - 1
    if used_traversals != total_traversals:
        raise TourReconstructionError(
            "Not all selected arcs belong to one Eulerian tour: reconstructed "
            f"{used_traversals} of {total_traversals} traversals. The Gurobi "
            "solution may contain disconnected subtours."
        )

    return route


def extract_arc_multiplicities(
    x: Mapping[Tuple[Node, Node, TourId], Any],
    *,
    tolerance: float = 1e-6,
) -> Dict[TourId, Counter[Arc]]:
    """Extract positive integer arc multiplicities from Gurobi variables.

    Parameters
    ----------
    x:
        Usually a ``gurobipy.tupledict`` indexed by ``(i, j, k)``. Values may
        also be plain numbers for testing.
    tolerance:
        Maximum accepted distance from the nearest integer.

    Returns
    -------
    dict
        ``{k: Counter({(i, j): multiplicity, ...}), ...}``.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative.")

    by_tour: Dict[TourId, Counter[Arc]] = defaultdict(Counter)

    for key, variable in x.items():
        if not isinstance(key, tuple) or len(key) != 3:
            raise TypeError(
                f"Expected every x key to be a tuple (i, j, k); got {key!r}."
            )

        source, target, tour_id = key
        value = _read_solution_value(variable)
        multiplicity = _integer_multiplicity(value, tolerance)

        if multiplicity > 0:
            by_tour[tour_id][(source, target)] += multiplicity

    return dict(by_tour)


def reconstruct_tours_by_id(
    x: Mapping[Tuple[Node, Node, TourId], Any],
    *,
    tolerance: float = 1e-6,
    start_nodes: Optional[Mapping[TourId, Node]] = None,
) -> Dict[TourId, NodeSequence]:
    """Reconstruct all active tours and retain their original tour IDs.

    ``start_nodes`` is useful when all tours are cycles and should be displayed
    from a known depot. Example: ``start_nodes={0: depot, 1: depot}``.
    """
    counts_by_tour = extract_arc_multiplicities(x, tolerance=tolerance)
    requested_starts = start_nodes or {}

    return {
        tour_id: reconstruct_eulerian_tour(
            edge_counts,
            start_node=requested_starts.get(tour_id),
        )
        for tour_id, edge_counts in counts_by_tour.items()
    }


def reconstruct_tours(
    x: Mapping[Tuple[Node, Node, TourId], Any],
    *,
    tolerance: float = 1e-6,
    start_nodes: Optional[Mapping[TourId, Node]] = None,
    tour_order: Optional[Iterable[TourId]] = None,
) -> List[NodeSequence]:
    """Return the Gurobi solution as the requested list of node lists.

    By default, active tour IDs are sorted. If IDs are not mutually sortable,
    insertion order is used. Pass ``tour_order`` to define an explicit order.
    Tour IDs absent from the positive solution are represented by empty lists
    only when they are explicitly included in ``tour_order``.
    """
    routes_by_id = reconstruct_tours_by_id(
        x,
        tolerance=tolerance,
        start_nodes=start_nodes,
    )

    if tour_order is not None:
        return [routes_by_id.get(tour_id, []) for tour_id in tour_order]

    try:
        ordered_ids = sorted(routes_by_id)
    except TypeError:
        # Mixed identifier types (for example, integers and strings) cannot
        # always be sorted in Python 3. Dictionary insertion order is stable.
        ordered_ids = list(routes_by_id)

    return [routes_by_id[tour_id] for tour_id in ordered_ids]


if __name__ == "__main__":
    # Standalone demonstration using plain numeric values instead of Gurobi
    # variables. The same functions accept x[i, j, k] Gurobi Var objects.
    example_x = {
        # Tour 0: 1 -> 2 -> 3 -> 1 -> 2 -> 1
        (1, 2, 0): 2,
        (2, 3, 0): 1,
        (3, 1, 0): 1,
        (2, 1, 0): 1,

        # Tour 1: 10 -> 11 -> 12 -> 10
        (10, 11, 1): 1,
        (11, 12, 1): 1,
        (12, 10, 1): 1,
    }

    print("List of lists:")
    print(reconstruct_tours(example_x))

    print("\nDictionary retaining tour IDs:")
    print(reconstruct_tours_by_id(example_x))
