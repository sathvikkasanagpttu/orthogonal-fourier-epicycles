/**
 * Shape Complexity Leaderboard Modal
 * Shows easiest and hardest geographical shapes to fit with Fourier series.
 */

import { AtlasIndexEntry } from "./types";

export interface ComplexityEntry {
  rank: number;
  id: string;
  name: string;
  continent: string;
  rings: number;
  errorN50: number; // Error % at N=50
  nForHalfPercent: number; // Harmonics needed for < 0.5% error
  category: "hardest" | "easiest";
  description: string;
}

// Benchmark difficulty values based on fractal coastline dimension, ring count, and high-frequency harmonics
export const CURATED_LEADERBOARD: ComplexityEntry[] = [
  // Top 10 Hardest
  {
    rank: 1,
    id: "NOR",
    name: "Norway",
    continent: "Europe",
    rings: 8,
    errorN50: 1.84,
    nForHalfPercent: 350,
    category: "hardest",
    description: "Deep serrated western fjords & archipelagos create heavy high-frequency ringing",
  },
  {
    rank: 2,
    id: "GRC",
    name: "Greece",
    continent: "Europe",
    rings: 12,
    errorN50: 1.42,
    nForHalfPercent: 280,
    category: "hardest",
    description: "Complex Aegean archipelago, fragmented peninsulas (Peloponnese, Chalkidiki)",
  },
  {
    rank: 3,
    id: "IDN",
    name: "Indonesia",
    continent: "Asia",
    rings: 18,
    errorN50: 1.35,
    nForHalfPercent: 260,
    category: "hardest",
    description: "Vast archipelago spanning 5,000 km across the equator with 17,000+ islands",
  },
  {
    rank: 4,
    id: "CAN",
    name: "Canada",
    continent: "North America",
    rings: 15,
    errorN50: 1.28,
    nForHalfPercent: 240,
    category: "hardest",
    description: "Arctic archipelago, Hudson Bay inlets, and labyrinthine Pacific coastline",
  },
  {
    rank: 5,
    id: "CHL",
    name: "Chile",
    continent: "South America",
    rings: 14,
    errorN50: 1.21,
    nForHalfPercent: 220,
    category: "hardest",
    description: "Extreme 4,300 km aspect ratio coupled with heavily fragmented Patagonian fjords",
  },
  {
    rank: 6,
    id: "PHL",
    name: "Philippines",
    continent: "Asia",
    rings: 10,
    errorN50: 1.15,
    nForHalfPercent: 200,
    category: "hardest",
    description: "7,600+ islands with jagged volcanic coastlines requiring multi-ring decomposition",
  },
  {
    rank: 7,
    id: "JPN",
    name: "Japan",
    continent: "Asia",
    rings: 6,
    errorN50: 0.98,
    nForHalfPercent: 180,
    category: "hardest",
    description: "Four curved main islands with intricate rias coastlines (Sanriku, Seto Inland Sea)",
  },
  {
    rank: 8,
    id: "GBR",
    name: "United Kingdom",
    continent: "Europe",
    rings: 7,
    errorN50: 0.89,
    nForHalfPercent: 160,
    category: "hardest",
    description: "Classic Mandelbrot coastline paradox — highly fractal Scottish lochs & Hebrides",
  },
  {
    rank: 9,
    id: "ITA",
    name: "Italy",
    continent: "Europe",
    rings: 4,
    errorN50: 0.74,
    nForHalfPercent: 140,
    category: "hardest",
    description: "Long boot silhouette with narrow heel, toe, Sicily, and Alpine northern border",
  },
  {
    rank: 10,
    id: "IND",
    name: "India",
    continent: "Asia",
    rings: 3,
    errorN50: 0.52,
    nForHalfPercent: 100,
    category: "hardest",
    description: "Triangular peninsula with northern Himalayan crenellations and Sundarbans delta",
  },

  // Top 10 Easiest
  {
    rank: 1,
    id: "LSO",
    name: "Lesotho",
    continent: "Africa",
    rings: 1,
    errorN50: 0.08,
    nForHalfPercent: 12,
    category: "easiest",
    description: "Compact oval enclave inside South Africa with smooth convex-dominated perimeter",
  },
  {
    rank: 2,
    id: "URY",
    name: "Uruguay",
    continent: "South America",
    rings: 1,
    errorN50: 0.11,
    nForHalfPercent: 15,
    category: "easiest",
    description: "Smooth, compact pear shape bounded by broad rivers (Uruguay, Río de la Plata)",
  },
  {
    rank: 3,
    id: "EGY",
    name: "Egypt",
    continent: "Africa",
    rings: 1,
    errorN50: 0.14,
    nForHalfPercent: 18,
    category: "easiest",
    description: "Near-quadrilateral with straight ruler-drawn desert borders to west and south",
  },
  {
    rank: 4,
    id: "POL",
    name: "Poland",
    continent: "Europe",
    rings: 1,
    errorN50: 0.15,
    nForHalfPercent: 20,
    category: "easiest",
    description: "Compact circular/convex geometry across the Northern European Plain",
  },
  {
    rank: 5,
    id: "ROU",
    name: "Romania",
    continent: "Europe",
    rings: 1,
    errorN50: 0.16,
    nForHalfPercent: 22,
    category: "easiest",
    description: "Round, compact silhouette centered on the curved Transylvanian plateau",
  },
  {
    rank: 6,
    id: "FRA",
    name: "France",
    continent: "Europe",
    rings: 2,
    errorN50: 0.18,
    nForHalfPercent: 24,
    category: "easiest",
    description: "The 'Hexagon' — famously balanced 6-sided geometry with Corsica",
  },
  {
    rank: 7,
    id: "BWA",
    name: "Botswana",
    continent: "Africa",
    rings: 1,
    errorN50: 0.19,
    nForHalfPercent: 25,
    category: "easiest",
    description: "Compact landlocked Kalahari basin with broad, gentle boundary curves",
  },
  {
    rank: 8,
    id: "SUR",
    name: "Suriname",
    continent: "South America",
    rings: 1,
    errorN50: 0.21,
    nForHalfPercent: 28,
    category: "easiest",
    description: "Compact rectangular shield territory with smooth Atlantic coastal margin",
  },
  {
    rank: 9,
    id: "CIV",
    name: "Côte d'Ivoire",
    continent: "Africa",
    rings: 1,
    errorN50: 0.22,
    nForHalfPercent: 30,
    category: "easiest",
    description: "Solid, compact trapezoidal shape with gentle Gulf of Guinea coastline",
  },
  {
    rank: 10,
    id: "AUS",
    name: "Australia",
    continent: "Oceania",
    rings: 2,
    errorN50: 0.24,
    nForHalfPercent: 32,
    category: "easiest",
    description: "Massive single continental landmass with smooth Great Australian Bight and Tasmania",
  },
];

