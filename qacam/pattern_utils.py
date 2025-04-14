import cv2
import cv2.aruco as aruco
import numpy as np
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ArUco Dictionary Mapping ---
# Provides a mapping from string names to cv2.aruco dictionary constants
ARUCO_DICTIONARIES = {
    "DICT_4X4_50": aruco.DICT_4X4_50,
    "DICT_4X4_100": aruco.DICT_4X4_100,
    "DICT_4X4_250": aruco.DICT_4X4_250,
    "DICT_4X4_1000": aruco.DICT_4X4_1000,
    "DICT_5X5_50": aruco.DICT_5X5_50,
    "DICT_5X5_100": aruco.DICT_5X5_100,
    "DICT_5X5_250": aruco.DICT_5X5_250,
    "DICT_5X5_1000": aruco.DICT_5X5_1000,
    "DICT_6X6_50": aruco.DICT_6X6_50,
    "DICT_6X6_100": aruco.DICT_6X6_100,
    "DICT_6X6_250": aruco.DICT_6X6_250,
    "DICT_6X6_1000": aruco.DICT_6X6_1000,
    "DICT_7X7_50": aruco.DICT_7X7_50,
    "DICT_7X7_100": aruco.DICT_7X7_100,
    "DICT_7X7_250": aruco.DICT_7X7_250,
    "DICT_7X7_1000": aruco.DICT_7X7_1000,
    "DICT_ARUCO_ORIGINAL": aruco.DICT_ARUCO_ORIGINAL,
    # Add AprilTag dictionaries if needed (might require contrib opencv)
    # "DICT_APRILTAG_16h5": aruco.DICT_APRILTAG_16h5,
    # ... other AprilTag dicts
}

def generate_pattern(
    output_filepath="aruco_pattern.png",
    rows=5,
    cols=7,
    marker_size_pixels=100,
    marker_separation_pixels=30,
    dictionary_name="DICT_6X6_250",
    start_id=0,
    page_width_pixels=None, # Optional: for centering on a page
    page_height_pixels=None, # Optional: for centering on a page
    border_bits=1
):
    """
    Generates a printable ArUco board pattern image.

    Creates a grid of ArUco markers and saves it as an image file.

    Args:
        output_filepath (str): Path to save the generated PNG image.
        rows (int): Number of rows in the marker grid.
        cols (int): Number of columns in the marker grid.
        marker_size_pixels (int): Size of each marker in pixels.
        marker_separation_pixels (int): Separation distance between markers in pixels.
        dictionary_name (str): Name of the ArUco dictionary to use (e.g., "DICT_6X6_250").
                               Must be a key in ARUCO_DICTIONARIES.
        start_id (int): The starting ID for the ArUco markers. Markers will be numbered
                        sequentially from this ID.
        page_width_pixels (int, optional): Total width of the output image (e.g., for A4 paper size in pixels).
                                           If provided, the pattern will be centered.
        page_height_pixels (int, optional): Total height of the output image. If provided, pattern centered.
        border_bits (int): Width of the marker border.

    Returns:
        bool: True if the pattern was generated successfully, False otherwise.
    """
    logger.info(f"Generating ArUco pattern: {rows}x{cols}, dict: {dictionary_name}, marker size: {marker_size_pixels}px")

    if dictionary_name not in ARUCO_DICTIONARIES:
        logger.error(f"Invalid dictionary name: {dictionary_name}. Available: {list(ARUCO_DICTIONARIES.keys())}")
        return False

    try:
        # Get the dictionary object
        aruco_dict = aruco.getPredefinedDictionary(ARUCO_DICTIONARIES[dictionary_name])

        # Create the grid board object
        # Note: markerLength and markerSeparation are relative for some functions,
        # but for drawPlanarBoard, we control pixel size directly later.
        # We use the pixel values here conceptually for calculating total size.
        # Try passing firstMarker positionally after the dictionary
        # Constructor without the start_id/ids argument for default numbering
        board = aruco.GridBoard(
            (cols, rows), # size
            marker_size_pixels, # markerLength
            marker_separation_pixels, # markerSeparation
            aruco_dict) # dictionary

        # Calculate the total size of the board in pixels
        total_width = cols * marker_size_pixels + (cols - 1) * marker_separation_pixels
        total_height = rows * marker_size_pixels + (rows - 1) * marker_separation_pixels

        # Determine the output image size
        out_width = page_width_pixels if page_width_pixels is not None and page_width_pixels >= total_width else total_width
        out_height = page_height_pixels if page_height_pixels is not None and page_height_pixels >= total_height else total_height

        # Calculate margins for centering if page size is provided
        margin_x = (out_width - total_width) // 2
        margin_y = (out_height - total_height) // 2

        # Draw the board onto an image
        # We need to provide the output image size and the margins
        # The third parameter to drawPlanarBoard is the output image size (height, width)
        # The fourth parameter is the margin size (top/left)
        # The fifth parameter is the border size around markers
        img = board.generateImage(
            outSize=(out_width, out_height), # Size of the final image
            marginSize=max(margin_x, margin_y), # Use max margin for simplicity, or handle x/y separately if needed
            borderBits=border_bits
            )


        # Ensure the output directory exists
        output_dir = os.path.dirname(output_filepath)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created output directory: {output_dir}")

        # Save the image
        cv2.imwrite(output_filepath, img)
        logger.info(f"Successfully generated and saved ArUco pattern to: {output_filepath}")
        return True

    except Exception as e:
        logger.exception(f"Failed to generate ArUco pattern: {e}") # Log full traceback
        return False

# Example Usage (Optional - for testing)
if __name__ == '__main__':
    logger.info("Running PatternUtils example...")

    # Define parameters for the pattern
    output_file = "generated_pattern_example.png"
    rows = 4
    cols = 6
    marker_px = 80
    separation_px = 20
    dictionary = "DICT_5X5_100" # Choose a smaller dictionary for example
    start_marker_id = 10

    # A4 paper size at 300 DPI (approx pixels)
    a4_width_px = 2480
    a4_height_px = 3508

    success = generate_pattern(
        output_filepath=output_file,
        rows=rows,
        cols=cols,
        marker_size_pixels=marker_px,
        marker_separation_pixels=separation_px,
        dictionary_name=dictionary,
        start_id=start_marker_id,
        page_width_pixels=a4_width_px // 2, # Example: Use half A4 width
        page_height_pixels=a4_height_px // 2 # Example: Use half A4 height
    )

    if success:
        logger.info(f"Pattern generation example successful. Check '{output_file}'.")
        # Optional: Display the generated pattern
        # try:
        #     img = cv2.imread(output_file)
        #     if img is not None:
        #         cv2.imshow("Generated Pattern", img)
        #         logger.info("Displaying pattern. Press any key to close.")
        #         cv2.waitKey(0)
        #         cv2.destroyAllWindows()
        #     else:
        #         logger.error("Could not read back the generated image file.")
        # except Exception as display_err:
        #     logger.error(f"Error displaying image: {display_err}")
    else:
        logger.error("Pattern generation example failed.")

    logger.info("PatternUtils example finished.")