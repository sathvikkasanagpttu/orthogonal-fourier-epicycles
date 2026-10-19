/**
 * Main application entrypoint for Orthogonal Fourier Epicycles: World Atlas Edition.
 */

import "katex/dist/katex.min.css";
import "./style.css";

import { CanvasRenderer } from "./canvas-renderer";
import {
  exportCanvasPNG,
  exportCoefficientsCSV,
  exportCoefficientsJSON,
  recordCanvasWebM,
  VideoRecorderController,
} from "./export-utils";
import { LeaderboardModal } from "./leaderboard";
import { MathHUD } from "./math-hud";
import { AppState, AtlasIndexEntry, DetailLevel, MapData } from "./types";

class WorldAtlasApp {
  private state: AppState;
  private renderer: CanvasRenderer;
  private mathHud: MathHUD;
  private leaderboard: LeaderboardModal;
  private indexEntries: AtlasIndexEntry[] = [];
  private activeContinentFilter: string = "All";
  private searchQuery: string = "";
  private lastTime: number = 0;
  private activeRecorder: VideoRecorderController | null = null;

  constructor() {
    const urlParams = new URLSearchParams(window.location.search);
    const initialMap = urlParams.get("map") || "IND";
    const initialN = parseInt(urlParams.get("n") || "120", 10);
    const initialSpeed = parseFloat(urlParams.get("speed") || "1.0");
    const initialDetail = (urlParams.get("detail") as DetailLevel) || "all";

    this.state = {
      selectedMapId: initialMap,
      mapData: null,
      activeN: isNaN(initialN) ? 120 : Math.max(1, Math.min(1000, initialN)),
      speed: isNaN(initialSpeed) ? 1.0 : initialSpeed,
      isPlaying: true,
      showCircles: true,
      showProjectionLines: true,
      showSilhouette: false,
      showGroundTruth: false,
      useLanczos: false,
      detailLevel: initialDetail,
      theme: "dark",
      currentT: 0,
      activeRingIndex: 0,
      isCompareMode: false,
      compareMapId: null,
      compareMapData: null,
      isAutoSweep: false,
    };

    const canvas = document.getElementById("epicycleCanvas") as HTMLCanvasElement;
    if (!canvas) throw new Error("Canvas element #epicycleCanvas not found");

    this.renderer = new CanvasRenderer(canvas);
    this.mathHud = new MathHUD();
    this.leaderboard = new LeaderboardModal((mapId) => this.selectMap(mapId));

    this.initEvents();
    this.loadIndex();
  }

  private async loadIndex(): Promise<void> {
    try {
      const res = await fetch("/atlas/index.json");
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      this.indexEntries = await res.json();
      this.renderSidebarList();
      await this.selectMap(this.state.selectedMapId);
    } catch (err) {
      console.error("Failed to load atlas/index.json:", err);
      // Fallback: load directly if local
      this.selectMap(this.state.selectedMapId);
    }
  }

  public async selectMap(mapId: string): Promise<void> {
    const entry = this.indexEntries.find((e) => e.id === mapId);
    let filePath = `/atlas/maps/${mapId}.json`;
    if (entry && entry.file) {
      filePath = `/atlas/${entry.file}`;
    }

    try {
      const res = await fetch(filePath);
      if (!res.ok) throw new Error(`Failed to load ${filePath}`);
      const data: MapData = await res.json();

      this.state.selectedMapId = mapId;
      this.state.mapData = data;
      this.state.currentT = 0;
      this.state.activeRingIndex = 0;
      this.renderer.resetPath();

      // Adjust slider max N to match main ring's available harmonics
      const mainRing = data.rings[0];
      const maxAvailableN = mainRing ? mainRing.N : 200;
      const sliderN = document.getElementById("sliderN") as HTMLInputElement;
      if (sliderN) {
        sliderN.max = maxAvailableN.toString();
        if (this.state.activeN > maxAvailableN) {
          this.state.activeN = maxAvailableN;
          sliderN.value = maxAvailableN.toString();
        }
      }

      this.updateUrlParams();
      this.updateControlsUI();
      this.renderSidebarList();
    } catch (err) {
      console.error(`Could not load map data for ${mapId}:`, err);
    }
  }

