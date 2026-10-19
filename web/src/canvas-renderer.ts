/**
 * 60 FPS HTML5 Canvas Renderer for Orthogonal Fourier Epicycles.
 *
 * Implements:
 *   - Responsive vertical (9:16) and landscape layouts
 *   - Independent X (teal) and Y (gold) epicycle chains
 *   - Orthogonal dashed projection lines meeting at P(t)
 *   - Soft glow traced outline with multi-ring persistent accumulation
 *   - Theme support (Dark & Light)
 */

import { computeChain } from "./fourier-worker";
import { AppState, FourierChain, MapData, RingData } from "./types";

export interface Point2D {
  x: number;
  y: number;
}

export class CanvasRenderer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private width: number = 540;
  private height: number = 960;
  private dpr: number = 1;

  // Traced points for current active ring
  private activeTracedPath: Point2D[] = [];
  // Completed rings permanently preserved
  private completedRings: Point2D[][] = [];
  private lastRingIndex: number = -1;
  private lastMapId: string = "";

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Could not obtain CanvasRenderingContext2D");
    }
    this.ctx = context;
    this.resize();
    window.addEventListener("resize", () => this.resize());
  }

  public resize(): void {
    const rect = this.canvas.parentElement?.getBoundingClientRect();
    if (!rect) return;

    this.width = rect.width;
    this.height = rect.height;
    this.dpr = window.devicePixelRatio || 1;

    this.canvas.width = this.width * this.dpr;
    this.canvas.height = this.height * this.dpr;
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
  }

  public resetPath(): void {
    this.activeTracedPath = [];
    this.completedRings = [];
    this.lastRingIndex = -1;
  }

  public getCanvas(): HTMLCanvasElement {
    return this.canvas;
  }

  public render(state: AppState): void {
    const { ctx, width, height } = this;
    const isDark = state.theme === "dark";

    // 1. Clear background
    ctx.fillStyle = isDark ? "#05070d" : "#f8fafc";
    ctx.fillRect(0, 0, width, height);

    if (!state.mapData || state.mapData.rings.length === 0) {
      ctx.fillStyle = isDark ? "#8892b0" : "#64748b";
      ctx.font = "14px monospace";
      ctx.textAlign = "center";
      ctx.fillText("Select a country or territory to render...", width / 2, height / 2);
      return;
    }

    // Map changed: reset paths
    if (state.selectedMapId !== this.lastMapId) {
      this.resetPath();
      this.lastMapId = state.selectedMapId;
    }

    const map = state.mapData;
    // Determine active rings according to detail level
    let activeRings = map.rings;
    if (state.detailLevel === "main") {
      activeRings = [map.rings[0]];
    } else if (state.detailLevel === "large") {
      activeRings = map.rings.filter(
        (r, i) => i === 0 || r.area_ratio >= 0.005 || i < 8
      );
    }

    const ringCount = activeRings.length;
    const currentRingIdx = Math.min(state.activeRingIndex, ringCount - 1);
    const ring = activeRings[currentRingIdx];

    // If active ring advanced, archive the finished ring into completedRings
    if (currentRingIdx !== this.lastRingIndex) {
      if (this.activeTracedPath.length > 5) {
        this.completedRings.push([...this.activeTracedPath]);
      }
      this.activeTracedPath = [];
      this.lastRingIndex = currentRingIdx;
    }

    // Dynamic Layout Calculation
    // Outline Area placed at bottom-left
    const isPortrait = height >= width * 1.2;
    const outlineScale = isPortrait ? width * 0.44 : height * 0.45;
    const outlineCenter: Point2D = isPortrait
      ? { x: width * 0.27, y: height * 0.73 }
      : { x: width * 0.32, y: height * 0.62 };

    // Base origins
    const a0 = ring.x_chain.a0 || 0;
    const c0 = ring.y_chain.c0 || 0;

    const xChainOrigin: Point2D = isPortrait
      ? { x: outlineCenter.x + a0 * outlineScale, y: height * 0.27 }
      : { x: outlineCenter.x + a0 * outlineScale, y: height * 0.22 };

    const yChainOrigin: Point2D = isPortrait
      ? { x: width * 0.75, y: outlineCenter.y - c0 * outlineScale }
      : { x: width * 0.78, y: outlineCenter.y - c0 * outlineScale };

    // Scale chains
    const scaledXChain: FourierChain = {
      ...ring.x_chain,
      R: ring.x_chain.R.map((r) => r * outlineScale),
    };
    const scaledYChain: FourierChain = {
      ...ring.y_chain,
      R: ring.y_chain.R.map((r) => r * outlineScale),
    };

    // Compute Epicycle Chains
    const xRes = computeChain(
      state.currentT,
      xChainOrigin,
      scaledXChain,
      state.activeN,
      25,
      true,
      state.useLanczos
    );
    const yRes = computeChain(
      state.currentT,
      yChainOrigin,
      scaledYChain,
      state.activeN,
      25,
      false,
      state.useLanczos
    );

    // Current drawing point P(t) = (X_tip.x, Y_tip.y)
    const P: Point2D = { x: xRes.tip.x, y: yRes.tip.y };

    if (state.isPlaying) {
      this.activeTracedPath.push({ ...P });
      if (this.activeTracedPath.length > 3000) {
        this.activeTracedPath.shift();
      }
    }

    // 2. Render Faint Ground Truth Silhouette
    if (state.showSilhouette) {
      ctx.fillStyle = isDark ? "rgba(11, 18, 32, 0.7)" : "rgba(226, 232, 240, 0.6)";
      ctx.strokeStyle = isDark ? "rgba(22, 32, 53, 0.9)" : "rgba(203, 213, 225, 0.8)";
      ctx.lineWidth = 1;

      for (const r of activeRings) {
        if (!r.ground_truth?.x) continue;
        const gx = r.ground_truth.x;
        const gy = r.ground_truth.y;
        ctx.beginPath();
        for (let i = 0; i < gx.length; i++) {
          const px = outlineCenter.x + gx[i] * outlineScale;
          const py = outlineCenter.y - gy[i] * outlineScale;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }
    }

    // 3. Render Ground Truth Outline Overlay (if toggled)
    if (state.showGroundTruth && ring.ground_truth?.x) {
      ctx.strokeStyle = isDark ? "rgba(255, 255, 255, 0.2)" : "rgba(0, 0, 0, 0.2)";
      ctx.lineWidth = 1.2;
      ctx.setLineDash([2, 2]);
      ctx.beginPath();
      const gx = ring.ground_truth.x;
      const gy = ring.ground_truth.y;
      for (let i = 0; i < gx.length; i++) {
        const px = outlineCenter.x + gx[i] * outlineScale;
        const py = outlineCenter.y - gy[i] * outlineScale;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 4. Render Completed Prior Rings
    for (const path of this.completedRings) {
      if (path.length < 2) continue;
      ctx.strokeStyle = "#ff6b6b";
      ctx.lineWidth = 2.0;
      ctx.beginPath();
      ctx.moveTo(path[0].x, path[0].y);
      for (let i = 1; i < path.length; i++) {
        ctx.lineTo(path[i].x, path[i].y);
      }
      ctx.stroke();
    }

    // 5. Render Current Active Traced Path (Coral with Soft Glow)
    if (this.activeTracedPath.length > 1) {
      ctx.save();
      ctx.shadowColor = "#ff6b6b";
      ctx.shadowBlur = 10;
      ctx.strokeStyle = "#ff6b6b";
      ctx.lineWidth = 2.4;
      ctx.beginPath();
      ctx.moveTo(this.activeTracedPath[0].x, this.activeTracedPath[0].y);
      for (let i = 1; i < this.activeTracedPath.length; i++) {
        ctx.lineTo(this.activeTracedPath[i].x, this.activeTracedPath[i].y);
      }
      ctx.stroke();
      ctx.restore();
    }

    // 6. Render Epicycle Chains (Circles + Radius Vectors)
    if (state.showCircles) {
      // X-Chain (Cyan / Teal)
      ctx.strokeStyle = isDark ? "rgba(0, 210, 211, 0.45)" : "rgba(14, 165, 233, 0.5)";
      ctx.lineWidth = 1.0;
      for (const c of xRes.circles) {
        if (c.r > 1.0) {
          ctx.beginPath();
          ctx.arc(c.cx, c.cy, c.r, 0, 2 * Math.PI);
          ctx.stroke();
        }
        ctx.beginPath();
        ctx.moveTo(c.cx, c.cy);
        ctx.lineTo(c.tx, c.ty);
        ctx.stroke();
      }

      // Y-Chain (Gold / Amber)
      ctx.strokeStyle = isDark ? "rgba(245, 166, 35, 0.45)" : "rgba(217, 119, 6, 0.5)";
      for (const c of yRes.circles) {
        if (c.r > 1.0) {
          ctx.beginPath();
          ctx.arc(c.cx, c.cy, c.r, 0, 2 * Math.PI);
          ctx.stroke();
        }
        ctx.beginPath();
        ctx.moveTo(c.cx, c.cy);
        ctx.lineTo(c.tx, c.ty);
        ctx.stroke();
      }
    }

    // Chain Labels
    ctx.font = "italic 15px Georgia, serif";
    ctx.textAlign = "center";
    ctx.fillStyle = isDark ? "#00d2d3" : "#0284c7";
    ctx.fillText("X(t) chain", xChainOrigin.x, xChainOrigin.y - outlineScale * 0.55);

    ctx.fillStyle = isDark ? "#f5a623" : "#d97706";
    ctx.fillText("Y(t) chain", yChainOrigin.x, yChainOrigin.y + outlineScale * 0.6);

    // 7. Render Orthogonal Dashed Projection Lines
    if (state.showProjectionLines) {
      ctx.save();
      ctx.setLineDash([4, 4]);

      // Vertical line from X tip down to P(t)
      ctx.strokeStyle = isDark ? "rgba(0, 210, 211, 0.75)" : "rgba(14, 165, 233, 0.8)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(xRes.tip.x, xRes.tip.y);
      ctx.lineTo(P.x, P.y);
      ctx.stroke();

      // Horizontal line from Y tip across to P(t)
      ctx.strokeStyle = isDark ? "rgba(245, 166, 35, 0.75)" : "rgba(217, 119, 6, 0.8)";
      ctx.beginPath();
      ctx.moveTo(yRes.tip.x, yRes.tip.y);
      ctx.lineTo(P.x, P.y);
      ctx.stroke();
      ctx.restore();
    }

    // 8. Render Glowing Drawing Point P(t)
    ctx.save();
    ctx.shadowColor = "#ff6b6b";
    ctx.shadowBlur = 12;
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(P.x, P.y, 4, 0, 2 * Math.PI);
    ctx.fill();

    ctx.strokeStyle = "rgba(255, 107, 107, 0.6)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(P.x, P.y, 9, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.restore();
  }
}
