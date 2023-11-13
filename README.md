# bathymetry-2-tiles
Small project to create tiles from bathymetry data that is not uint8. For uint8 data use GDAL2Tiles?

requirements:
pip install rasterio

Input is a geotif.
Converts this geotif to signed int16 to reduce space, if your resolution is in centimeters you might want to skip this step.
Then outputs tiles in 160x160 pixel resolutions, edges are output as remainder. Transform affine is kept for each tile and recalculated.
These zoom levels are created; doubling from 800 pixels until it is not possible to double anymore. My files are for example 13000x13000 then these zoom levels would be created:
800x, 1600x, 3200x, 6400x, 12800x, 13000x.

