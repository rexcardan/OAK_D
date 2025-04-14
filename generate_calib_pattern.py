# generate_calib_pattern.py
import logging
from qacam.pattern_utils import generate_pattern

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Customize Your Pattern Here ---
OUTPUT_FILE = "my_calibration_pattern.png"
PATTERN_ROWS = 5
PATTERN_COLS = 7
# Updated sizes to better fill the page within margins:
MARKER_SIZE_PX = 340  # Size of marker in pixels for the image
MARKER_SEP_PX = 90   # Separation in pixels for the image
DICTIONARY = "DICT_6X6_250" # ArUco dictionary

# --- Page Layout (Landscape US Letter @ 300 DPI) ---
PAGE_WIDTH_IN = 11
PAGE_HEIGHT_IN = 8.5
DPI = 300

PAGE_WIDTH_PX = int(PAGE_WIDTH_IN * DPI)
PAGE_HEIGHT_PX = int(PAGE_HEIGHT_IN * DPI)
# --- End Customization ---

logger.info(f"Generating calibration pattern: {OUTPUT_FILE}")
logger.info(f"Targeting page size: {PAGE_WIDTH_PX}x{PAGE_HEIGHT_PX} pixels ({PAGE_WIDTH_IN}x{PAGE_HEIGHT_IN} inches @ {DPI} DPI)")
logger.info(f"Using marker size={MARKER_SIZE_PX}px, separation={MARKER_SEP_PX}px to maximize page usage.")

success = generate_pattern(
    output_filepath=OUTPUT_FILE,
    rows=PATTERN_ROWS,
    cols=PATTERN_COLS,
    marker_size_pixels=MARKER_SIZE_PX,
    marker_separation_pixels=MARKER_SEP_PX,
    dictionary_name=DICTIONARY,
    page_width_pixels=PAGE_WIDTH_PX, # Pass calculated page width
    page_height_pixels=PAGE_HEIGHT_PX # Pass calculated page height
)

if success:
    logger.info("Pattern generated successfully.")
    logger.info(f"IMPORTANT: Print '{OUTPUT_FILE}' ensuring accurate scaling (100% / actual size).")
    logger.info("The pattern should be centered on an 11 x 8.5 inch landscape page and fill most of it.")
    logger.info("You will need to measure the *actual* printed marker size and separation in meters for the calibration process.")
else:
    logger.error("Failed to generate pattern.")