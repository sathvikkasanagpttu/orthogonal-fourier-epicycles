"""Configuration constants and aesthetic styling for Orthogonal Fourier Epicycles.

This module centralizes all file system paths, color schemes, layout dimensions,
video parameters, and mathematical defaults to ensure reproducible rendering.
"""

from pathlib import Path

# ==============================================================================
# 1. FILE SYSTEM & DIRECTORIES
# ==============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
WEB_DIR = PROJECT_ROOT / "web"

GEOJSON_PATH = DATA_DIR / "india_outline.geojson"
MASK_PNG_PATH = DATA_DIR / "india_mask.png"
WEB_COEFFS_JSON_PATH = WEB_DIR / "coefficients.json"

# ==============================================================================
# 2. COLOR PALETTE (Reference Match: Near-Black Theme)
# ==============================================================================
# Background & Silhouette
COLOR_BG = "#05070d"               # Deepest navy / near-black canvas
COLOR_SILHOUETTE_FILL = "#0b1220"  # Subtle filled silhouette behind trace
COLOR_SILHOUETTE_STROKE = "#162035"# Faint boundary stroke for silhouette
SILHOUETTE_OPACITY = 0.65

# Epicycles & Equations
COLOR_X = "#00d2d3"                # Vibrant cyan / teal for x(t) chain and equation
COLOR_X_PALE = "#007a7b"           # Dimmer cyan for secondary harmonics
COLOR_Y = "#f5a623"                # Warm gold / amber for y(t) chain and equation
COLOR_Y_PALE = "#8a5d14"           # Dimmer gold for secondary harmonics

# Traced Outline & Drawing Point
COLOR_PATH = "#ff6b6b"             # Coral / orange for outline & P(t) equation
COLOR_PATH_GLOW = "#ff8787"        # Bright coral outer glow
COLOR_DOT = "#ffffff"              # Glowing white core for current drawing point
COLOR_DOT_HALO = "#ff9e9e"         # Soft coral halo around drawing dot

# Typography & Accents
COLOR_TEXT_PRIMARY = "#ffffff"     # Main white text
COLOR_TEXT_MUTED = "#8892b0"       # Muted slate for subtitles & labels
COLOR_DIVIDER = "#1f293d"          # Clean dark horizontal divider rule

# ==============================================================================
# 3. MATHEMATICAL & SAMPLING CONSTANTS
# ==============================================================================
M_SAMPLES = 8192                   # Number of uniform arc-length sample points (2^13)
N_MAX_HARMONICS = 1000             # Maximum Fourier harmonic order
DEFAULT_SWEEP_N = [1, 3, 5, 10, 25, 100, 300, 1000]
SORT_BY_AMPLITUDE = True           # Stack epicycles from largest to smallest amplitude
LANCZOS_SMOOTHING = False          # Optional sigma-smoothing to tame Gibbs overshoot

# ==============================================================================
# 4. MANIM CANVAS & VIDEO SETTINGS
# ==============================================================================
# Default is 9:16 vertical video format (1080x1920) for mobile/reels/shorts
ASPECT_RATIO_VERTICAL = "9:16"
VERTICAL_PIXEL_WIDTH = 1080
VERTICAL_PIXEL_HEIGHT = 1920

# 16:9 landscape alternative
LANDSCAPE_PIXEL_WIDTH = 1920
LANDSCAPE_PIXEL_HEIGHT = 1080

FPS = 60                           # High quality 60 frames per second
FRAME_HEIGHT_VERTICAL = 16.0       # Manim coordinate vertical span [-8.0, 8.0]
FRAME_WIDTH_VERTICAL = 9.0         # Manim coordinate horizontal span [-4.5, 4.5]

# ==============================================================================
# 5. SPATIAL LAYOUT COORDINATES (Vertical Format)
# ==============================================================================
# India Outline Placement (Bottom-Left)
OUTLINE_CENTER = [-2.15, -3.9, 0.0]
OUTLINE_SCALE = 3.8

# X-Chain Epicycles Placement (Top-Left)
# Horizontal coordinate MUST match outline center x + scaled a0 for vertical alignment!
X_CHAIN_CENTER_Y = 3.2
X_CHAIN_MAX_VISIBLE = 25           # Draw top 25 circles; sum rest invisibly

# Y-Chain Epicycles Placement (Bottom-Right)
# Vertical coordinate MUST match outline center y + scaled c0 for horizontal alignment!
Y_CHAIN_CENTER_X = 2.15
Y_CHAIN_MAX_VISIBLE = 25           # Draw top 25 circles; sum rest invisibly

# Line Widths & Opacities
STROKE_WIDTH_CIRCLE = 1.0
STROKE_WIDTH_RADIUS = 1.3
STROKE_WIDTH_PATH = 2.4
STROKE_WIDTH_DASH = 1.2
DASH_LENGTH = 0.09
DASH_SPACING = 0.07
DOT_RADIUS = 0.08
DOT_HALO_RADIUS = 0.18

# Right Column Stat & Equation Coordinates
STATS_TOP_Y = 5.2                  # "N = 1000" position
ERROR_TOP_Y = 4.35                 # "error = 0.02%" position
DIVIDER_Y = 3.65                   # Horizontal line separator
EQ_X_Y = 2.8                       # x(t) equation y-position
EQ_Y_Y = 1.9                       # y(t) equation y-position
EQ_P_Y = 1.0                       # P(t) equation y-position
EQUATION_COLUMN_X = 2.25           # Center x for stats & equations
