"""Unit test suite for Orthogonal Fourier Epicycles mathematics and geometry.

Covers:
  - FFT coefficient correctness validated against direct numerical integration
  - Exact signal reconstruction at Nyquist limit (N = M // 2)
  - Polar epicycle amplitude-phase mathematical equivalence
  - Closed-curve continuity: P(0) == P(2π)
  - Arc-length uniformity after resampling
  - Error metrics monotonic reduction with increasing N
  - Epicycle tip alignment: X-tip x == x(t) and Y-tip y == y(t)
"""

import numpy as np
import pytest

from src.fourier import (
    compute_coefficients,
    compute_contour_error,
    compute_epicycle_chain_tips,
    lanczos_sigma,
    reconstruct_1d,
    reconstruct_2d,
    sort_harmonics_by_amplitude,
    to_amplitude_phase,
)
from src.outline import (
    clean_contour,
    normalize_contour,
    resample_arc_length,
)


@pytest.fixture
def synthetic_signal():
    """Generates an analytic periodic test signal with known Fourier coefficients."""
    M = 4096
    t = np.linspace(0, 2 * np.pi, M, endpoint=False)
    # Known: a0 = 1.5, a1 = 2.0, b1 = -1.2, a3 = 0.5, b5 = 0.8
    x = 1.5 + 2.0 * np.cos(t) - 1.2 * np.sin(t) + 0.5 * np.cos(3 * t) + 0.8 * np.sin(5 * t)
    # Known: c0 = -0.5, c1 = 1.0, d2 = 1.5, c4 = -0.4
    y = -0.5 + 1.0 * np.cos(t) + 1.5 * np.sin(2 * t) - 0.4 * np.cos(4 * t)
    return t, x, y


def test_coefficients_fft_vs_numerical_integral(synthetic_signal):
    """Validate that FFT-derived coefficients match numerical Riemann integration."""
    t, x, y = synthetic_signal
    M = len(t)
    dt = 2 * np.pi / M

    (a0_fft, c0_fft), a_fft, b_fft, c_fft, d_fft = compute_coefficients(x, y, N_harmonics=10)

    # Direct numerical integration:
    # a0 = (1 / 2π) * integral x(t) dt
    # a_k = (1 / π) * integral x(t) * cos(kt) dt
    # b_k = (1 / π) * integral x(t) * sin(kt) dt
    a0_integral = np.sum(x) * dt / (2 * np.pi)
    c0_integral = np.sum(y) * dt / (2 * np.pi)

    assert np.isclose(a0_fft, a0_integral, atol=1e-10)
    assert np.isclose(c0_fft, c0_integral, atol=1e-10)

    for k in range(1, 11):
        a_k_integral = np.sum(x * np.cos(k * t)) * dt / np.pi
        b_k_integral = np.sum(x * np.sin(k * t)) * dt / np.pi
        assert np.isclose(a_fft[k - 1], a_k_integral, atol=1e-10)
        assert np.isclose(b_fft[k - 1], b_k_integral, atol=1e-10)


