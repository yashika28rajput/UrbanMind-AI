# CHETNA-Road Delhi: MODELLED 2021 ROAD-TRAFFIC CO2

These outputs contain **modelled 2021 road-traffic CO2 estimates**, not measured emissions and not current emissions. They are not a total all-sector GHG inventory.

## Files

- `data/processed/carbon/delhi_ward_co2_modelled_2021_annual.csv`: one row per ward, fractional-area primary estimate plus centroid-assignment sensitivity columns.
- `data/processed/carbon/delhi_ward_co2_modelled_2021_daily.csv`: one row per ward per day (365 × 272 = 99,280 rows).

## Inputs and interpretation

- Source dataset: CHETNA-Road Delhi 2021 road-traffic emissions NetCDF, distributed through the CHETNA-Road dataset record linked below; data variable `co2` with units `tonnes`, indexed by time, latitude, longitude. Daily 2021 values are treated as tonnes per grid cell per day.
- Ward geometry: `data/processed/ml/environmental/delhi_ward_environmental_risk.geojson`; 272 numbered polygons.
- The NetCDF provides `lat` and `lon` but no explicit CRS attribute. Coordinates were interpreted as geographic longitude/latitude (OGC:CRS84), consistent with their coordinate names, Delhi coordinate ranges, and the GeoJSON CRS. Both datasets were reprojected to EPSG:32643 for area calculations.

## Allocation method

For each finite NetCDF cell, a footprint was constructed around its coordinate center using half the regular 0.005-degree spacing. Cell edges were densified before projection to EPSG:32643. Each daily cell total was allocated to wards by the fraction of the cell footprint intersecting each ward. The NetCDF's NaN fill cells were excluded; they were never treated as zero or imputed. The cell fraction outside the union of wards remains unallocated.

Ward polygons have a small aggregate overlap (0.277428 km² after projection). To prevent duplicate allocation there, each cell's intersection area with the union was split among intersecting wards in proportion to their individual intersection areas. This preserves conservation while making the shared sliver allocation explicit. The method assumes emissions are uniformly distributed inside each cell; actual emissions may be concentrated on road segments.

Coverage percentage is allocated valid cell-footprint area divided by ward polygon area. Flags use an analyst-selected 90% threshold: `ADEQUATE_GE90%` >= 90%, `PARTIAL_LT90%` > 0.01% and < 90%, and `NO_COVERAGE` <= 0.01%. The threshold is a screening rule, not a standard. Partial wards have missing-area limitations and should not be treated as equally complete.

## Coverage and conservation

- Wards: 272; coverage flags: {'ADEQUATE_GE90%': 257, 'PARTIAL_LT90%': 15, 'NO_COVERAGE': 0}.
- Partial wards below 90% valid-area coverage:
- Ward 178 (SANGAM VIHAR): 66.68%
- Ward 187 (SANGAM VIHAR CENTRAL): 67.40%
- Ward 177 (SAID UL AJAIB): 79.94%
- Ward 7 (BURARI): 81.44%
- Ward 176 (BHATI): 85.65%
- Ward 4 (BAKHTAWAR PUR): 85.93%
- Ward 143 (KAPASHERA): 86.24%
- Ward 186 (SANGAM VIHAR WEST): 87.28%
- Ward 133 (CHHAWLA): 88.42%
- Ward 28 (BAWANA): 88.48%
- Ward 8 (JHARODA): 88.97%
- Ward 140 (KHERA): 89.33%
- Ward 29 (KARALA): 89.55%
- Ward 198 (PUL PEHLAD): 89.66%
- Ward 175 (AYA NAGAR): 89.90%
- Valid grid cells: 5,348; cells crossing multiple ward polygons: 2,136.
- Total finite grid values across 2021: 2,192,252.388498 tonnes.
- Fractionally allocated inside ward union: 2,023,024.426394 tonnes (92.280635%); outside ward union remains unallocated.
- Conservation check: maximum daily absolute difference between sum of ward allocations and cell totals multiplied by union-intersection fractions = 2.54658516496e-11 tonnes; tolerance = 0.000202302442639 tonnes. Check passed.
- Valid grid footprint area outside the ward union: 159.860742 km². Ward polygon area not covered by finite grid cells: 70.219359 km².

## Centroid-assignment sensitivity

The alternative assigns each valid cell's entire annual total to the ward covering its cell centroid; centers outside all wards are left unallocated. This is a sensitivity comparison, not the primary estimate.

- Centroid-assigned total: 2,028,007.955948 tonnes (92.507960% of valid grid total), compared with 2,023,024.426394 tonnes (92.280635%) for fractional allocation.
- Across wards: 143 centroid estimates increase, 129 decrease, and 0 are unchanged relative to fractional allocation.
- Median absolute ward change: 9.503%; 90th percentile absolute change: 34.449%; largest absolute change: 79.318% for ward 267 (NEHRU VIHAR).
- Centroid cells outside wards (unallocated): 584 of 5348.

## Source

CHETNA-Road dataset DOI: https://doi.org/10.6084/m9.figshare.28330067.v2
Paper/methods: https://doi.org/10.1038/s41597-025-06287-9