  private updateUrlParams(): void {
    const url = new URL(window.location.href);
    url.searchParams.set("map", this.state.selectedMapId);
    url.searchParams.set("n", this.state.activeN.toString());
    url.searchParams.set("speed", this.state.speed.toString());
    url.searchParams.set("detail", this.state.detailLevel);
    window.history.replaceState({}, "", url.toString());
  }

  private renderSidebarList(): void {
    const container = document.getElementById("mapListContainer");
    if (!container) return;

    const query = this.searchQuery.toLowerCase().trim();
    const filtered = this.indexEntries.filter((item) => {
      const matchesSearch =
        item.name.toLowerCase().includes(query) ||
        item.id.toLowerCase().includes(query) ||
        item.continent.toLowerCase().includes(query);

      const matchesContinent =
        this.activeContinentFilter === "All" ||
        item.continent.toLowerCase() === this.activeContinentFilter.toLowerCase() ||
        (this.activeContinentFilter === "World" && item.id === "WLD") ||
        (this.activeContinentFilter === "Continents" && item.id.startsWith("CONT_"));

      return matchesSearch && matchesContinent;
    });

    container.innerHTML = filtered
      .map(
        (item) => `
      <div class="map-card ${item.id === this.state.selectedMapId ? "active" : ""}" data-id="${item.id}">
        <div class="map-info">
          <span class="map-name">${item.name}</span>
          <span class="map-meta">
            <span class="badge">${item.id}</span>
            <span>${item.continent}</span>
            ${item.ring_count > 1 ? `<span>• ${item.ring_count} parts</span>` : ""}
          </span>
        </div>
      </div>
    `
      )
      .join("");

    container.querySelectorAll(".map-card").forEach((card) => {
      card.addEventListener("click", () => {
        const id = card.getAttribute("data-id");
        if (id) this.selectMap(id);
      });
    });
  }

