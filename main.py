import logging
import os
import time
import cv2 # For displaying images if needed

# Import components from the qacam package
from qacam.camera_handler import CameraHandler
from qacam.calibration import Calibration
from qacam.pattern_utils import generate_pattern, ARUCO_DICTIONARIES
from qacam.tracking import Tracking
from qacam.qa_tests import QATests

# Configure logging for the main script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# Calibration file (ensure this exists or run calibration first)
CALIBRATION_FILE = "calibration_params.yaml" # Or "test_calibration.yaml" if using example data

# Pattern definition (MUST match the physical pattern being used)
# Example using a 5x7 board from a common dictionary
PATTERN_PARAMS = {
    'dictionary_name': "DICT_6X6_250", # Example dictionary
    'marker_size_m': 0.035,           # Physical size of one marker square side (meters)
    'rows': 5,                        # Number of rows in the pattern
    'cols': 7,                        # Number of columns in the pattern
    'marker_separation_m': 0.018,     # Physical separation between markers (meters)
    'type': 'board'                   # Type of pattern ('board' or 'marker')
}
# Example for a single marker:
# PATTERN_PARAMS = {
#     'dictionary_name': "DICT_6X6_250",
#     'marker_size_m': 0.1, # Physical size in meters
#     'type': 'marker'
# }

# Output directory for test results
RESULTS_BASE_DIR = "qa_results"

# --- Helper Functions ---
def ensure_calibration_file():
    """Checks for calibration file and prompts user if missing."""
    if not os.path.exists(CALIBRATION_FILE):
        logger.error(f"Calibration file '{CALIBRATION_FILE}' not found.")
        logger.warning("Please run a calibration sequence first or ensure the file exists.")
        # In a real application, you might trigger the calibration process here.
        # For this example, we'll exit if it's missing.
        return False
    logger.info(f"Using calibration file: {CALIBRATION_FILE}")
    return True

def generate_example_pattern_if_missing(filename="example_pattern_to_print.png"):
    """Generates an example pattern image based on PATTERN_PARAMS if it doesn't exist."""
    if not os.path.exists(filename):
        logger.warning(f"Example pattern file '{filename}' not found. Generating...")
        success = generate_pattern(
            output_filepath=filename,
            rows=PATTERN_PARAMS['rows'],
            cols=PATTERN_PARAMS['cols'],
            marker_size_pixels=100, # Adjust pixel size for printing needs
            marker_separation_pixels=int(100 * (PATTERN_PARAMS['marker_separation_m'] / PATTERN_PARAMS['marker_size_m'])), # Approx pixel separation
            dictionary_name=PATTERN_PARAMS['dictionary_name'],
            page_width_pixels=1000, # Example page size
            page_height_pixels=1400
        )
        if success:
            logger.info(f"Generated example pattern '{filename}'. Please print this pattern accurately.")
        else:
            logger.error("Failed to generate example pattern.")

# --- Main Application Logic ---
def main():
    logger.info("--- QA Cam Application Start ---")

    # 1. Check Prerequisites
    if not ensure_calibration_file():
        return # Exit if calibration is missing
    generate_example_pattern_if_missing() # Generate pattern for user if needed

    # 2. Initialize Components (using context manager for CameraHandler)
    try:
        with CameraHandler() as handler:
            logger.info("CameraHandler initialized successfully.")

            # Load calibration
            calibrator = Calibration(handler, params_file=CALIBRATION_FILE)
            if not calibrator.get_parameters():
                logger.error("Failed to load calibration parameters. Exiting.")
                return
            logger.info("Calibration parameters loaded.")

            # Initialize Tracking
            try:
                tracker = Tracking(handler, calibrator, pattern_params=PATTERN_PARAMS)
                logger.info("Tracking module initialized.")
            except ValueError as e:
                 logger.error(f"Failed to initialize Tracking: {e}")
                 logger.error("Please ensure PATTERN_PARAMS match the physical pattern and calibration.")
                 return

            # Initialize QA Tests
            qa_tester = QATests(tracker)
            logger.info("QATests module initialized.")

            # 3. Set Reference Pose
            logger.info("\n--- Setting Reference Pose ---")
            logger.info("Please position the printed pattern at the 'Home' (0,0,0) location.")
            logger.info("Ensure the camera has a clear, stable view of the entire pattern.")
            input("Press Enter when ready to capture the reference pose...")

            if qa_tester.tracker.set_reference_pose():
                logger.info("Reference pose captured successfully.")

                # 4. Run a QA Test (Example: Couch Test)
                logger.info("\n--- Running Couch Position Test ---")
                run_test = input("Do you want to run the Couch Position Test now? (y/n): ").lower()
                if run_test == 'y':
                    couch_results_dir = os.path.join(RESULTS_BASE_DIR, "couch_test")
                    success = qa_tester.run_couch_test(output_dir=couch_results_dir)
                    if success:
                        logger.info(f"Couch test completed. Results saved in '{couch_results_dir}'.")
                    else:
                        logger.error("Couch test failed or was interrupted.")
                else:
                    logger.info("Skipping Couch Position Test.")

                # Add options to run other tests here...
                # run_gantry = input("Run Gantry Angle Test? (y/n): ").lower() == 'y'
                # if run_gantry: ...
                # run_collimator = input("Run Collimator Angle Test? (y/n): ").lower() == 'y'
                # if run_collimator: ...

            else:
                logger.error("Failed to set reference pose. Cannot proceed with tests.")
                logger.warning("Ensure the pattern is clearly visible and matches the PATTERN_PARAMS.")

    except RuntimeError as e:
        logger.error(f"Camera or Device Runtime Error: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred in main: {e}") # Log full traceback

    logger.info("--- QA Cam Application End ---")

if __name__ == "__main__":
    main()
