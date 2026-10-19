# Geographic Boundary Data for India

This directory contains the geospatial and raster representations of India's mainland boundary used to parameterize the orthogonal Fourier epicycles.

## Files

1. `india_outline.geojson`:
   - Official national boundary of India (exterior ring of the mainland), strictly aligned with the Survey of India (Government of India) statutory alignment, including the entirety of Jammu & Kashmir, Ladakh, and Arunachal Pradesh.
   - Vector format: GeoJSON `FeatureCollection` containing a single `Polygon`.
   - Coordinates: Longitude/Latitude (WGS 84, EPSG:4326).
   - Point count: 4,126 vertices (preserves topology, coastal estuaries, and northern frontiers).

2. `india_mask.png`:
   - High-contrast black-and-white raster silhouette (2000x2400 pixels) of the official boundary on a solid black background.
   - Used for the computer-vision (`cv2.findContours`) input pathway in `src/outline.py`.

## Data Source & Provenance

- **Source Entity**: Survey of India, Department of Science & Technology, Government of India.
- **Digital Compilation**: Maintained and curated by [DataMeet Community Maps](https://github.com/datameet/maps), specifically `Country/india-composite.geojson`.
- **Licence**: Creative Commons Attribution 2.5 India / Open Data Commons Open Database License (ODbL).
- **Processing**: Extracted via Shapely `simplify(tolerance=0.01, preserve_topology=True)` to remove topological noise while retaining sub-kilometer coastal fidelity.
