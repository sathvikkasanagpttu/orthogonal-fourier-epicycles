# World Atlas Map Data: Sources, Projections & Licensing

This directory stores raw and processed geospatial datasets for **Orthogonal Fourier Epicycles: World Atlas Edition**.

## 1. Data Sources

- **Primary Source**: [Natural Earth](https://www.naturalearthdata.com/)
  - Dataset: Admin 0 – Countries (1:50m cultural vectors)
  - Dataset: Physical Land (1:50m physical vectors for World / Continents)
  - Raw files: `data/raw/ne_50m_admin_0_countries.geojson` and `data/raw/ne_50m_land.geojson`
- **Licence**: Public Domain (Creative Commons Zero / CC0). Natural Earth vector and raster data were created by the North American Cartographic Information Society (NACIS) and contributed to the public domain without restriction.

## 2. Boundary Views & Disputed Borders

Natural Earth documents international boundaries according to **de facto** international status lines of control.

- **Configurable Boundary Views**:
  - `de_facto` (Default): Natural Earth standard global edition.
  - `sovereign_in` (India Statutory View): Retains the official sovereign boundary of India as published by the Survey of India (Government of India), including Jammu & Kashmir, Ladakh, and Arunachal Pradesh.
- Users and developers can toggle between boundary viewpoints via the `--boundary-view` flag in `scripts/build_atlas.py` or through the interactive selector.

## 3. Cartographic Projections

To eliminate high-latitude Mercator/geographic distortion:
- **Countries**: Local Equirectangular projection scaled by $\cos(\phi_0)$, where $\phi_0$ is the mean latitude, or Lambert Azimuthal Equal-Area (LAEA) centered on the nation's centroid.
- **World & Continents**: Equal Earth or Robinson projection (WGS 84 ellipsoid), preserving realistic continental proportions.
- **Antimeridian Unwrapping**: Territories spanning the $180^\circ$ meridian (e.g., Russia/Chukotka, Fiji, USA/Aleutian Islands) are continuous without horizontal seam slicing.
