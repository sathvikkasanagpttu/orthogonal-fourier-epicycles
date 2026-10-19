"""Fourier analysis, harmonic decomposition, reconstruction, and error metrics.

Provides real-valued Fourier series calculation for orthogonal x(t) and y(t) chains:
  x(t) = a0 + sum_{k=1..N} [ a_k cos(kt) + b_k sin(kt) ]
  y(t) = c0 + sum_{k=1..N} [ c_k cos(kt) + d_k sin(kt) ]

Features:
  - Vectorized FFT-based coefficient extraction via np.fft.rfft
  - Direct conversion to polar epicycle form: R_k cos(kt - φ_k)
  - Optional Lanczos sigma smoothing factor to suppress Gibbs ringing
  - KDTree-based Euclidean contour distance and Hausdorff metrics
  - Harmonic sorting by descending amplitude for optimal epicycle chaining
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from scipy.spatial import cKDTree


def compute_coefficients(
    x: np.ndarray,
    y: np.ndarray,
    N_harmonics: Optional[int] = None,
) -> Tuple[Tuple[float, float], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute real Fourier series coefficients for x(t) and y(t) using FFT.

    For a sequence of M points sampled at t_m = 2π*m/M:
      X_k = sum_{m=0}^{M-1} x_m * exp(-i * 2π * k * m / M)
    The real Fourier coefficients satisfy:
      a0 = Re(X_0) / M
      a_k = 2 * Re(X_k) / M    (for k >= 1)
      b_k = -2 * Im(X_k) / M   (for k >= 1)
    and identically for y(t) -> (c0, c_k, d_k).

    Args:
        x: Array of x-coordinates of length M.
        y: Array of y-coordinates of length M.
        N_harmonics: Maximum harmonic order N to retain. If None, retains M // 2.

    Returns:
        Tuple containing:
          - (a0, c0): DC centers (scalar floats)
          - a: Cosine coefficients for x(t), shape (N,)
          - b: Sine coefficients for x(t), shape (N,)
          - c: Cosine coefficients for y(t), shape (N,)
          - d: Sine coefficients for y(t), shape (N,)
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    M = len(x_arr)

    if len(y_arr) != M:
        raise ValueError("x and y arrays must have identical length.")

    max_possible_harmonics = M // 2
    if N_harmonics is None or N_harmonics > max_possible_harmonics:
        N = max_possible_harmonics
    else:
        N = int(N_harmonics)

    # Real FFT: returns frequencies 0, 1, ..., M//2
    fft_x = np.fft.rfft(x_arr)
    fft_y = np.fft.rfft(y_arr)

    # DC components (k = 0)
    a0 = float(np.real(fft_x[0])) / M
    c0 = float(np.real(fft_y[0])) / M

    # AC components (k = 1 .. N)
    a = (2.0 * np.real(fft_x[1 : N + 1]) / M).astype(np.float64)
    b = (-2.0 * np.imag(fft_x[1 : N + 1]) / M).astype(np.float64)
    c = (2.0 * np.real(fft_y[1 : N + 1]) / M).astype(np.float64)
    d = (-2.0 * np.imag(fft_y[1 : N + 1]) / M).astype(np.float64)

    return (a0, c0), a, b, c, d


def to_amplitude_phase(a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Convert Cartesian Fourier coefficients (a_k, b_k) to polar epicycle parameters (R_k, φ_k).

    Identity:
      a * cos(kt) + b * sin(kt) = R * cos(kt - φ)
    where:
      R = sqrt(a^2 + b^2)
      φ = atan2(b, a)
    since cos(kt - φ) = cos(kt)*cos(φ) + sin(kt)*sin(φ).

    Args:
        a: Array of cosine coefficients.
        b: Array of sine coefficients.

    Returns:
        Tuple of (R, phi):
          - R: Epicycle radius amplitudes (non-negative).
          - phi: Phase angles in radians within [-π, π].
    """
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)

    R = np.hypot(a_arr, b_arr)
    phi = np.arctan2(b_arr, a_arr)
    return R, phi


def lanczos_sigma(N: int) -> np.ndarray:
    """Compute Lanczos sigma smoothing factors for harmonics k = 1..N.

    Suppresses the Gibbs phenomenon (ringing artifacts near sharp corners or edges)
    by multiplying the k-th harmonic by:
      σ_k = sinc(k / N) = sin(π * k / N) / (π * k / N)

    Args:
        N: Total number of harmonics being summed.

    Returns:
        np.ndarray of shape (N,) with smoothing multipliers in (0, 1].
    """
    if N <= 1:
        return np.ones(N, dtype=np.float64)

    k = np.arange(1, N + 1, dtype=np.float64)
    # np.sinc(x) in numpy computes sin(pi * x) / (pi * x)
    return np.sinc(k / N)