def test_reconstruction_at_nyquist(synthetic_signal):
    """Reconstruction using all available harmonics must reproduce the original within tolerance."""
    t, x, y = synthetic_signal
    M = len(t)

    centre, a, b, c, d = compute_coefficients(x, y, N_harmonics=M // 2)
    x_rec, y_rec = reconstruct_2d(t, centre, a, b, c, d, N=M // 2)

    assert np.allclose(x, x_rec, atol=1e-10)
    assert np.allclose(y, y_rec, atol=1e-10)


def test_amplitude_phase_equivalence():
    """Verify R cos(kt - φ) == a cos(kt) + b sin(kt) for arbitrary coefficients."""
    np.random.seed(42)
    a = np.random.randn(50)
    b = np.random.randn(50)

    R, phi = to_amplitude_phase(a, b)

    t = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    for k in range(1, 51):
        lhs = a[k - 1] * np.cos(k * t) + b[k - 1] * np.sin(k * t)
        rhs = R[k - 1] * np.cos(k * t - phi[k - 1])
        assert np.allclose(lhs, rhs, atol=1e-12)


def test_closed_curve_continuity():
    """Ensure that the parametric curve is closed: P(0) == P(2π)."""
    t_endpoints = np.array([0.0, 2.0 * np.pi])
    a = np.array([0.5, -0.2, 0.1])
    b = np.array([0.3, 0.4, -0.15])
    c = np.array([0.2, 0.1, -0.3])
    d = np.array([-0.1, 0.4, 0.2])

    x_rec, y_rec = reconstruct_2d(t_endpoints, (0.0, 0.0), a, b, c, d, N=3)

    assert np.isclose(x_rec[0], x_rec[1], atol=1e-12)
    assert np.isclose(y_rec[0], y_rec[1], atol=1e-12)


def test_outline_arc_length_uniformity():
    """Verify that arc-length resampling produces segments of near-equal chord length."""
    # Create an arbitrary polygon (e.g. an irregular star)
    theta = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    r = 1.0 + 0.3 * np.sin(5 * theta)
    pts = np.column_stack([r * np.cos(theta), r * np.sin(theta)])
    pts = clean_contour(pts)

    M = 1000
    xr, yr = resample_arc_length(pts, M=M)
    resampled_pts = np.column_stack([xr, yr])

    diffs = np.diff(resampled_pts, axis=0)
    dists = np.hypot(diffs[:, 0], diffs[:, 1])

    # Standard deviation of step lengths should be extremely small
    mean_dist = np.mean(dists)
    std_dist = np.std(dists)
    rel_std = std_dist / mean_dist

    assert rel_std < 0.02, f"Relative standard deviation {rel_std} too large for uniform arc length."


def test_error_monotonic_decrease():
    """Verify that error metrics monotonically decrease as N increases on a non-bandlimited curve."""
    # Create a non-bandlimited polygonal contour (e.g. square/diamond)
    t_dense = np.linspace(0, 2 * np.pi, 2048, endpoint=False)
    # Triangle wave / piecewise linear curve with infinite harmonic spectrum
    x = np.abs((t_dense % np.pi) - np.pi / 2.0) - np.pi / 4.0
    y = np.abs(((t_dense + np.pi / 4.0) % np.pi) - np.pi / 2.0) - np.pi / 4.0

    centre, a, b, c, d = compute_coefficients(x, y, N_harmonics=200)

    n_values = [1, 3, 10, 30, 100]
    errors = []

    for N in n_values:
        xr, yr = reconstruct_2d(t_dense, centre, a, b, c, d, N=N)
        err = compute_contour_error(x, y, xr, yr)["mean_error_pct"]
        errors.append(err)

    for i in range(len(errors) - 1):
        assert errors[i] > errors[i + 1], f"Error did not strictly decrease: N={n_values[i]} ({errors[i]:.4f}%) vs N={n_values[i+1]} ({errors[i+1]:.4f}%)"



def test_epicycle_chain_tip_alignment():
    """Verify that the X-chain tip x-coordinate matches x(t) and Y-chain tip y-coordinate matches y(t)."""
    np.random.seed(123)
    N = 40
    a = np.random.randn(N) * 0.1
    b = np.random.randn(N) * 0.1
    c = np.random.randn(N) * 0.1
    d = np.random.randn(N) * 0.1
    a0, c0 = 0.5, -0.3

    origin_x = (a0, 3.0)
    origin_y = (4.0, c0)

    for t_test in [0.0, 0.5, 1.2, 2.8, 4.5, 5.9]:
        # Exact values from 1D reconstruction
        x_expected = reconstruct_1d(np.array([t_test]), a0, a, b, N=N)[0]
        y_expected = reconstruct_1d(np.array([t_test]), c0, c, d, N=N)[0]

        # Epicycle tips with only 10 visible circles (tail summed invisibly)
        _, tip_x = compute_epicycle_chain_tips(t_test, origin_x, a, b, N_total=N, max_visible=10, component="x")
        _, tip_y = compute_epicycle_chain_tips(t_test, origin_y, c, d, N_total=N, max_visible=10, component="y")

        assert np.isclose(tip_x[0], x_expected, atol=1e-12), f"X-chain tip x mismatch: {tip_x[0]} vs {x_expected}"
        assert np.isclose(tip_y[1], y_expected, atol=1e-12), f"Y-chain tip y mismatch: {tip_y[1]} vs {y_expected}"
