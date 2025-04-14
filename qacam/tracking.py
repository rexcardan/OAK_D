import time
import json
import logging
import threading
import numpy as np
import cv2
import cv2.aruco as aruco
import os
from datetime import datetime

# Assuming CameraHandler and Calibration are in the same package
from .camera_handler import CameraHandler
from .calibration import Calibration
from .pattern_utils import ARUCO_DICTIONARIES # For accessing dictionary objects

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Tracking:
    """
    Handles tracking the pose of a known pattern (e.g., ArUco board) over time.
    Uses CameraHandler for image acquisition and Calibration for camera parameters.
    """

    def __init__(self, camera_handler: CameraHandler, calibration: Calibration, pattern_params: dict):
        """
        Initializes the Tracking module.

        Args:
            camera_handler: An instance of CameraHandler.
            calibration: An instance of Calibration containing loaded camera parameters.
            pattern_params (dict): Dictionary describing the pattern to track. Expected keys:
                'dictionary_name': Name of the ArUco dictionary (e.g., "DICT_6X6_250").
                'marker_size_m': The size of one marker side in meters.
                'rows': Number of rows in the grid (if using a board).
                'cols': Number of columns in the grid (if using a board).
                'type': 'board' or 'marker' (determines detection logic).
                Optional for 'board':
                'marker_separation_m': Separation between markers in meters.
        """
        if not isinstance(camera_handler, CameraHandler):
            raise TypeError("camera_handler must be an instance of CameraHandler")
        if not isinstance(calibration, Calibration):
            raise TypeError("calibration must be an instance of Calibration")
        if not calibration.get_parameters():
            raise ValueError("Calibration parameters must be loaded in the Calibration instance.")

        self.camera_handler = camera_handler
        self.calibration_params = calibration.get_parameters()
        self.pattern_params = pattern_params
        self.reference_pose = None # Will store the 'home' pose (rvec, tvec)
        self.tracking_data = [] # List to store timestamped poses
        self.is_tracking = False
        self.tracking_thread = None
        self.tracking_interval_s = 1.0 # Default interval

        # Validate pattern_params and setup ArUco detector
        self._validate_pattern_params()
        self.aruco_dict = aruco.getPredefinedDictionary(ARUCO_DICTIONARIES[self.pattern_params['dictionary_name']])
        self.aruco_params = aruco.DetectorParameters()
        # self.aruco_detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_params) # OpenCV 4.7+

        if self.pattern_params['type'] == 'board':
            self.board = aruco.GridBoard(
                size=(self.pattern_params['cols'], self.pattern_params['rows']),
                markerLength=self.pattern_params['marker_size_m'],
                markerSeparation=self.pattern_params['marker_separation_m'],
                dictionary=self.aruco_dict
            )
            logger.info("Tracking initialized for ArUco board.")
        elif self.pattern_params['type'] == 'marker':
             logger.info("Tracking initialized for single ArUco marker.")
             self.board = None # Not used for single marker pose estimation
        else:
             raise ValueError("Invalid pattern_params['type']. Must be 'board' or 'marker'.")


        logger.info("Tracking module initialized.")

    def _validate_pattern_params(self):
        """Checks if required keys are present in pattern_params."""
        required_keys = ['dictionary_name', 'marker_size_m', 'type']
        if self.pattern_params.get('type') == 'board':
            required_keys.extend(['rows', 'cols', 'marker_separation_m'])

        for key in required_keys:
            if key not in self.pattern_params:
                raise ValueError(f"Missing required key in pattern_params: '{key}'")
        if self.pattern_params['dictionary_name'] not in ARUCO_DICTIONARIES:
             raise ValueError(f"Invalid dictionary name in pattern_params: {self.pattern_params['dictionary_name']}")


    def _estimate_pose(self, frame):
        """
        Detects the pattern in the frame and estimates its pose.

        Args:
            frame: The image frame (numpy array) to process.

        Returns:
            tuple: (rvec, tvec) representing the pose (rotation and translation vectors),
                   or (None, None) if the pattern is not detected or pose estimation fails.
                   Returns (None, None) also if calibration params are missing.
        """
        if self.calibration_params is None:
            logger.error("Cannot estimate pose: Calibration parameters not available.")
            return None, None

        mtx = self.calibration_params['camera_matrix']
        dist = self.calibration_params['distortion_coefficients']

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = aruco.detectMarkers(gray, self.aruco_dict, parameters=self.aruco_params)
        # corners, ids, rejected = self.aruco_detector.detectMarkers(gray) # OpenCV 4.7+

        rvec, tvec = None, None
        if ids is not None and len(ids) > 0:
            logger.debug(f"Detected {len(ids)} markers.")
            if self.pattern_params['type'] == 'board' and self.board is not None:
                # Estimate pose for the entire board
                # Requires OpenCV 3.4.2+ for refinePose
                obj_points, img_points = self.board.matchImagePoints(corners, ids)
                if obj_points is not None and img_points is not None and len(obj_points) >= 4: # Need at least 4 points for pose
                    try:
                        # Use solvePnP for initial estimate if refine isn't available or fails
                        retval, rvec, tvec = cv2.solvePnP(obj_points, img_points, mtx, dist)
                        if retval:
                             logger.debug(f"Board pose estimated: tvec={tvec.flatten()}, rvec={rvec.flatten()}")
                        else:
                             logger.warning("Board pose estimation failed (solvePnP returned false).")
                             rvec, tvec = None, None
                        # Optional refinement:
                        # aruco.refineDetectedMarkers(gray, self.board, corners, ids, rejected, mtx, dist)
                        # retval, rvec, tvec = aruco.estimatePoseBoard(corners, ids, self.board, mtx, dist, rvec, tvec) # Use rvec/tvec from solvePnP as initial guess
                        # if not retval:
                        #     logger.warning("Board pose estimation refinement failed.")
                        #     rvec, tvec = None, None # Reset if refinement fails
                    except Exception as e:
                        logger.error(f"Error during board pose estimation: {e}")
                        rvec, tvec = None, None
                else:
                    logger.debug("Not enough points matched for board pose estimation.")

            elif self.pattern_params['type'] == 'marker':
                # Estimate pose for the first detected marker (assuming only one is primary)
                # Note: This is less robust than board estimation.
                marker_size = self.pattern_params['marker_size_m']
                # Define object points for a single marker (origin at top-left)
                obj_pts = np.array([[-marker_size/2, marker_size/2, 0],
                                    [ marker_size/2, marker_size/2, 0],
                                    [ marker_size/2,-marker_size/2, 0],
                                    [-marker_size/2,-marker_size/2, 0]], dtype=np.float32)

                try:
                    # Use solvePnP directly for single markers
                    # We need the corners corresponding to the *first* ID found
                    marker_corners = corners[0].reshape((4, 2)) # Get corners for the first marker
                    retval, rvec, tvec = cv2.solvePnP(obj_pts, marker_corners, mtx, dist)
                    if retval:
                        logger.debug(f"Single marker pose estimated: tvec={tvec.flatten()}, rvec={rvec.flatten()}")
                    else:
                        logger.warning("Single marker pose estimation failed (solvePnP returned false).")
                        rvec, tvec = None, None
                except Exception as e:
                    logger.error(f"Error during single marker pose estimation: {e}")
                    rvec, tvec = None, None
        else:
            logger.debug("No markers detected in the frame.")

        return rvec, tvec


    def set_reference_pose(self):
        """
        Captures the current pose of the pattern and sets it as the reference ('home') pose.

        Returns:
            bool: True if the reference pose was set successfully, False otherwise.
        """
        logger.info("Attempting to set reference pose...")
        rgb_frame, _ = self.camera_handler.get_rgbd_frames()
        if rgb_frame is None:
            logger.error("Failed to get frame from camera to set reference pose.")
            return False

        rvec, tvec = self._estimate_pose(rgb_frame)

        if rvec is not None and tvec is not None:
            self.reference_pose = {'rvec': rvec, 'tvec': tvec, 'timestamp': datetime.now().isoformat()}
            logger.info(f"Reference pose set successfully: tvec={tvec.flatten()}, rvec={rvec.flatten()}")
            return True
        else:
            logger.error("Failed to detect pattern or estimate pose. Reference pose not set.")
            self.reference_pose = None
            return False

    def _tracking_loop(self):
        """Internal method run by the tracking thread."""
        logger.info(f"Tracking loop started with interval: {self.tracking_interval_s}s")
        while self.is_tracking:
            loop_start_time = time.time()
            timestamp = datetime.now().isoformat()

            rgb_frame, depth_frame = self.camera_handler.get_rgbd_frames()
            imu_data = self.camera_handler.get_imu_data() # Get IMU data as well

            current_pose = {'rvec': None, 'tvec': None}
            if rgb_frame is not None:
                rvec, tvec = self._estimate_pose(rgb_frame)
                if rvec is not None and tvec is not None:
                    current_pose['rvec'] = rvec.tolist() # Convert to list for JSON serialization
                    current_pose['tvec'] = tvec.tolist()
            else:
                logger.warning("Tracking loop: Failed to get RGB frame.")

            # --- Store Data ---
            data_point = {
                'timestamp': timestamp,
                'pose': current_pose,
                # Add depth frame info if needed (e.g., path if saved separately, or stats)
                # 'depth_info': depth_frame.shape if depth_frame is not None else None,
                'imu_data': None # Placeholder for processed IMU data
            }

            # Process and add IMU data if available
            if imu_data is not None and imu_data.imuPackets:
                 # Example: Store the last packet's data
                 last_packet = imu_data.imuPackets[-1]
                 accel = last_packet.acceleroMeter
                 gyro = last_packet.gyroscope
                 data_point['imu_data'] = {
                     'accelerometer': {'x': accel.x, 'y': accel.y, 'z': accel.z, 'ts': accel.timestamp.get()},
                     'gyroscope': {'x': gyro.x, 'y': gyro.y, 'z': gyro.z, 'ts': gyro.timestamp.get()}
                 }


            self.tracking_data.append(data_point)
            logger.debug(f"Tracking data point added at {timestamp}. Pose: {current_pose['tvec']}")

            # --- Calculate sleep time ---
            elapsed_time = time.time() - loop_start_time
            sleep_time = self.tracking_interval_s - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                logger.warning(f"Tracking loop took longer ({elapsed_time:.3f}s) than interval ({self.tracking_interval_s}s).")

        logger.info("Tracking loop stopped.")


    def start_tracking(self, interval_s=1.0):
        """
        Starts the tracking process in a separate thread.

        Args:
            interval_s (float): The interval in seconds between pose captures.
        """
        if self.is_tracking:
            logger.warning("Tracking is already running.")
            return

        if self.reference_pose is None:
            logger.warning("Reference pose not set. Call set_reference_pose() first.")
            # Optionally, set reference pose automatically here?
            # if not self.set_reference_pose(): return # Stop if setting ref fails

        self.tracking_interval_s = interval_s
        self.is_tracking = True
        self.tracking_data = [] # Clear previous data
        self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracking_thread.start()
        logger.info("Tracking started.")

    def stop_tracking(self):
        """Stops the tracking process."""
        if not self.is_tracking:
            logger.warning("Tracking is not currently running.")
            return

        self.is_tracking = False
        if self.tracking_thread is not None:
            self.tracking_thread.join(timeout=self.tracking_interval_s * 2) # Wait for thread to finish
            if self.tracking_thread.is_alive():
                logger.warning("Tracking thread did not terminate gracefully.")
            self.tracking_thread = None
        logger.info("Tracking stopped.")
        return self.tracking_data # Return collected data

    def get_tracking_data(self):
        """
        Returns the collected tracking data.

        Returns:
            list: A list of dictionaries, each containing timestamped pose information.
        """
        return self.tracking_data

    def save_tracking_data(self, filepath="tracking_data.json"):
        """
        Saves the collected tracking data to a JSON file.

        Args:
            filepath (str): The path to the file where data should be saved.

        Returns:
            bool: True if saving was successful, False otherwise.
        """
        logger.info(f"Saving tracking data to {filepath}...")
        if not self.tracking_data:
            logger.warning("No tracking data to save.")
            return False

        output_dir = os.path.dirname(filepath)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                logger.info(f"Created output directory: {output_dir}")
            except Exception as e:
                 logger.error(f"Failed to create directory {output_dir}: {e}")
                 return False

        try:
            save_data = {
                'reference_pose': self.reference_pose, # Include reference pose
                'tracking_log': self.tracking_data,
                'pattern_params': self.pattern_params, # Include pattern info
                'calibration_params_summary': { # Include summary, not full matrix maybe
                    'source_file': self.calibration.params_file,
                    'image_width': self.calibration_params.get('image_width'),
                    'image_height': self.calibration_params.get('image_height')
                }
            }
            with open(filepath, 'w') as f:
                json.dump(save_data, f, indent=4)
            logger.info(f"Successfully saved {len(self.tracking_data)} data points to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save tracking data to {filepath}: {e}")
            return False