def sort_harmonics_by_amplitude(
    a: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    d: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute permutation indices that sort harmonics by descending amplitude.

    Returns independent sorting orders for X-chain (R_x) and Y-chain (R_y).

    Args:
        a, b: Coefficients for x(t).
        c, d: Coefficients for y(t).

    Returns:
        Tuple of (order_x, order_y) containing zero-based harmonic index permutations.
    """
    R_x, _ = to_amplitude_phase(a, b)
    R_y, _ = to_amplitude_phase(c, d)

    order_x = np.argsort(-R_x)
    order_y = np.argsort(-R_y)
    return order_x, order_y


def reconstruct_1d(
    t: np.ndarray,
    dc: float,
    cos_coeffs: np.ndarray,
    sin_coeffs: np.ndarray,
    N: Optional[int] = None,
    use_lanczos: bool = False,
    order: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Reconstruct 1D signal from real Fourier series coefficients for arbitrary t array.

    Args:
        t: 1D array of time/angle parameters in radians.
        dc: Scalar DC offset (a0 or c0).
        cos_coeffs: Cosine coefficients (a or c).
        sin_coeffs: Sine coefficients (b or d).
        N: Number of harmonics to include. If None, uses all available.
        use_lanczos: If True, applies Lanczos sigma smoothing factor.
        order: Optional permutation of harmonic indices (e.g. sorted by amplitude).

    Returns:
        np.ndarray of same shape as t with reconstructed signal values.
    """
    t_arr = np.asarray(t, dtype=np.float64)
    total_coeffs = len(cos_coeffs)

    if N is None or N > total_coeffs:
        N_eval = total_coeffs
    else:
        N_eval = int(N)

    if N_eval == 0:
        return np.full_like(t_arr, dc)

    if order is not None:
        idx = order[:N_eval]
        k_vals = idx + 1  # 1-based harmonic frequencies
        a_vals = cos_coeffs[idx]
        b_vals = sin_coeffs[idx]
    else:
        k_vals = np.arange(1, N_eval + 1, dtype=np.float64)
        a_vals = cos_coeffs[:N_eval]
        b_vals = sin_coeffs[:N_eval]

    if use_lanczos:
        sigma = lanczos_sigma(N_eval)
        a_vals = a_vals * sigma
        b_vals = b_vals * sigma

    # Vectorized computation: shape (N_eval, len(t))
    # angles = k * t
    angles = np.outer(k_vals, t_arr)
    cos_terms = np.cos(angles)
    sin_terms = np.sin(angles)

    # Dot product along harmonic axis
    harmonic_sum = np.dot(a_vals, cos_terms) + np.dot(b_vals, sin_terms)
    return dc + harmonic_sum


def reconstruct_2d(
    t: np.ndarray,
    centre: Tuple[float, float],
    a: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    d: np.ndarray,
    N: Optional[int] = None,
    use_lanczos: bool = False,
    sort_by_amplitude: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    """Reconstruct 2D parametric curve P(t) = (x(t), y(t)) from Fourier coefficients.

    Args:
        t: Array of evaluation angles in radians.
        centre: (a0, c0) DC offset.
        a, b: Fourier coefficients for x(t).
        c, d: Fourier coefficients for y(t).
        N: Harmonic truncation order.
        use_lanczos: Whether to apply Lanczos sigma smoothing.
        sort_by_amplitude: Whether to sum harmonics in descending amplitude order.

    Returns:
        Tuple of (x_rec, y_rec) arrays evaluated at t.
    """
    a0, c0 = centre
    order_x, order_y = None, None
    if sort_by_amplitude:
        order_x, order_y = sort_harmonics_by_amplitude(a, b, c, d)

    x_rec = reconstruct_1d(t, a0, a, b, N=N, use_lanczos=use_lanczos, order=order_x)
    y_rec = reconstruct_1d(t, c0, c, d, N=N, use_lanczos=use_lanczos, order=order_y)
    return x_rec, y_rec


def compute_contour_error(
    x_true: np.ndarray,
    y_true: np.ndarray,
    x_rec: np.ndarray,
    y_rec: np.ndarray,
) -> Dict[str, float]:
    """Calculate reconstruction error relative to the original outline.

    Metrics:
      1. Mean nearest-neighbor distance (via scipy cKDTree), expressed as a percentage
         of the ground truth bounding-box diagonal.
      2. Symmetric Hausdorff distance, expressed as a percentage of the diagonal.

    Args:
        x_true, y_true: Ground truth outline coordinates (M,).
        x_rec, y_rec: Reconstructed curve coordinates (M,).

    Returns:
        Dict with keys:
          - 'mean_error_pct': Mean distance as % of bounding-box diagonal.
          - 'hausdorff_pct': Hausdorff distance as % of bounding-box diagonal.
          - 'bbox_diagonal': Bounding box diagonal length.
    """
    pts_true = np.column_stack([x_true, y_true])
    pts_rec = np.column_stack([x_rec, y_rec])

    # Bounding box diagonal of ground truth
    span_x = np.max(x_true) - np.min(x_true)
    span_y = np.max(y_true) - np.min(y_true)
    bbox_diagonal = float(np.hypot(span_x, span_y))

    if bbox_diagonal <= 0.0:
        return {"mean_error_pct": 0.0, "hausdorff_pct": 0.0, "bbox_diagonal": 1.0}

    # Query reconstructed points against ground truth tree
    tree_true = cKDTree(pts_true)
    dists_rec_to_true, _ = tree_true.query(pts_rec)
    mean_dist = float(np.mean(dists_rec_to_true))

    # Query ground truth against reconstructed tree for bidirectional Hausdorff
    tree_rec = cKDTree(pts_rec)
    dists_true_to_rec, _ = tree_rec.query(pts_true)
    hausdorff_dist = float(max(np.max(dists_rec_to_true), np.max(dists_true_to_rec)))

    mean_error_pct = (mean_dist / bbox_diagonal) * 100.0
    hausdorff_pct = (hausdorff_dist / bbox_diagonal) * 100.0

    return {
        "mean_error_pct": mean_error_pct,
        "hausdorff_pct": hausdorff_pct,
        "bbox_diagonal": bbox_diagonal,
    }


def compute_epicycle_chain_tips(
    t_val: float,
    root_origin: Tuple[float, float],
    a_or_c: np.ndarray,
    b_or_d: np.ndarray,
    N_total: int,
    max_visible: int = 25,
    order: Optional[np.ndarray] = None,
    component: str = "x",
) -> Tuple[List[Tuple[Tuple[float, float], float, Tuple[float, float]]], Tuple[float, float]]:
    """Compute the visual circles and exact tip coordinate for an orthogonal epicycle chain.

    For the X-chain:
      The 2D vector for harmonic k is:
        v_k = ( R_k * cos(k*t - φ_k),  R_k * sin(k*t - φ_k) )
      Notice:
        v_k.x = R_k * cos(k*t - φ_k) = a_k * cos(kt) + b_k * sin(kt)
      The sum of x-components gives the exact x(t) offset.

    For the Y-chain:
      The 2D vector for harmonic k is:
        w_k = ( R_k * sin(k*t - φ_k),  R_k * cos(k*t - φ_k) )
      Notice:
        w_k.y = R_k * cos(k*t - φ_k) = c_k * cos(kt) + d_k * sin(kt)
      The sum of y-components gives the exact y(t) offset.

    The first `max_visible` circles are rendered explicitly. Any remaining harmonics up
    to N_total are summed invisibly into the final tip so that the tip position is
    mathematically exact even at N = 1000.

    Args:
        t_val: Current angle in radians.
        root_origin: (x0, y0) base center coordinate of the first circle.
        a_or_c: Cosine coefficients array.
        b_or_d: Sine coefficients array.
        N_total: Total active harmonics (up to len(a_or_c)).
        max_visible: Number of epicycle circles to return for visual rendering.
        order: Permutation array (e.g. descending amplitude).
        component: 'x' or 'y'.

    Returns:
        Tuple of:
          - visible_circles: List of ((center_x, center_y), radius, (tip_x, tip_y))
          - final_exact_tip: (tip_x, tip_y) summing all N_total harmonics.
    """
    total = min(N_total, len(a_or_c))
    if order is None:
        idx = np.arange(total)
    else:
        idx = order[:total]

    k_vals = idx + 1
    a_vals = a_or_c[idx]
    b_vals = b_or_d[idx]

    R_vals, phi_vals = to_amplitude_phase(a_vals, b_vals)
    angles = k_vals * t_val - phi_vals

    if component == "x":
        dx_vals = R_vals * np.cos(angles)  # Exactly a*cos(kt) + b*sin(kt)
        dy_vals = R_vals * np.sin(angles)
    else:  # component == 'y'
        dx_vals = R_vals * np.sin(angles)
        dy_vals = R_vals * np.cos(angles)  # Exactly c*cos(kt) + d*sin(kt)

    visible_count = min(max_visible, total)
    visible_circles = []

    curr_x, curr_y = root_origin
    for i in range(visible_count):
        center = (curr_x, curr_y)
        radius = float(R_vals[i])
        next_x = curr_x + float(dx_vals[i])
        next_y = curr_y + float(dy_vals[i])
        tip = (next_x, next_y)
        visible_circles.append((center, radius, tip))
        curr_x, curr_y = next_x, next_y

    # Sum any remaining harmonics invisibly into the final exact tip
    if total > visible_count:
        tail_dx = float(np.sum(dx_vals[visible_count:]))
        tail_dy = float(np.sum(dy_vals[visible_count:]))
        final_tip = (curr_x + tail_dx, curr_y + tail_dy)
    else:
        final_tip = (curr_x, curr_y)

    return visible_circles, final_tip
