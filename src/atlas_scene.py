"""AtlasEpicyclesScene: Manim scene capable of rendering any country/continent/world map
from the precomputed Atlas dataset with orthogonal Fourier epicycles.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from manim import *

# Project root setup
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from src.config import (
        COLOR_BG,
        COLOR_DOT,
        COLOR_DOT_HALO,
        COLOR_PATH,
        COLOR_PATH_GLOW,
        COLOR_TEXT_MUTED,
        COLOR_TEXT_PRIMARY,
        COLOR_X,
        COLOR_X_PALE,
        COLOR_Y,
        COLOR_Y_PALE,
        DASH_LENGTH,
        DASH_SPACING,
        DOT_HALO_RADIUS,
        DOT_RADIUS,
        FRAME_HEIGHT_VERTICAL,
        FRAME_WIDTH_VERTICAL,
        OUTLINE_CENTER,
        OUTLINE_SCALE,
        STROKE_WIDTH_CIRCLE,
        STROKE_WIDTH_DASH,
        STROKE_WIDTH_PATH,
        STROKE_WIDTH_RADIUS,
        VERTICAL_PIXEL_HEIGHT,
        VERTICAL_PIXEL_WIDTH,
        X_CHAIN_CENTER_Y,
        X_CHAIN_MAX_VISIBLE,
        Y_CHAIN_CENTER_X,
        Y_CHAIN_MAX_VISIBLE,
    )
except ImportError:
    from config import *  # type: ignore


def make_math_or_text(tex_string: str, text_string: str, font_size: int, color: str) -> VMobject:
    """Create MathTex if system has LaTeX installed, otherwise fall back to styled Text."""
    if shutil.which("latex"):
        try:
            return MathTex(tex_string, font_size=font_size, color=color)
        except Exception:
            pass
    return Text(text_string, font="Georgia", font_size=int(font_size * 0.75), color=color)


def make_integer(val: int, font_size: int, color: str) -> Integer:
    """Create Integer without LaTeX dependency if absent."""
    if shutil.which("latex"):
        return Integer(val, font_size=font_size, color=color, group_with_commas=False)
    return Integer(val, font_size=font_size, color=color, mob_class=Text, group_with_commas=False)


def make_decimal(val: float, num_decimal_places: int, font_size: int, color: str) -> DecimalNumber:
    """Create DecimalNumber without LaTeX dependency if absent."""
    if shutil.which("latex"):
        return DecimalNumber(val, num_decimal_places=num_decimal_places, font_size=font_size, color=color)
    return DecimalNumber(val, num_decimal_places=num_decimal_places, font_size=font_size, color=color, mob_class=Text)


def load_atlas_map(map_id_or_path: str) -> Dict[str, Any]:
    """Find and load atlas map data by ID or file path."""
    atlas_dir = ROOT_DIR / "web" / "public" / "atlas"
    if not atlas_dir.exists():
        atlas_dir = ROOT_DIR / "atlas"

    # Direct file path
    p = Path(map_id_or_path)
    if p.exists() and p.is_file():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    # Check index.json
    index_file = atlas_dir / "index.json"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            index_list = json.load(f)
        for item in index_list:
            if item["id"].upper() == map_id_or_path.upper() or item["name"].lower() == map_id_or_path.lower():
                target_file = atlas_dir / item["file"]
                if target_file.exists():
                    with open(target_file, "r", encoding="utf-8") as tf:
                        return json.load(tf)

    # Check direct maps/<ID>.json
    cand = atlas_dir / "maps" / f"{map_id_or_path.upper()}.json"
    if cand.exists():
        with open(cand, "r", encoding="utf-8") as f:
            return json.load(f)

    # World
    if map_id_or_path.upper() in ["WLD", "WORLD"]:
        wld_file = atlas_dir / "world.json"
        if wld_file.exists():
            with open(wld_file, "r", encoding="utf-8") as f:
                return json.load(f)

    raise FileNotFoundError(f"Could not find map data for '{map_id_or_path}' in {atlas_dir}")


class AtlasEpicyclesScene(Scene):
    """General Manim scene for rendering any country or region from the Atlas."""

    map_id: str = "IND"
    detail_level: str = "all"  # 'main', 'large', 'all'
    n_sweep: bool = False
    active_n: int = 120

    def construct(self) -> None:
        # Allow environment override
        target_map = os.environ.get("ATLAS_MAP_ID", self.map_id)
        detail = os.environ.get("ATLAS_DETAIL", self.detail_level)
        is_sweep = os.environ.get("ATLAS_N_SWEEP", "0") in ["1", "true", "True"] or self.n_sweep

        map_data = load_atlas_map(target_map)
        country_name = map_data.get("name", target_map)
        rings = map_data.get("rings", [])
        if not rings:
            raise ValueError(f"No rings in map {target_map}")

        # Filter rings by detail level
        if detail == "main":
            rings = [rings[0]]
        elif detail == "large":
            rings = [r for i, r in enumerate(rings) if i == 0 or r.get("area_ratio", 0) >= 0.005 or i < 8]

        main_ring = rings[0]
        x_chain_data = main_ring["x_chain"]
        y_chain_data = main_ring["y_chain"]

        a0 = x_chain_data.get("a0", 0.0)
        c0 = y_chain_data.get("c0", 0.0)
        R_x = np.array(x_chain_data["R"], dtype=float)
        phi_x = np.array(x_chain_data["phi"], dtype=float)
        order_x = np.array(x_chain_data["order"], dtype=int)

        R_y = np.array(y_chain_data["R"], dtype=float)
        phi_y = np.array(y_chain_data["phi"], dtype=float)
        order_y = np.array(y_chain_data["order"], dtype=int)

        error_table = main_ring.get("error_table", {})

        def get_interp_error(n_float: float) -> float:
            n_clamped = max(1, min(1000, int(round(n_float))))
            keys = sorted([int(k) for k in error_table.keys()])
            if not keys:
                return 0.05
            if n_clamped in keys:
                return float(error_table[str(n_clamped)])
            for i in range(len(keys) - 1):
                if keys[i] <= n_clamped <= keys[i + 1]:
                    k0, k1 = keys[i], keys[i + 1]
                    e0, e1 = error_table[str(k0)], error_table[str(k1)]
                    frac = (n_clamped - k0) / (k1 - k0)
                    return float(e0 + frac * (e1 - e0))
            return float(error_table[str(keys[-1])])

        # Epicycle roots
        x_chain_root = np.array([OUTLINE_CENTER[0] + a0 * OUTLINE_SCALE, X_CHAIN_CENTER_Y, 0.0])
        y_chain_root = np.array([Y_CHAIN_CENTER_X, OUTLINE_CENTER[1] + c0 * OUTLINE_SCALE, 0.0])

        # Static Titles and Equations
        title = Text("Orthogonal Fourier Epicycles", font="Georgia", font_size=34, weight=BOLD)
        title.set_color_by_gradient(COLOR_X, COLOR_Y, COLOR_PATH)
        title.to_edge(UP, buff=0.55)

        subtitle = Text(f"{country_name} — Independent x(t) & y(t) Harmonics", font="Georgia", font_size=16, color=COLOR_TEXT_MUTED)
        subtitle.next_to(title, DOWN, buff=0.18)

        # Equations HUD
        eq_x = make_math_or_text(
            r"x(t) = a_0 + \sum_{k=1}^N \left( a_k \cos kt + b_k \sin kt \right)",
            "x(t) = a0 + sum(ak cos kt + bk sin kt)",
            font_size=18,
            color=COLOR_X,
        )
        eq_y = make_math_or_text(
            r"y(t) = c_0 + \sum_{k=1}^N \left( c_k \cos kt + d_k \sin kt \right)",
            "y(t) = c0 + sum(ck cos kt + dk sin kt)",
            font_size=18,
            color=COLOR_Y,
        )
        eq_p = make_math_or_text(
            r"\mathbf{P}(t) = \big( x(t),\, y(t) \big)",
            "P(t) = (x(t), y(t))",
            font_size=20,
            color=COLOR_PATH,
        )

        eq_group = VGroup(eq_x, eq_y, eq_p).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
        eq_group.to_corner(UL, buff=0.7).shift(DOWN * 1.5)

        # Live N and Error metrics
        n_tracker = ValueTracker(10.0 if is_sweep else float(self.active_n))
        t_tracker = ValueTracker(0.0)

        n_label = Text("N = ", font="Georgia", font_size=22, color=COLOR_TEXT_PRIMARY)
        n_num = always_redraw(lambda: make_integer(int(round(n_tracker.get_value())), font_size=24, color=COLOR_X))
        n_mobj = VGroup(n_label, n_num).arrange(RIGHT, buff=0.08)

        err_label = Text("error = ", font="Georgia", font_size=20, color=COLOR_TEXT_MUTED)
        err_num = always_redraw(
            lambda: make_decimal(
                get_interp_error(n_tracker.get_value()),
                num_decimal_places=2,
                font_size=22,
                color=COLOR_PATH,
            )
        )
        pct_sign = Text("%", font="Georgia", font_size=20, color=COLOR_TEXT_MUTED)
        err_mobj = VGroup(err_label, err_num, pct_sign).arrange(RIGHT, buff=0.06)

        stats_group = VGroup(n_mobj, err_mobj).arrange(DOWN, buff=0.18, aligned_edge=LEFT)
        stats_group.to_corner(UR, buff=0.7).shift(DOWN * 1.5)

        self.add(title, subtitle, eq_group, stats_group)

        # Helper to compute tips
        def get_chain_tips(root: np.ndarray, R_arr: np.ndarray, phi_arr: np.ndarray, order_arr: np.ndarray, t: float, num_n: int, is_y_chain: bool = False):
            curr = np.array(root, dtype=float)
            centers = []
            radii = []
            N_eval = min(num_n, len(R_arr))
            for i in range(N_eval):
                r = R_arr[i] * OUTLINE_SCALE
                k = order_arr[i]
                phi = phi_arr[i]
                angle = k * t - phi
                centers.append(curr.copy())
                radii.append(r)
                if not is_y_chain:
                    curr += np.array([r * np.cos(angle), r * np.sin(angle), 0.0])
                else:
                    # In standard Cartesian y(t), component is vertical
                    curr += np.array([r * np.cos(angle), r * np.sin(angle), 0.0])
            return curr, centers, radii

        # Dynamic epicycles
        x_mobjects = always_redraw(
            lambda: self.build_chain_mobject(
                x_chain_root, R_x, phi_x, order_x, t_tracker.get_value(), int(round(n_tracker.get_value())), COLOR_X, COLOR_X_PALE, X_CHAIN_MAX_VISIBLE, False
            )
        )
        y_mobjects = always_redraw(
            lambda: self.build_chain_mobject(
                y_chain_root, R_y, phi_y, order_y, t_tracker.get_value(), int(round(n_tracker.get_value())), COLOR_Y, COLOR_Y_PALE, Y_CHAIN_MAX_VISIBLE, True
            )
        )

        # Dashed Projection Lines and Drawing Point P(t)
        def get_current_P():
            t = t_tracker.get_value()
            n_val = int(round(n_tracker.get_value()))
            tip_x, _, _ = get_chain_tips(x_chain_root, R_x, phi_x, order_x, t, n_val, False)
            tip_y, _, _ = get_chain_tips(y_chain_root, R_y, phi_y, order_y, t, n_val, True)
            return np.array([tip_x[0], tip_y[1], 0.0]), tip_x, tip_y

        proj_lines = always_redraw(
            lambda: self.build_projection_lines(*get_current_P())
        )
        drawing_point = always_redraw(
            lambda: self.build_drawing_point(get_current_P()[0])
        )

        # Traced Path
        traced_path = VMobject()
        traced_path.set_stroke(COLOR_PATH, width=STROKE_WIDTH_PATH)
        p0, _, _ = get_current_P()
        traced_path.set_points_as_corners([p0, p0])

        def update_traced_path(mob):
            pt, _, _ = get_current_P()
            mob.add_points_as_corners([pt])

        traced_path.add_updater(update_traced_path)

        self.add(x_mobjects, y_mobjects, proj_lines, traced_path, drawing_point)

        if is_sweep:
            # Progressive sweep over harmonic counts
            sweep_values = [5, 10, 25, 50, 100, 200, min(500, len(R_x))]
            for val in sweep_values:
                self.play(
                    n_tracker.animate.set_value(val),
                    t_tracker.animate.increment_value(2 * np.pi),
                    run_time=3.5,
                    rate_func=linear,
                )
        else:
            # Steady 2-period drawing at fixed N
            self.play(
                t_tracker.animate.set_value(4 * np.pi),
                run_time=12.0,
                rate_func=linear,
            )

        self.wait(1.0)

    def build_chain_mobject(self, root, R_arr, phi_arr, order_arr, t, num_n, color, pale_color, max_vis, is_y):
        grp = VGroup()
        curr = np.array(root, dtype=float)
        N_eval = min(num_n, len(R_arr))
        for i in range(min(N_eval, max_vis)):
            r = R_arr[i] * OUTLINE_SCALE
            k = order_arr[i]
            phi = phi_arr[i]
            angle = k * t - phi
            circle = Circle(radius=max(0.005, r), stroke_color=pale_color, stroke_width=STROKE_WIDTH_CIRCLE)
            circle.move_to(curr)
            nxt = curr + np.array([r * np.cos(angle), r * np.sin(angle), 0.0])
            arrow = Line(curr, nxt, stroke_color=color, stroke_width=STROKE_WIDTH_RADIUS)
            grp.add(circle, arrow)
            curr = nxt
        return grp

    def build_projection_lines(self, P, tip_x, tip_y):
        grp = VGroup()
        vert_line = DashedLine(
            start=tip_x,
            end=P,
            dashed_ratio=0.6,
            dash_length=DASH_LENGTH,
            color=COLOR_X,
            stroke_width=STROKE_WIDTH_DASH,
        )
        horiz_line = DashedLine(
            start=tip_y,
            end=P,
            dashed_ratio=0.6,
            dash_length=DASH_LENGTH,
            color=COLOR_Y,
            stroke_width=STROKE_WIDTH_DASH,
        )
        grp.add(vert_line, horiz_line)
        return grp

    def build_drawing_point(self, P):
        grp = VGroup()
        halo = Dot(point=P, radius=DOT_HALO_RADIUS, color=COLOR_DOT_HALO)
        dot = Dot(point=P, radius=DOT_RADIUS, color=COLOR_DOT)
        grp.add(halo, dot)
        return grp