# Example Usage (Optional - for testing)
if __name__ == '__main__':
    logger.info("Running Tracking example...")

    # --- Configuration ---
    CALIBRATION_FILE = "test_calibration.yaml" # Assumes calibration.py example created this
    OUTPUT_DATA_FILE = "test_tracking_output.json"
    TRACKING_DURATION_S = 5
    TRACKING_INTERVAL_S = 0.5

    # Define the pattern being tracked (MUST match the physical pattern used)
    # Example: Using the pattern generated by pattern_utils.py example
    pattern = {
        'dictionary_name': "DICT_5X5_100", # Must match generated pattern
        'marker_size_m': 0.08, # Physical size of the marker side in meters
        'rows': 4,             # Must match generated pattern
        'cols': 6,             # Must match generated pattern
        'marker_separation_m': 0.02, # Physical separation in meters
        'type': 'board'        # Tracking the whole board
    }
    # Or for a single marker:
    # pattern = {
    #     'dictionary_name': "DICT_6X6_250",
    #     'marker_size_m': 0.1, # Physical size in meters
    #     'type': 'marker'
    # }


    # --- Setup ---
    try:
        # Ensure calibration file exists (or run calibration.py example first)
        if not os.path.exists(CALIBRATION_FILE):
             logger.error(f"Calibration file '{CALIBRATION_FILE}' not found. Run calibration.py example first.")
             exit()

        # Use context managers for CameraHandler
        with CameraHandler() as handler:
            calibrator = Calibration(handler, params_file=CALIBRATION_FILE)
            if not calibrator.get_parameters():
                logger.error("Failed to load calibration parameters. Exiting.")
                exit()

            tracker = Tracking(handler, calibrator, pattern_params=pattern)

            # --- Run Tracking ---
            logger.info("Setting reference pose (point camera at pattern)...")
            time.sleep(2) # Give user time to position pattern
            if tracker.set_reference_pose():
                logger.info(f"Starting tracking for {TRACKING_DURATION_S} seconds...")
                tracker.start_tracking(interval_s=TRACKING_INTERVAL_S)
                time.sleep(TRACKING_DURATION_S)
                collected_data = tracker.stop_tracking()
                logger.info(f"Tracking finished. Collected {len(collected_data)} data points.")

                # Save the data
                if tracker.save_tracking_data(OUTPUT_DATA_FILE):
                    logger.info(f"Tracking data saved to {OUTPUT_DATA_FILE}")
                else:
                    logger.error("Failed to save tracking data.")
            else:
                logger.error("Could not set reference pose. Ensure pattern is visible and calibration is correct.")

    except RuntimeError as e:
         logger.error(f"Runtime Error during example: {e}")
    except ValueError as e:
         logger.error(f"Configuration Error: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during example: {e}")
    finally:
        logger.info("Tracking example finished.")