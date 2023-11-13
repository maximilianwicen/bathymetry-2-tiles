import rasterio
from rasterio.enums import Resampling
import os
from rasterio import windows




def reduce_resolution(src, resolutions):
    original_transform = src.transform
    in_memory_images = {}

    for res in resolutions:
        # Determine the scale factor based on the larger dimension
        scale_factor = res / max(src.width, src.height)

        # Calculate the new width and height
        new_width = int(src.width * scale_factor)
        new_height = int(src.height * scale_factor)

        new_transform = rasterio.Affine(
            original_transform.a / scale_factor,
            original_transform.b,
            original_transform.c,
            original_transform.d,
            original_transform.e / scale_factor,
            original_transform.f
        )

        data = src.read(
            out_shape=(src.count, new_height, new_width),
            resampling=Resampling.bilinear
        )

        out_meta = src.meta.copy()
        out_meta.update({
            "height": new_height,
            "width": new_width,
            "transform": new_transform,
            "crs": src.crs
        })

        # Store the rescaled image in the dictionary
        in_memory_images[(new_width, new_height)] = {"data": data, "meta": out_meta}

    return in_memory_images


def calculate_resolutions(width, height):
    max_dimension = max(width, height)
    max_limit = 128000
    resolution = 800
    resolutions = []

    while resolution <= max_dimension and resolution <= max_limit:
        resolutions.append(resolution)
        resolution *= 2

    # Include the image's native resolution if it's not already in the list and is within the limit
    if max_dimension <= max_limit and max_dimension not in resolutions:
        resolutions.append(max_dimension)

    return resolutions

def save_spliced_images(in_memory_images, output_base_dir):
    tile_size = 160  # Fixed tile size
    zoom_level = 1  # Start from zoom level 1

    for res, image_dict in in_memory_images.items():
        src_data = image_dict['data']
        src_meta = image_dict['meta']
        width, height = src_meta['width'], src_meta['height']

        # Create a directory for each zoom level
        zoom_dir = os.path.join(output_base_dir, f'zoom_{zoom_level}')
        os.makedirs(zoom_dir, exist_ok=True)

        # Calculate the number of full tiles and remainders for each dimension
        num_x_tiles, remainder_x = divmod(width, tile_size)
        num_y_tiles, remainder_y = divmod(height, tile_size)

        for i in range(num_x_tiles + (1 if remainder_x else 0)):
            for j in range(num_y_tiles + (1 if remainder_y else 0)):
                x = i * tile_size
                y = j * tile_size

                # Determine the dimensions of the tile
                actual_tile_width = tile_size if x + tile_size <= width else remainder_x
                actual_tile_height = tile_size if y + tile_size <= height else remainder_y

                window = windows.Window(x, y, actual_tile_width, actual_tile_height)
                transform = rasterio.windows.transform(window, src_meta['transform'])

                tile_data = src_data[:, y:y+actual_tile_height, x:x+actual_tile_width]

                tile_meta = src_meta.copy()
                tile_meta.update({
                    "height": actual_tile_height,
                    "width": actual_tile_width,
                    "transform": transform
                })

                # Save the tile
                tile_filename = os.path.join(zoom_dir, f'tile_{i}_{j}.tif')
                with rasterio.open(tile_filename, 'w', **tile_meta) as dest:
                    dest.write(tile_data)

        zoom_level += 1  # Increment zoom level for next resolution

def create_directory_for_geotiff(input_geotiff):
    # Extract the filename from the full path and then remove its extension
    base_name = os.path.splitext(os.path.basename(input_geotiff))[0]

    # Get the directory of the script
    script_directory = os.path.dirname(os.path.realpath(__file__))

    # Move up one directory level to parent directory
    parent_directory = os.path.join(script_directory, '..')

    # Construct the path to the Bathymetry_data directory
    bathymetry_data_dir = os.path.join(parent_directory, 'Bathymetry_data')

    # Create the final output directory within Bathymetry_data
    output_base_dir = os.path.join(bathymetry_data_dir, base_name)

    # Create the top-level directory
    os.makedirs(output_base_dir, exist_ok=True)
    return output_base_dir


import rasterio
from rasterio.io import MemoryFile

def convert_float_to_int16(input_file):
    with rasterio.open(input_file) as src:
        # Read the original data
        data = src.read()

        # Convert the data to int16
        data_int16 = data.astype('int16')

        # Prepare metadata for the in-memory file
        out_meta = src.meta.copy()
        out_meta.update({
            'dtype': 'int16',
            'nodata': None  # Update or remove the nodata value as necessary
        })

        # Write the data to an in-memory file and return the dataset
        with MemoryFile() as memfile:
            with memfile.open(**out_meta) as mem_dst:
                mem_dst.write(data_int16)
                # Need to read back the data from the in-memory file
            return memfile.open()

# Usage example
input_geotiff = 'bath_data.tif'  # Replace with the path to your GeoTIFF
# Usage
src = convert_float_to_int16(input_geotiff)
resolutions = calculate_resolutions(src.width, src.height)
in_memory_images = reduce_resolution(src, resolutions)
output_base_dir = create_directory_for_geotiff(input_geotiff)
save_spliced_images(in_memory_images,output_base_dir)
