"""Export graph tours over satellite imagery.

Dependencies:
    pip install matplotlib contextily geopandas shapely pyproj xyzservices

Swiss coordinate systems:
    EPSG:2056 = CH1903+ / LV95 (default)
    EPSG:21781 = CH1903 / LV03

Example:
    tours = [[1, 2, 3, 1], [4, 5, 6]]
    coordinates = {1: (2683000, 1247000), 2: (2683500, 1247200),
                   3: (2683200, 1247600), 4: (2684000, 1248000),
                   5: (2684500, 1248200), 6: (2684300, 1248600)}
    export_tours(tours, coordinates, output_dir="tour_maps")
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from xyzservices import TileProvider
from pyproj import CRS
from shapely.geometry import Point

Coordinate = tuple[float, float]


def export_tours(
    tours: Sequence[Sequence[int]],
    coordinates: Mapping[int, Coordinate],
    output_dir: str | Path = "tour_maps",
    *,
    source_crs: str | int = "EPSG:2056",
    padding_ratio: float = 0.15,
    minimum_padding_m: float = 150.0,
    dpi: int = 180,
    zoom: int | str = "auto",
    close_tours: bool = False,
    filename_prefix: str = "tour",
) -> list[Path]:
    """Create one satellite PNG per tour and return the generated paths.

    Coordinates are interpreted in ``source_crs`` and converted to Web Mercator.
    Consecutive node IDs define directed arcs. If ``close_tours`` is true, an
    extra arc from the last node to the first is added unless already present.

    SWISSIMAGE tiles require internet access while this function is running.
    The output includes the required swisstopo attribution.
    """
    _validate_inputs(tours, coordinates, source_crs, padding_ratio, minimum_padding_m)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    for tour_number, raw_tour in enumerate(tours, start=1):
        tour = list(raw_tour)
        if not tour:
            raise ValueError(f"Tour {tour_number} is empty")
        missing = sorted(set(tour).difference(coordinates))
        if missing:
            raise KeyError(f"Tour {tour_number} references unknown nodes: {missing}")

        points = gpd.GeoSeries(
            [Point(*coordinates[node]) for node in tour], crs=source_crs
        ).to_crs(epsg=3857)
        xy = [(point.x, point.y) for point in points]

        min_x, min_y, max_x, max_y = points.total_bounds
        span_x, span_y = max_x - min_x, max_y - min_y
        pad_x = max(span_x * padding_ratio, minimum_padding_m)
        pad_y = max(span_y * padding_ratio, minimum_padding_m)

        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_xlim(min_x - pad_x, max_x + pad_x)
        ax.set_ylim(min_y - pad_y, max_y + pad_y)

        # Official Swiss open-data orthophotos; no account or API key required.
        swissimage = TileProvider(
            name="SWISSIMAGE",
            url=("https://wmts.geo.admin.ch/1.0.0/"
                 "ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg"),
            attribution="© swisstopo",
            max_zoom=20,
        )
        ctx.add_basemap(ax, source=swissimage, zoom=zoom, attribution="© swisstopo")

        draw_xy = xy[:]
        if close_tours and len(draw_xy) > 1 and tour[0] != tour[-1]:
            draw_xy.append(draw_xy[0])

        # Curved directed arcs reduce overlap and make arrow direction visible.
        for edge_index, ((x1, y1), (x2, y2)) in enumerate(zip(draw_xy, draw_xy[1:])):
            if x1 == x2 and y1 == y2:
                continue
            curvature = 0.10 if edge_index % 2 == 0 else -0.10
            arrow = FancyArrowPatch(
                (x1, y1), (x2, y2),
                arrowstyle="-|>", mutation_scale=16,
                connectionstyle=f"arc3,rad={curvature}",
                linewidth=2.2, color="red", alpha=0.9, zorder=4,
                shrinkA=5, shrinkB=5,
            )
            ax.add_patch(arrow)

        xs, ys = zip(*xy)
        ax.scatter(xs, ys, s=55, c="red", edgecolors="white", linewidths=1.2, zorder=5)
        for node, (x, y) in zip(tour, xy):
            ax.annotate(str(node), (x, y), xytext=(5, 5), textcoords="offset points",
                        color="white", fontsize=8, weight="bold", zorder=6,
                        bbox={"boxstyle": "round,pad=0.15", "fc": "#b00000", "ec": "none", "alpha": 0.85})

        ax.set_axis_off()
        ax.set_title(f"Tour {tour_number}", fontsize=14)
        fig.tight_layout()
        path = out / f"{filename_prefix}_{tour_number:03d}.png"
        fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0.05)
        plt.close(fig)
        generated.append(path)

    return generated


def _validate_inputs(
    tours: Sequence[Sequence[int]],
    coordinates: Mapping[int, Coordinate],
    source_crs: str | int,
    padding_ratio: float,
    minimum_padding_m: float,
) -> None:
    if isinstance(tours, (str, bytes)) or not isinstance(tours, Sequence):
        raise TypeError("tours must be a sequence of integer sequences")
    if not coordinates:
        raise ValueError("coordinates cannot be empty")
    CRS.from_user_input(source_crs)  # Raises a useful error for invalid CRS.
    if padding_ratio < 0 or minimum_padding_m < 0:
        raise ValueError("padding values must be non-negative")
    for node, coordinate in coordinates.items():
        if not isinstance(node, int):
            raise TypeError(f"Node key {node!r} is not an integer")
        if len(coordinate) != 2:
            raise ValueError(f"Coordinate for node {node} must contain exactly two values")
        float(coordinate[0]); float(coordinate[1])
    for i, tour in enumerate(tours, start=1):
        if isinstance(tour, (str, bytes)) or not isinstance(tour, Sequence):
            raise TypeError(f"Tour {i} is not a sequence")
        if any(not isinstance(node, int) for node in tour):
            raise TypeError(f"Tour {i} contains a non-integer node ID")


if __name__ == "__main__":
    # Small LV95 example around Bern. Replace with your own graph data.
    example_tours = [[1, 2, 3, 1], [1, 3, 2]]
    example_coordinates = {
        1: (2600000, 1200000),
        2: (2600800, 1200300),
        3: (2600400, 1200900),
    }
    files = export_tours(example_tours, example_coordinates)
    print("Generated:", *(str(path) for path in files), sep="\n")