  private initEvents(): void {
    // Search input
    const searchInput = document.getElementById("searchInput") as HTMLInputElement;
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        this.searchQuery = searchInput.value;
        this.renderSidebarList();
      });
    }

    // Continent filter chips
    document.querySelectorAll(".chip-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        document.querySelectorAll(".chip-btn").forEach((b) => b.classList.remove("active"));
        const target = e.currentTarget as HTMLElement;
        target.classList.add("active");
        this.activeContinentFilter = target.getAttribute("data-continent") || "All";
        this.renderSidebarList();
      });
    });

    // N Slider & Number input
    const sliderN = document.getElementById("sliderN") as HTMLInputElement;
    const valN = document.getElementById("valN");
    if (sliderN && valN) {
      sliderN.addEventListener("input", () => {
        this.state.activeN = parseInt(sliderN.value, 10);
        valN.textContent = sliderN.value;
        this.updateUrlParams();
      });
    }

    // N Step Buttons
    document.getElementById("btnNMinus")?.addEventListener("click", () => {
      this.state.activeN = Math.max(1, this.state.activeN - 10);
      if (sliderN) sliderN.value = this.state.activeN.toString();
      if (valN) valN.textContent = this.state.activeN.toString();
      this.updateUrlParams();
    });

    document.getElementById("btnNPlus")?.addEventListener("click", () => {
      const maxN = parseInt(sliderN.max || "500", 10);
      this.state.activeN = Math.min(maxN, this.state.activeN + 10);
      if (sliderN) sliderN.value = this.state.activeN.toString();
      if (valN) valN.textContent = this.state.activeN.toString();
      this.updateUrlParams();
    });

    // Speed Slider
    const sliderSpeed = document.getElementById("sliderSpeed") as HTMLInputElement;
    const valSpeed = document.getElementById("valSpeed");
    if (sliderSpeed && valSpeed) {
      sliderSpeed.addEventListener("input", () => {
        this.state.speed = parseFloat(sliderSpeed.value);
        valSpeed.textContent = `${this.state.speed.toFixed(1)}x`;
        this.updateUrlParams();
      });
    }

    // Play/Pause button
    const btnPlayPause = document.getElementById("btnPlayPause");
    if (btnPlayPause) {
      btnPlayPause.addEventListener("click", () => {
        this.state.isPlaying = !this.state.isPlaying;
        btnPlayPause.textContent = this.state.isPlaying ? "⏸ Pause" : "▶ Play";
      });
    }

    // Reset button
    document.getElementById("btnReset")?.addEventListener("click", () => {
      this.state.currentT = 0;
      this.state.activeRingIndex = 0;
      this.renderer.resetPath();
    });

    // Detail level selector
    const selectDetail = document.getElementById("selectDetail") as HTMLSelectElement;
    if (selectDetail) {
      selectDetail.addEventListener("change", () => {
        this.state.detailLevel = selectDetail.value as DetailLevel;
        this.state.currentT = 0;
        this.state.activeRingIndex = 0;
        this.renderer.resetPath();
        this.updateUrlParams();
      });
    }

    // Toggles
    const bindToggle = (id: string, prop: keyof AppState) => {
      const el = document.getElementById(id) as HTMLInputElement;
      if (el) {
        el.addEventListener("change", () => {
          (this.state as any)[prop] = el.checked;
        });
      }
    };
    bindToggle("toggleCircles", "showCircles");
    bindToggle("toggleProjections", "showProjectionLines");
    bindToggle("toggleLanczos", "useLanczos");
    bindToggle("toggleSilhouette", "showSilhouette");
    bindToggle("toggleGroundTruth", "showGroundTruth");
    bindToggle("toggleAutoSweep", "isAutoSweep");

    // Random country button
    document.getElementById("btnRandom")?.addEventListener("click", () => {
      this.pickRandomMap();
    });

    // Leaderboard button
    document.getElementById("btnLeaderboard")?.addEventListener("click", () => {
      this.leaderboard.show();
    });

    // Theme toggle
    document.getElementById("btnTheme")?.addEventListener("click", () => {
      this.state.theme = this.state.theme === "dark" ? "light" : "dark";
      document.body.classList.toggle("theme-light", this.state.theme === "light");
    });

    // Exports
    document.getElementById("btnExportPNG")?.addEventListener("click", () => {
      exportCanvasPNG(this.renderer.getCanvas(), `${this.state.selectedMapId}_N${this.state.activeN}.png`);
    });

    document.getElementById("btnRecordWebM")?.addEventListener("click", () => {
      this.handleRecordVideo();
    });

    document.getElementById("btnExportJSON")?.addEventListener("click", () => {
      if (this.state.mapData) {
        exportCoefficientsJSON(this.state.mapData, this.state.activeN);
      }
    });

    document.getElementById("btnExportCSV")?.addEventListener("click", () => {
      if (this.state.mapData) {
        exportCoefficientsCSV(this.state.mapData, this.state.activeN);
      }
    });

    // Keyboard shortcuts
    window.addEventListener("keydown", (e) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      if (e.code === "Space") {
        e.preventDefault();
        this.state.isPlaying = !this.state.isPlaying;
        if (btnPlayPause) {
          btnPlayPause.textContent = this.state.isPlaying ? "⏸ Pause" : "▶ Play";
        }
      } else if (e.code === "KeyR") {
        this.pickRandomMap();
      } else if (e.code === "KeyL") {
        this.leaderboard.show();
      } else if (e.code === "KeyC") {
        this.state.currentT = 0;
        this.state.activeRingIndex = 0;
        this.renderer.resetPath();
      } else if (e.code === "KeyT") {
        this.state.theme = this.state.theme === "dark" ? "light" : "dark";
        document.body.classList.toggle("theme-light", this.state.theme === "light");
      } else if (e.key === "+" || e.key === "=" || e.code === "ArrowUp") {
        e.preventDefault();
        this.adjustN(10);
      } else if (e.key === "-" || e.code === "ArrowDown") {
        e.preventDefault();
        this.adjustN(-10);
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        this.state.currentT = (this.state.currentT + 0.05) % (2 * Math.PI);
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        this.state.currentT = (this.state.currentT - 0.05 + 2 * Math.PI) % (2 * Math.PI);
      }
    });

    // Start render loop
    requestAnimationFrame((t) => this.loop(t));
  }

  private adjustN(delta: number): void {
    const sliderN = document.getElementById("sliderN") as HTMLInputElement;
    const valN = document.getElementById("valN");
    const maxN = parseInt(sliderN?.max || "500", 10);
    this.state.activeN = Math.max(1, Math.min(maxN, this.state.activeN + delta));
    if (sliderN) sliderN.value = this.state.activeN.toString();
    if (valN) valN.textContent = this.state.activeN.toString();
    this.updateUrlParams();
  }

  private pickRandomMap(): void {
    if (this.indexEntries.length === 0) return;
    const randEntry = this.indexEntries[Math.floor(Math.random() * this.indexEntries.length)];
    this.selectMap(randEntry.id);
  }

  private handleRecordVideo(): void {
    const btn = document.getElementById("btnRecordWebM");
    if (this.activeRecorder && this.activeRecorder.isRecording()) {
      this.activeRecorder.stop();
      if (btn) btn.textContent = "⏺ Record WebM";
      return;
    }

    if (btn) btn.textContent = "⏹ Stop (0%)";
    const durationMs = (10000 / this.state.speed); // 1-2 periods

    this.activeRecorder = recordCanvasWebM(
      this.renderer.getCanvas(),
      durationMs,
      `${this.state.selectedMapId}_N${this.state.activeN}_epicycles.webm`,
      (progress) => {
        if (btn) btn.textContent = `⏹ Stop (${Math.round(progress * 100)}%)`;
      },
      () => {
        if (btn) btn.textContent = "⏺ Record WebM";
        this.activeRecorder = null;
      }
    );
  }

  private updateControlsUI(): void {
    const sliderN = document.getElementById("sliderN") as HTMLInputElement;
    const valN = document.getElementById("valN");
    if (sliderN && valN) {
      sliderN.value = this.state.activeN.toString();
      valN.textContent = this.state.activeN.toString();
    }
  }

  private loop(timestamp: number): void {
    if (!this.lastTime) this.lastTime = timestamp;
    const dt = Math.min(0.1, (timestamp - this.lastTime) / 1000);
    this.lastTime = timestamp;

    if (this.state.isPlaying && this.state.mapData) {
      // 1 full cycle (2*pi) in ~12 seconds at 1.0x speed
      const angularSpeed = (2 * Math.PI) / 12 * this.state.speed;
      this.state.currentT += angularSpeed * dt;

      if (this.state.currentT >= 2 * Math.PI) {
        this.state.currentT -= 2 * Math.PI;

        // Multi-ring sequential logic
        let activeRings = this.state.mapData.rings;
        if (this.state.detailLevel === "main") {
          activeRings = [this.state.mapData.rings[0]];
        } else if (this.state.detailLevel === "large") {
          activeRings = this.state.mapData.rings.filter(
            (r, i) => i === 0 || r.area_ratio >= 0.005 || i < 8
          );
        }

        if (this.state.activeRingIndex < activeRings.length - 1) {
          this.state.activeRingIndex++;
        } else {
          // Finished all rings for this cycle
          if (this.state.isAutoSweep) {
            const sliderN = document.getElementById("sliderN") as HTMLInputElement;
            const maxN = parseInt(sliderN?.max || "500", 10);
            if (this.state.activeN < maxN) {
              this.adjustN(10);
            } else {
              this.state.activeN = 5;
              this.adjustN(0);
            }
          }
        }
      }
    }

    // Update KaTeX & Live Stats
    if (this.state.mapData) {
      const ring = this.state.mapData.rings[this.state.activeRingIndex] || this.state.mapData.rings[0];
      const errorPct = ring ? this.computeErrorForN(ring.error_table, this.state.activeN) : 0;
      this.mathHud.updateStats(
        this.state.mapData.name,
        this.state.activeN,
        errorPct,
        this.state.activeRingIndex,
        this.state.mapData.rings.length
      );
    }

    // Render Canvas
    this.renderer.render(this.state);

    requestAnimationFrame((t) => this.loop(t));
  }

  private computeErrorForN(errorTable: Record<string, number>, N: number): number {
    if (!errorTable) return 0;
    const keys = Object.keys(errorTable).map(Number).sort((a, b) => a - b);
    if (keys.length === 0) return 0;

    if (errorTable[N.toString()] !== undefined) {
      return errorTable[N.toString()];
    }

    // Linear interpolation
    if (N <= keys[0]) return errorTable[keys[0].toString()];
    if (N >= keys[keys.length - 1]) return errorTable[keys[keys.length - 1].toString()];

    for (let i = 0; i < keys.length - 1; i++) {
      const k1 = keys[i];
      const k2 = keys[i + 1];
      if (N >= k1 && N <= k2) {
        const e1 = errorTable[k1.toString()];
        const e2 = errorTable[k2.toString()];
        const frac = (N - k1) / (k2 - k1);
        return e1 + frac * (e2 - e1);
      }
    }
    return 0;
  }
}

// Instantiate on DOMContentLoaded
window.addEventListener("DOMContentLoaded", () => {
  new WorldAtlasApp();
});