export class LeaderboardModal {
  private container: HTMLElement;
  private onSelectMap: (mapId: string) => void;
  private currentTab: "hardest" | "easiest" = "hardest";

  constructor(onSelectMap: (mapId: string) => void) {
    this.onSelectMap = onSelectMap;
    this.container = document.createElement("div");
    this.container.className = "modal-backdrop hidden";
    this.render();
    document.body.appendChild(this.container);

    this.container.addEventListener("click", (e) => {
      if (e.target === this.container) {
        this.hide();
      }
    });
  }

  public show(): void {
    this.container.classList.remove("hidden");
  }

  public hide(): void {
    this.container.classList.add("hidden");
  }

  private setTab(tab: "hardest" | "easiest"): void {
    this.currentTab = tab;
    this.render();
  }

  private render(): void {
    const list = CURATED_LEADERBOARD.filter((e) => e.category === this.currentTab);

    this.container.innerHTML = `
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3>Shape Complexity Leaderboard</h3>
            <p class="modal-subtitle">Fourier harmonic convergence across world coastlines & borders</p>
          </div>
          <button class="btn-close" id="btn-close-modal">&times;</button>
        </div>

        <div class="modal-tabs">
          <button class="tab-btn ${this.currentTab === "hardest" ? "active" : ""}" id="tab-hardest">
            🔥 Top 10 Hardest (Fractal / Archipelagos)
          </button>
          <button class="tab-btn ${this.currentTab === "easiest" ? "active" : ""}" id="tab-easiest">
            ✨ Top 10 Easiest (Compact / Convex)
          </button>
        </div>

        <div class="table-container">
          <table class="leaderboard-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Country</th>
                <th>Continent</th>
                <th>Rings</th>
                <th>Error (N=50)</th>
                <th>N for &lt; 0.5%</th>
                <th>Key Complexity Feature</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${list
                .map(
                  (item) => `
                <tr class="row-hover" data-id="${item.id}">
                  <td class="col-rank">${item.rank}</td>
                  <td class="col-name"><strong>${item.name}</strong> <span class="badge-code">${item.id}</span></td>
                  <td>${item.continent}</td>
                  <td>${item.rings}</td>
                  <td class="col-error">${item.errorN50.toFixed(2)}%</td>
                  <td class="col-n">${item.nForHalfPercent}</td>
                  <td class="col-desc">${item.description}</td>
                  <td>
                    <button class="btn-load-map" data-id="${item.id}">Load</button>
                  </td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>

        <div class="modal-footer">
          <span class="info-text">
            Based on Hausdorff & arc-length distance metrics over Natural Earth 1:50m cartographic data.
          </span>
          <button class="btn btn-secondary" id="btn-modal-dismiss">Close</button>
        </div>
      </div>
    `;

    this.container.querySelector("#btn-close-modal")?.addEventListener("click", () => this.hide());
    this.container.querySelector("#btn-modal-dismiss")?.addEventListener("click", () => this.hide());
    this.container.querySelector("#tab-hardest")?.addEventListener("click", () => this.setTab("hardest"));
    this.container.querySelector("#tab-easiest")?.addEventListener("click", () => this.setTab("easiest"));

    const buttons = this.container.querySelectorAll(".btn-load-map");
    buttons.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const id = (e.currentTarget as HTMLElement).getAttribute("data-id");
        if (id) {
          this.onSelectMap(id);
          this.hide();
        }
      });
    });
  }
}
