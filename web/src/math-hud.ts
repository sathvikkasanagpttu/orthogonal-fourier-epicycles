/**
 * HUD & Mathematical Equations renderer using KaTeX.
 */

import katex from "katex";

export class MathHUD {
  private eqXEl: HTMLElement | null;
  private eqYEl: HTMLElement | null;
  private eqPEl: HTMLElement | null;
  private nDisplayEl: HTMLElement | null;
  private errorDisplayEl: HTMLElement | null;
  private mapTitleEl: HTMLElement | null;
  private ringStatusEl: HTMLElement | null;

  constructor() {
    this.eqXEl = document.getElementById("hudEqX");
    this.eqYEl = document.getElementById("hudEqY");
    this.eqPEl = document.getElementById("hudEqP");
    this.nDisplayEl = document.getElementById("hudN");
    this.errorDisplayEl = document.getElementById("hudError");
    this.mapTitleEl = document.getElementById("hudMapTitle");
    this.ringStatusEl = document.getElementById("hudRingStatus");

    this.renderFormulas();
  }

  public renderFormulas(): void {
    if (this.eqXEl) {
      katex.render(
        "x(t) = \\sum_{k=1}^N \\left( a_k \\cos kt + b_k \\sin kt \\right)",
        this.eqXEl,
        { displayMode: false, throwOnError: false }
      );
    }
    if (this.eqYEl) {
      katex.render(
        "y(t) = \\sum_{k=1}^N \\left( c_k \\cos kt + d_k \\sin kt \\right)",
        this.eqYEl,
        { displayMode: false, throwOnError: false }
      );
    }
    if (this.eqPEl) {
      katex.render(
        "\\mathbf{P}(t) = (x(t), y(t))",
        this.eqPEl,
        { displayMode: false, throwOnError: false }
      );
    }
  }

  public updateStats(
    mapName: string,
    N: number,
    errorPct: number,
    currentRing: number,
    totalRings: number
  ): void {
    if (this.mapTitleEl) {
      this.mapTitleEl.textContent = mapName;
    }
    if (this.nDisplayEl) {
      this.nDisplayEl.textContent = `N = ${N}`;
    }
    if (this.errorDisplayEl) {
      this.errorDisplayEl.textContent = `error = ${errorPct.toFixed(2)}%`;
    }
    if (this.ringStatusEl) {
      if (totalRings > 1) {
        this.ringStatusEl.style.display = "block";
        this.ringStatusEl.textContent = `Part ${currentRing + 1} of ${totalRings}`;
      } else {
        this.ringStatusEl.style.display = "none";
      }
    }
  }
}
