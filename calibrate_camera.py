import cv2
import cv2.aruco as aruco
import numpy as np
import logging
import os
import time
from qacam.camera_handler import CameraHandler
from qacam.calibration import Calibration
from qacam.pattern_utils import ARUCO_DICTIONARIES

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pattern details (Should match the generated/printed pattern)
ARUCO_DICT_NAME = "DICT_6X6_250" # Match generate_calib_pattern.py
ROWS = 5  # Number of rows in the pattern
COLS = 7  # Number of columns in the pattern

# Calibration settings
IMAGES_NEEDED = 20 # Number of good views required for calibration
CALIBRATION_FILENAME = "calibration_params.yaml" # Default output file

# --- Helper Functions ---
def get_measured_dimensions():
    """Prompts user for the physical dimensions of the printed pattern."""
    while True:
        try:
            size_str = input(f"Enter the measured side length of one square marker (in meters): ")
            marker_size_m = float(size_str)
            if marker_size_m > 0:
                break
            else:
                print("Marker size must be positive.")
        except ValueError:
            print("Invalid input. Please enter a number (e.g., 0.035).")

    while True:
        try:
            sep_str = input(f"Enter the measured separation distance between markers (in meters): ")
            marker_separation_m = float(sep_str)
            if marker_separation_m > 0:
                break
            else:
                print("Marker separation must be positive.")
        except ValueError:
            print("Invalid input. Please enter a number (e.g., 0.018).")

    return marker_size_m, marker_separation_m

def create_aruco_board_object_points(rows, cols, marker_size_m, marker_separation_m):
    """Creates the 3D coordinates of the ArUco board corners."""
    objp = np.zeros((rows * cols, 3), np.float32)
    idx = 0
    for r in range(rows):
        for c in range(cols):
            # Calculate top-left corner coordinate for this marker
            # Origin is typically at the top-left corner of the top-left marker's border
            # Adjust if your coordinate system origin differs
            base_x = c * (marker_size_m + marker_separation_m)
            base_y = r * (marker_size_m + marker_separation_m)

            # Define corners relative to the marker's top-left
            # Order: top-left, top-right, bottom-right, bottom-left
            # This order must match the order returned by detectMarkers
            objp[idx*4 + 0] = [base_x, base_y, 0]
            objp[idx*4 + 1] = [base_x + marker_size_m, base_y, 0]
            objp[idx*4 + 2] = [base_x + marker_size_m, base_y + marker_size_m, 0]
            objp[idx*4 + 3] = [base_x, base_y + marker_size_m, 0]
            idx += 1 # This logic assumes objp should store individual corner points, not marker centers

    # Correction: cv2.calibrateCamera expects one point per corner,
    # but the ArUco board object points should represent the corners
    # of the *entire board* or individual markers if using estimatePoseSingleMarkers.
    # For calibrateCamera with ArUco, we usually provide the object points
    # corresponding to the *detected* corners for each view.

    # Let's redefine objp for a single marker's corners relative to its center (or top-left)
    # We will create the full object points list dynamically based on detected IDs later.

    # Simpler approach: Use aruco.GridBoard to get the object points directly.
    # This requires the dictionary object first.
    try:
        aruco_dict = aruco.getPredefinedDictionary(ARUCO_DICTIONARIES[ARUCO_DICT_NAME])
        # Note: Using the *measured* physical sizes here is crucial!
        board = aruco.GridBoard(
            (cols, rows),
            marker_size_m,
            marker_separation_m,
            aruco_dict)
        # board.getObjPoints() returns points suitable for estimatePoseBoard,
        # but calibrateCamera needs points matched to detected image corners per frame.
        # We'll construct the obj_points_all list frame-by-frame.
        logger.info("ArUco board definition created for object points.")
        # Return the board object itself, we'll use it later
        return board
    except Exception as e:
        logger.error(f"Failed to create ArUco board object: {e}")
        return None


