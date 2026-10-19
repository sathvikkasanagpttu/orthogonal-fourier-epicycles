"""Manim scene for Orthogonal Fourier Epicycles drawing the outline of India.

Visualizes two independent real-valued Fourier chains (X and Y) tracing the closed
boundary of India with live harmonic count N, error metrics, and orthogonal guide lines.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import List, Tuple

# Ensure project root is in sys.path whether executed as module or script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
from manim import *

try:
    from src.config import (
        COLOR_BG,
        COLOR_DIVIDER,
        COLOR_DOT,
        COLOR_DOT_HALO,
        COLOR_PATH,
        COLOR_PATH_GLOW,
        COLOR_SILHOUETTE_FILL,
        COLOR_SILHOUETTE_STROKE,
        COLOR_TEXT_MUTED,
        COLOR_TEXT_PRIMARY,
        COLOR_X,
        COLOR_X_PALE,
        COLOR_Y,
        COLOR_Y_PALE,
        DASH_LENGTH,
        DASH_SPACING,
        DEFAULT_SWEEP_N,
        DIVIDER_Y,
        DOT_HALO_RADIUS,
        DOT_RADIUS,
        EQ_P_Y,
        EQ_X_Y,
        EQ_Y_Y,
        EQUATION_COLUMN_X,
        ERROR_TOP_Y,
        FRAME_HEIGHT_VERTICAL,
        FRAME_WIDTH_VERTICAL,
        GEOJSON_PATH,
        M_SAMPLES,
        N_MAX_HARMONICS,
        OUTLINE_CENTER,
        OUTLINE_SCALE,
        SILHOUETTE_OPACITY,
        STATS_TOP_Y,
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
    from src.fourier import (
        compute_coefficients,
        compute_contour_error,
        compute_epicycle_chain_tips,
        reconstruct_2d,
        sort_harmonics_by_amplitude,
    )
    from src.outline import get_india_contour
except ImportError:
    from config import (  # type: ignore
        COLOR_BG,
        COLOR_DIVIDER,
        COLOR_DOT,
        COLOR_DOT_HALO,
        COLOR_PATH,
        COLOR_PATH_GLOW,
        COLOR_SILHOUETTE_FILL,
        COLOR_SILHOUETTE_STROKE,
        COLOR_TEXT_MUTED,
        COLOR_TEXT_PRIMARY,
        COLOR_X,
        COLOR_X_PALE,
        COLOR_Y,
        COLOR_Y_PALE,
        DASH_LENGTH,
        DASH_SPACING,
        DEFAULT_SWEEP_N,
        DIVIDER_Y,
        DOT_HALO_RADIUS,
        DOT_RADIUS,
        EQ_P_Y,
        EQ_X_Y,
        EQ_Y_Y,
        EQUATION_COLUMN_X,
        ERROR_TOP_Y,
        FRAME_HEIGHT_VERTICAL,
        FRAME_WIDTH_VERTICAL,
        GEOJSON_PATH,
        M_SAMPLES,
        N_MAX_HARMONICS,
        OUTLINE_CENTER,
        OUTLINE_SCALE,
        SILHOUETTE_OPACITY,
        STATS_TOP_Y,
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
    from fourier import (  # type: ignore
        compute_coefficients,
        compute_contour_error,
        compute_epicycle_chain_tips,
        reconstruct_2d,
        sort_harmonics_by_amplitude,
    )
    from outline import get_india_contour  # type: ignore


# Configure default vertical mobile layout (9:16)
config.pixel_width = VERTICAL_PIXEL_WIDTH
config.pixel_height = VERTICAL_PIXEL_HEIGHT
config.frame_width = FRAME_WIDTH_VERTICAL
config.frame_height = FRAME_HEIGHT_VERTICAL
config.background_color = COLOR_BG


def make_math_or_text(tex_string: str, text_string: str, font_size: int, color: str) -> VMobject:
    """Create MathTex if system has LaTeX installed, otherwise fall back to styled Text."""
    if shutil.which("latex"):
        try:
            return MathTex(tex_string, font_size=font_size, color=color)
        except Exception:
            pass
    # High-quality typography fallback with serif rendering
    return Text(text_string, font="Georgia", font_size=font_size * 0.75, color=color)


def make_integer(val: int, font_size: int, color: str) -> Integer:
    """Create Integer using MathTex if available or Text if LaTeX is not installed."""
    if shutil.which("latex"):
        return Integer(val, font_size=font_size, color=color, group_with_commas=False)
    return Integer(val, font_size=font_size, color=color, mob_class=Text, group_with_commas=False)




def make_decimal(val: float, num_decimal_places: int, font_size: int, color: str) -> DecimalNumber:
    """Create DecimalNumber using MathTex if available or Text if LaTeX is not installed."""
    if shutil.which("latex"):
        return DecimalNumber(val, num_decimal_places=num_decimal_places, font_size=font_size, color=color)
    return DecimalNumber(val, num_decimal_places=num_decimal_places, font_size=font_size, color=color, mob_class=Text)



class OrthogonalEpicycles(Scene):
    """Vertical animation rendering Orthogonal Fourier Epicycles drawing India."""

    def construct(self) -> None:
        # ======================================================================
        # 1. LOAD & PRECOMPUTE FOURIER DECOMPOSITION
        # ======================================================================
        x_norm, y_norm, t_samples = get_india_contour(mode="geojson", filepath=GEOJSON_PATH, M=M_SAMPLES)
        (a0, c0), a, b, c, d = compute_coefficients(x_norm, y_norm, N_harmonics=N_MAX_HARMONICS)
        order_x, order_y = sort_harmonics_by_amplitude(a, b, c, d)

        # Precompute error lookup for fast, smooth interpolation during animation
        err_lookup = {}
        for n_val in [1, 2, 3, 5, 10, 15, 25, 50, 100, 200, 300, 500, 750, 1000]:
            xr, yr = reconstruct_2d(t_samples, (a0, c0), a, b, c, d, N=n_val, sort_by_amplitude=True)
            err_lookup[n_val] = compute_contour_error(x_norm, y_norm, xr, yr)["mean_error_pct"]

        def get_interp_error(n_float: float) -> float:
            n_clamped = max(1, min(1000, int(round(n_float))))
            keys = sorted(err_lookup.keys())
            if n_clamped in err_lookup:
                return err_lookup[n_clamped]
            for i in range(len(keys) - 1):
                if keys[i] <= n_clamped <= keys[i + 1]:
                    # Log-linear interpolation
                    k0, k1 = keys[i], keys[i + 1]
                    e0, e1 = err_lookup[k0], err_lookup[k1]
                    frac = (np.log(n_clamped) - np.log(k0)) / (np.log(k1) - np.log(k0))
                    return float(np.exp(np.log(e0) + frac * (np.log(e1) - np.log(e0))))
            return err_lookup[keys[-1]]

        # Coordinates for epicycle roots
        # The X root x MUST equal OUTLINE_CENTER[0] + a0 * OUTLINE_SCALE so that tip.x == P.x
        x_chain_root = np.array([OUTLINE_CENTER[0] + a0 * OUTLINE_SCALE, X_CHAIN_CENTER_Y, 0.0])
        # The Y root y MUST equal OUTLINE_CENTER[1] + c0 * OUTLINE_SCALE so that tip.y == P.y
        y_chain_root = np.array([Y_CHAIN_CENTER_X, OUTLINE_CENTER[1] + c0 * OUTLINE_SCALE, 0.0])

        # ======================================================================
        # 2. STATIC SCENE GRAPH & LABELS
        # ======================================================================
        # Main Title (Top-Center)
        title = Text("Orthogonal Fourier Epicycles", font="Georgia", font_size=36, weight=BOLD)
        title.set_color_by_gradient(COLOR_X, COLOR_Y, COLOR_PATH)
        title.to_edge(UP, buff=0.6)

        subtitle = Text("Closed outline drawn by independent x(t) & y(t) harmonics", font="Georgia", font_size=17, color=COLOR_TEXT_MUTED)
        subtitle.next_to(title, DOWN, buff=0.2)

        # X-chain label (above top-left epicycles)
        x_label = Text("X(t) chain", font="Georgia", slant=ITALIC, font_size=20, color=COLOR_X)
        x_label.move_to(np.array([x_chain_root[0], X_CHAIN_CENTER_Y + 2.5, 0.0]))

        # Y-chain label (below bottom-right epicycles)
        y_label = Text("Y(t) chain", font="Georgia", slant=ITALIC, font_size=20, color=COLOR_Y)
        y_label.move_to(np.array([Y_CHAIN_CENTER_X, y_chain_root[1] - 2.5, 0.0]))

        # Faint filled silhouette of India in background
        silhouette = VMobject()
        poly_pts = [
            np.array([OUTLINE_CENTER[0] + x * OUTLINE_SCALE, OUTLINE_CENTER[1] + y * OUTLINE_SCALE, 0.0])
            for x, y in zip(x_norm, y_norm)
        ]
        silhouette.set_points_as_corners(poly_pts)
        silhouette.close_path()
        silhouette.set_fill(COLOR_SILHOUETTE_FILL, opacity=SILHOUETTE_OPACITY)
        silhouette.set_stroke(COLOR_SILHOUETTE_STROKE, width=1.0)

        # ======================================================================
        # 3. DYNAMIC STATS & EQUATIONS PANEL (Top-Right)
        # ======================================================================
        n_tracker = ValueTracker(1)
        t_tracker = ValueTracker(0)

        # "N = <value>"
        n_text_label = Text("N =", font="Georgia", slant=ITALIC, font_size=42, color=COLOR_TEXT_PRIMARY)
        n_number = make_integer(1, font_size=46, color=COLOR_PATH)
        n_number.add_updater(lambda m: m.set_value(int(round(n_tracker.get_value()))))

        n_group = VGroup(n_text_label, n_number).arrange(RIGHT, buff=0.2)
        n_group.move_to(np.array([EQUATION_COLUMN_X, STATS_TOP_Y, 0.0]))

        # "error = <value>%"
        error_label = Text("error =", font="Georgia", font_size=28, color=COLOR_TEXT_PRIMARY)
        error_number = make_decimal(get_interp_error(1), num_decimal_places=2, font_size=28, color=COLOR_TEXT_PRIMARY)
        error_unit = Text("%", font="Georgia", font_size=28, color=COLOR_TEXT_PRIMARY)

        error_number.add_updater(lambda m: m.set_value(get_interp_error(n_tracker.get_value())))
        error_group = VGroup(error_label, error_number, error_unit).arrange(RIGHT, buff=0.12)
        error_group.move_to(np.array([EQUATION_COLUMN_X, ERROR_TOP_Y, 0.0]))

        # Thin horizontal divider rule
        divider = Line(
            start=np.array([EQUATION_COLUMN_X - 1.6, DIVIDER_Y, 0.0]),
            end=np.array([EQUATION_COLUMN_X + 1.6, DIVIDER_Y, 0.0]),
            stroke_width=1.0,
            color=COLOR_DIVIDER,
        )

        # Math equations
        eq_x = make_math_or_text(
            r"x(t) = \sum_{k=1}^N \left( a_k \cos kt + b_k \sin kt \right)",
            "x(t) = ∑ (a_k cos kt + b_k sin kt)",
            font_size=26,
            color=COLOR_X,
        ).move_to(np.array([EQUATION_COLUMN_X, EQ_X_Y, 0.0]))

        eq_y = make_math_or_text(
            r"y(t) = \sum_{k=1}^N \left( c_k \cos kt + d_k \sin kt \right)",
            "y(t) = ∑ (c_k cos kt + d_k sin kt)",
            font_size=26,
            color=COLOR_Y,
        ).move_to(np.array([EQUATION_COLUMN_X, EQ_Y_Y, 0.0]))

        eq_p = make_math_or_text(
            r"\mathbf{P}(t) = (x(t), y(t))",
            "P(t) = (x(t), y(t))",
            font_size=27,
            color=COLOR_PATH,
        ).move_to(np.array([EQUATION_COLUMN_X, EQ_P_Y, 0.0]))

        equations_group = VGroup(n_group, error_group, divider, eq_x, eq_y, eq_p)

        # ======================================================================
        # 4. EPICYCLE CHAINS & ORTHOGONAL GUIDE REDRAWERS
        # ======================================================================
        # Helper to compute current tip & circles for X chain
        def get_x_chain_state() -> Tuple[List, np.ndarray]:
            t_val = t_tracker.get_value()
            n_val = int(round(n_tracker.get_value()))
            scaled_a = a * OUTLINE_SCALE
            scaled_b = b * OUTLINE_SCALE
            circles, tip = compute_epicycle_chain_tips(
                t_val=t_val,
                root_origin=(x_chain_root[0], x_chain_root[1]),
                a_or_c=scaled_a,
                b_or_d=scaled_b,
                N_total=n_val,
                max_visible=X_CHAIN_MAX_VISIBLE,
                order=order_x,
                component="x",
            )
            return circles, np.array([tip[0], tip[1], 0.0])

        # Helper to compute current tip & circles for Y chain
        def get_y_chain_state() -> Tuple[List, np.ndarray]:
            t_val = t_tracker.get_value()
            n_val = int(round(n_tracker.get_value()))
            scaled_c = c * OUTLINE_SCALE
            scaled_d = d * OUTLINE_SCALE
            circles, tip = compute_epicycle_chain_tips(
                t_val=t_val,
                root_origin=(y_chain_root[0], y_chain_root[1]),
                a_or_c=scaled_c,
                b_or_d=scaled_d,
                N_total=n_val,
                max_visible=Y_CHAIN_MAX_VISIBLE,
                order=order_y,
                component="y",
            )
            return circles, np.array([tip[0], tip[1], 0.0])

        # Epicycle X chain Mobject
        def draw_x_chain() -> VMobject:
            group = VGroup()
            circles, _ = get_x_chain_state()
            for (cx, cy), r, (tx, ty) in circles:
                if r > 0.015:
                    circ = Circle(radius=r, stroke_width=STROKE_WIDTH_CIRCLE, stroke_color=COLOR_X, stroke_opacity=0.45)
                    circ.move_to(np.array([cx, cy, 0.0]))
                    group.add(circ)
                # Radius vector
                rad_line = Line(
                    start=np.array([cx, cy, 0.0]),
                    end=np.array([tx, ty, 0.0]),
                    stroke_width=STROKE_WIDTH_RADIUS,
                    stroke_color=COLOR_X,
                    stroke_opacity=0.75,
                )
                group.add(rad_line)
            return group

        # Epicycle Y chain Mobject
        def draw_y_chain() -> VMobject:
            group = VGroup()
            circles, _ = get_y_chain_state()
            for (cx, cy), r, (tx, ty) in circles:
                if r > 0.015:
                    circ = Circle(radius=r, stroke_width=STROKE_WIDTH_CIRCLE, stroke_color=COLOR_Y, stroke_opacity=0.45)
                    circ.move_to(np.array([cx, cy, 0.0]))
                    group.add(circ)
                # Radius vector
                rad_line = Line(
                    start=np.array([cx, cy, 0.0]),
                    end=np.array([tx, ty, 0.0]),
                    stroke_width=STROKE_WIDTH_RADIUS,
                    stroke_color=COLOR_Y,
                    stroke_opacity=0.75,
                )
                group.add(rad_line)
            return group

        x_chain_mobject = always_redraw(draw_x_chain)
        y_chain_mobject = always_redraw(draw_y_chain)

        # Drawing Point P(t) = (X_tip.x, Y_tip.y)
        def get_drawing_point() -> np.ndarray:
            _, x_tip = get_x_chain_state()
            _, y_tip = get_y_chain_state()
            return np.array([x_tip[0], y_tip[1], 0.0])

        # Dashed Lines Connecting Tips to P(t)
        def draw_x_dashed() -> VMobject:
            _, x_tip = get_x_chain_state()
            p = get_drawing_point()
            return DashedLine(
                start=x_tip,
                end=p,
                dash_length=DASH_LENGTH,
                dashed_ratio=0.55,
                stroke_width=STROKE_WIDTH_DASH,
                color=COLOR_X,
                stroke_opacity=0.8,
            )

        def draw_y_dashed() -> VMobject:
            _, y_tip = get_y_chain_state()
            p = get_drawing_point()
            return DashedLine(
                start=y_tip,
                end=p,
                dash_length=DASH_LENGTH,
                dashed_ratio=0.55,
                stroke_width=STROKE_WIDTH_DASH,
                color=COLOR_Y,
                stroke_opacity=0.8,
            )

        dashed_x = always_redraw(draw_x_dashed)
        dashed_y = always_redraw(draw_y_dashed)

        # Glowing Drawing Point Dot
        def draw_dot() -> VMobject:
            p = get_drawing_point()
            group = VGroup()
            halo = Dot(point=p, radius=DOT_HALO_RADIUS, color=COLOR_DOT_HALO).set_opacity(0.4)
            core = Dot(point=p, radius=DOT_RADIUS, color=COLOR_DOT).set_opacity(1.0)
            group.add(halo, core)
            return group

        drawing_dot = always_redraw(draw_dot)

        # Static curve preview for sweeping N
        curve_preview = VMobject()

        def update_curve_for_N(target_N: int) -> VMobject:
            t_arr = np.linspace(0, 2 * np.pi, 1200, endpoint=True)
            xr, yr = reconstruct_2d(t_arr, (a0, c0), a, b, c, d, N=target_N, sort_by_amplitude=True)
            pts = [
                np.array([OUTLINE_CENTER[0] + px * OUTLINE_SCALE, OUTLINE_CENTER[1] + py * OUTLINE_SCALE, 0.0])
                for px, py in zip(xr, yr)
            ]
            curve = VMobject()
            curve.set_points_smoothly(pts)
            curve.set_stroke(COLOR_PATH, width=STROKE_WIDTH_PATH)
            return curve

        # ======================================================================
        # 5. ANIMATION CHOREOGRAPHY
        # ======================================================================
        # Step 1: Fade in title, equations, background silhouette, and empty layout
        self.play(FadeIn(title, shift=DOWN * 0.3), FadeIn(subtitle), run_time=1.2)
        self.play(
            FadeIn(equations_group, shift=LEFT * 0.3),
            FadeIn(x_label),
            FadeIn(y_label),
            FadeIn(silhouette),
            run_time=1.0,
        )

        # Add active epicycle chains and orthogonal dashed guides
        self.add(x_chain_mobject, y_chain_mobject, dashed_x, dashed_y, drawing_dot)
        self.wait(0.5)

        # Step 2: N = 1 initial harmonic trace
        curve_preview = update_curve_for_N(1)
        self.play(Create(curve_preview), run_time=1.4)
        self.wait(0.4)

        # Step 3: Sweep N through 1, 3, 5, 10, 25, 100, 300, 1000
        sweep_values = [3, 5, 10, 25, 100, 300, 1000]
        for next_N in sweep_values:
            new_curve = update_curve_for_N(next_N)
            # Smoothly animate N value tracker and transform curve
            self.play(
                n_tracker.animate.set_value(next_N),
                Transform(curve_preview, new_curve),
                run_time=0.65,
                rate_func=linear,
            )
            self.wait(0.15)

        self.wait(0.6)

        # Step 4: Final full-revolution trace at N = 1000 with glowing traced path
        # Remove the static curve preview and let the moving drawing point trace dynamically!
        self.remove(curve_preview)

        # Build dynamic traced path with dual glow layers
        glowing_trace = VMobject()
        glowing_trace.set_stroke(COLOR_PATH_GLOW, width=6.0, opacity=0.3)
        core_trace = VMobject()
        core_trace.set_stroke(COLOR_PATH, width=STROKE_WIDTH_PATH, opacity=1.0)

        trace_points = []

        def update_trace(m: VMobject) -> None:
            pt = get_drawing_point()
            trace_points.append(pt)
            if len(trace_points) > 1:
                core_trace.set_points_as_corners(trace_points)
                glowing_trace.set_points_as_corners(trace_points)

        trace_updater = Mobject().add_updater(update_trace)
        self.add(glowing_trace, core_trace, trace_updater)

        # Animate t from 0 to 2π over 12 seconds for slow, mesmerizing full detail
        self.play(
            t_tracker.animate.set_value(2.0 * np.pi),
            run_time=12.0,
            rate_func=linear,
        )

        trace_updater.remove_updater(update_trace)
        self.remove(trace_updater)

        # Ensure complete outline remains intact and hold final frame
        final_completed_outline = update_curve_for_N(1000)
        self.add(final_completed_outline)

        # Step 5: Hold last frame for 2 seconds
        self.wait(2.0)