# --- Main Calibration Logic ---
def main():
    logger.info("--- Camera Calibration Script ---")

    # 1. Get Measured Dimensions
    marker_size_m, marker_separation_m = get_measured_dimensions()
    logger.info(f"Using Marker Size: {marker_size_m}m, Separation: {marker_separation_m}m")

    # 2. Setup ArUco and Board Object Points
    try:
        aruco_dict = aruco.getPredefinedDictionary(ARUCO_DICTIONARIES[ARUCO_DICT_NAME])
        aruco_params = aruco.DetectorParameters()
        # aruco_detector = aruco.ArucoDetector(aruco_dict, aruco_params) # OpenCV 4.7+
        board = aruco.GridBoard(
                    (COLS, ROWS),
                    marker_size_m,
                    marker_separation_m,
                    aruco_dict)
        # Get the canonical object points from the board definition
        # These are the 3D points corresponding to the corners of all markers in the board's coordinate system
        canonical_obj_points = board.getObjPoints()
        if canonical_obj_points is None or len(canonical_obj_points) == 0:
             logger.error("Failed to get object points from board definition.")
             return

    except Exception as e:
        logger.error(f"Failed to setup ArUco dictionary or board: {e}")
        return

    # 3. Initialize Camera and Calibration Helper
    try:
        with CameraHandler() as handler:
            # Pass handler even though we might not use its calibrate method directly
            calibrator = Calibration(handler, params_file=CALIBRATION_FILENAME)
            logger.info("CameraHandler initialized.")

            # Lists to store points from all images
            all_corners = [] # 2D points in image plane
            all_ids = [] # Marker IDs corresponding to corners
            obj_points_all = [] # 3D points corresponding to detected corners per image
            img_size = None # To store image dimensions

            logger.info("\n--- Starting Image Capture ---")
            logger.info(f"Need {IMAGES_NEEDED} valid views of the pattern.")
            logger.info("Position the pattern in view. Press 'c' to capture, 'q' to quit.")
            logger.info("Ensure pattern is detected (corners drawn) before capturing.")
            logger.info("Move the pattern to different positions/angles/distances for each capture.")

            captured_count = 0
            while captured_count < IMAGES_NEEDED:
                frame, _ = handler.get_rgbd_frames()
                if frame is None:
                    time.sleep(0.1)
                    continue

                if img_size is None:
                    img_size = (frame.shape[1], frame.shape[0]) # (width, height)

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                corners, ids, rejected = aruco.detectMarkers(gray, aruco_dict, parameters=aruco_params)
                # corners, ids, rejected = aruco_detector.detectMarkers(gray) # OpenCV 4.7+

                display_frame = frame.copy()
                if ids is not None:
                    aruco.drawDetectedMarkers(display_frame, corners, ids)

                # Display instructions
                cv2.putText(display_frame, f"Captures: {captured_count}/{IMAGES_NEEDED}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(display_frame, "Press 'c' to capture, 'q' to quit.", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                if ids is None:
                     cv2.putText(display_frame, "Pattern not detected!", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)


                cv2.imshow("Calibration Capture", display_frame)
                key = cv2.waitKey(1) & 0xFF

                if key == ord('c'):
                    if ids is not None and len(ids) > 3: # Need a reasonable number of markers
                        logger.info(f"Attempting capture {captured_count + 1}...")
                        # Match detected corners (img_points) with board object points
                        # objPoints_view, imgPoints_view = board.matchImagePoints(corners, ids) # Preferred method

                        # Manual matching if matchImagePoints not available/working:
                        # We need to get the object points corresponding *only* to the detected IDs
                        objPoints_view = []
                        imgPoints_view = []
                        for i, marker_id in enumerate(ids):
                            if marker_id[0] < len(canonical_obj_points): # Check if ID is within board definition
                                # Find the corresponding 4 object points for this marker ID
                                # The canonical_obj_points are ordered by ID (0, 1, 2...)
                                # Each marker has 4 corners.
                                marker_obj_pts = canonical_obj_points[marker_id[0]]
                                objPoints_view.extend(marker_obj_pts)
                                imgPoints_view.extend(corners[i][0]) # corners[i] is shape (1, 4, 2), need (4, 2)
                            else:
                                logger.warning(f"Detected marker ID {marker_id[0]} is outside the defined board range.")


                        if len(objPoints_view) > 0:
                             obj_points_all.append(np.array(objPoints_view, dtype=np.float32))
                             all_corners.append(np.array(imgPoints_view, dtype=np.float32))
                             # all_ids.append(ids) # We don't strictly need all_ids for calibrateCamera
                             captured_count += 1
                             logger.info(f"Capture successful ({captured_count}/{IMAGES_NEEDED}). Move pattern to a new position/angle.")
                        else:
                             logger.warning("Capture failed: Could not match detected markers to board definition.")

                    else:
                        logger.warning("Capture failed: Pattern not detected clearly (need >3 markers).")

                elif key == ord('q'):
                    logger.warning("Calibration cancelled by user.")
                    cv2.destroyAllWindows()
                    return # Exit script

            cv2.destroyAllWindows()
            logger.info("--- Image Capture Complete ---")

            # 4. Perform Calibration Calculation
            if captured_count >= IMAGES_NEEDED:
                logger.info("Calculating calibration parameters...")
                try:
                    # Use calibrateCameraRO for potentially better robustness with outliers
                    # ret, mtx, dist, rvecs, tvecs, stdDeviationsIntrinsics, stdDeviationsExtrinsics, perViewErrors = cv2.calibrateCameraRO(
                    #     obj_points_all, all_corners, img_size, None, None)

                    # Standard calibration
                    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                        obj_points_all, all_corners, img_size, None, None)

                    if ret:
                        logger.info("Calibration successful!")
                        logger.info(f"RMS Reprojection Error: {ret}")
                        logger.info(f"Camera Matrix:\n{mtx}")
                        logger.info(f"Distortion Coefficients:\n{dist.ravel()}") # Flatten for easier reading

                        # 5. Save Parameters
                        calibration_data = {
                            'camera_matrix': mtx,
                            'distortion_coefficients': dist,
                            'image_width': img_size[0],
                            'image_height': img_size[1],
                            'rms_error': ret
                            # Optionally add rvecs, tvecs if needed later
                        }
                        if calibrator.save_parameters(calibration_data):
                            logger.info(f"Calibration parameters saved to '{CALIBRATION_FILENAME}'")
                        else:
                            logger.error("Failed to save calibration parameters.")
                    else:
                        logger.error("Calibration calculation failed (calibrateCamera returned False).")

                except Exception as calib_err:
                    logger.exception(f"Error during calibration calculation: {calib_err}")
            else:
                logger.error("Calibration aborted: Not enough images captured.")

    except RuntimeError as e:
        logger.error(f"Camera or Device Runtime Error: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
    finally:
        cv2.destroyAllWindows() # Ensure windows are closed

    logger.info("--- Calibration Script Finished ---")


if __name__ == "__main__":
    main()