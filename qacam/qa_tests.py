import time
import logging
import json
import os
from datetime import datetime

# Assuming Tracking is in the same package
from .tracking import Tracking
from .camera_handler import CameraHandler # Potentially needed for direct IMU access?
from .calibration import Calibration # For context in example
from .pattern_utils import generate_pattern # For context in example


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QATests:
    """
    Implements specific QA test sequences using the Tracking module.
    Guides the user through test steps and records data via the tracker.
    """

    def __init__(self, tracker: Tracking):
        """
        Initializes the QATests module.

        Args:
            tracker: An instance of the Tracking module, already initialized
                     with CameraHandler and Calibration.
        """
        if not isinstance(tracker, Tracking):
            raise TypeError("tracker must be an instance of Tracking")
        self.tracker = tracker
        self.test_results = {} # Dictionary to store results of different tests
        logger.info("QATests module initialized.")

    def _prompt_user_and_wait(self, message):
        """Helper function to prompt user and wait for confirmation."""
        input(f"ACTION REQUIRED: {message}. Press Enter to continue...")
        logger.info(f"User confirmed action: {message}")
        # Add a small delay to allow systems to settle if needed
        time.sleep(0.5)

    def _record_measurement(self, step_name):
        """
        Stops tracking briefly to record a stable measurement for a test step.
        Restarts tracking afterwards.

        Args:
            step_name (str): Name of the test step being measured.

        Returns:
            dict: The last recorded data point from the tracker, or None.
        """
        logger.info(f"Attempting to record measurement for step: {step_name}")
        # Stop tracking to get the latest consistent data
        # Note: This assumes the tracker stores data internally even when stopped briefly.
        # If tracker clears data on stop, we need a different approach (e.g., get last N points).
        # Or, perhaps better: add a method to Tracking to get a single, current pose estimate.
        # For now, we'll assume stop_tracking returns the data collected just before stopping.

        # Let's refine this: Instead of stopping/starting, let's add a method to Tracking
        # to explicitly capture and return the *current* pose on demand.
        # --- Refinement Needed in Tracking class ---
        # Add a method like `get_current_pose()` to Tracking.py
        # For now, we simulate this by getting the last data point if tracking.

        if not self.tracker.is_tracking:
             logger.warning("Tracker is not running. Cannot record measurement.")
             # Maybe try to get a single frame and estimate pose directly?
             # Requires access to camera_handler and calibration params here...
             # For simplicity now, we rely on the tracker being active.
             return None


        # Get the latest data point(s)
        # A better approach might be needed depending on Tracking implementation details
        # (e.g., averaging last few points, or a dedicated 'capture' method)
        time.sleep(self.tracker.tracking_interval_s * 1.5) # Wait for at least one cycle
        all_data = self.tracker.get_tracking_data()
        if not all_data:
            logger.error("No tracking data available to record measurement.")
            return None

        last_data_point = all_data[-1].copy() # Get the most recent point
        last_data_point['step_name'] = step_name # Add context
        logger.info(f"Measurement recorded for {step_name}: Pose={last_data_point.get('pose', {}).get('tvec')}")
        return last_data_point


    def run_couch_test(self, output_dir="qa_results/couch_test"):
        """
        Executes the couch position QA test sequence.

        Guides the user through moving the couch and records pattern pose at each step.

        Args:
            output_dir (str): Directory to save the results JSON file.

        Returns:
            bool: True if the test completed and results were saved, False otherwise.
        """
        logger.info("Starting Couch QA Test...")
        test_name = "couch_position_test"
        results = {'test_name': test_name, 'steps': [], 'start_time': datetime.now().isoformat()}

        if not self.tracker.reference_pose:
             logger.error("Reference pose is not set in the tracker. Cannot start test.")
             return False

        try:
            # Start tracking continuously for the duration of the test
            self.tracker.start_tracking(interval_s=0.5) # Use a reasonable interval

            # 1. Initial Position (Home)
            self._prompt_user_and_wait("Ensure pattern is at the 'Home' position (0,0,0)")
            measurement = self._record_measurement("Home Position")
            if measurement: results['steps'].append(measurement)

            # 2. Move Right (+X)
            self._prompt_user_and_wait("Move couch 20 cm to RIGHT (+X)")
            measurement = self._record_measurement("Couch Right 20cm")
            if measurement: results['steps'].append(measurement)

            # 3. Back to Baseline
            self._prompt_user_and_wait("Move couch back to 'Home' position")
            measurement = self._record_measurement("Return Home from Right")
            if measurement: results['steps'].append(measurement)

            # 4. Move Left (-X)
            self._prompt_user_and_wait("Move couch 20 cm to LEFT (-X)")
            measurement = self._record_measurement("Couch Left 20cm")
            if measurement: results['steps'].append(measurement)

            # 5. Back to Baseline
            self._prompt_user_and_wait("Move couch back to 'Home' position")
            measurement = self._record_measurement("Return Home from Left")
            if measurement: results['steps'].append(measurement)

            # 6. Move Towards Gantry (+Y) - Assuming Y is towards gantry
            self._prompt_user_and_wait("Move couch 20 cm TOWARDS GANTRY (+Y)")
            measurement = self._record_measurement("Couch Towards Gantry 20cm")
            if measurement: results['steps'].append(measurement)

            # 7. Back to Baseline
            self._prompt_user_and_wait("Move couch back to 'Home' position")
            measurement = self._record_measurement("Return Home from Towards Gantry")
            if measurement: results['steps'].append(measurement)

            # 8. Move Away from Gantry (-Y)
            self._prompt_user_and_wait("Move couch 20 cm AWAY FROM GANTRY (-Y)")
            measurement = self._record_measurement("Couch Away Gantry 20cm")
            if measurement: results['steps'].append(measurement)

            # 9. Back to Baseline
            self._prompt_user_and_wait("Move couch back to 'Home' position")
            measurement = self._record_measurement("Return Home from Away Gantry")
            if measurement: results['steps'].append(measurement)

            # 10. Move Up (+Z)
            self._prompt_user_and_wait("Move couch 10 cm UP (+Z)")
            measurement = self._record_measurement("Couch Up 10cm")
            if measurement: results['steps'].append(measurement)

            # 11. Back to Baseline
            self._prompt_user_and_wait("Move couch back to 'Home' position")
            measurement = self._record_measurement("Return Home from Up")
            if measurement: results['steps'].append(measurement)

            # 12. Move Down (-Z)
            self._prompt_user_and_wait("Move couch 10 cm DOWN (-Z)")
            measurement = self._record_measurement("Couch Down 10cm")
            if measurement: results['steps'].append(measurement)

            # 13. Back to Baseline
            self._prompt_user_and_wait("Move couch back to 'Home' position")
            measurement = self._record_measurement("Return Home from Down")
            if measurement: results['steps'].append(measurement)

            # 14. Rotate Couch +90 deg (Yaw)
            self._prompt_user_and_wait("Rotate couch +90 degrees (Clockwise from above?)")
            measurement = self._record_measurement("Couch Rotate +90 deg")
            if measurement: results['steps'].append(measurement)

            # 15. Back to Baseline
            self._prompt_user_and_wait("Rotate couch back to 0 degrees")
            measurement = self._record_measurement("Return Home from +90 deg")
            if measurement: results['steps'].append(measurement)

            # 16. Rotate Couch -90 deg (Yaw)
            self._prompt_user_and_wait("Rotate couch -90 degrees (Counter-Clockwise?)")
            measurement = self._record_measurement("Couch Rotate -90 deg")
            if measurement: results['steps'].append(measurement)

            # 17. Back to Baseline
            self._prompt_user_and_wait("Rotate couch back to 0 degrees")
            measurement = self._record_measurement("Return Home from -90 deg")
            if measurement: results['steps'].append(measurement)


            results['end_time'] = datetime.now().isoformat()
            self.test_results[test_name] = results
            logger.info("Couch QA Test finished.")

        except Exception as e:
            logger.exception(f"Error during Couch QA Test: {e}")
            return False
        finally:
            # Ensure tracking is stopped even if errors occurred
            if self.tracker.is_tracking:
                self.tracker.stop_tracking()

        # Save results
        return self._save_test_results(test_name, output_dir)


    def run_gantry_angle_test(self, output_dir="qa_results/gantry_test"):
        """
        Executes the gantry angle QA test sequence.

        Guides the user through rotating the gantry and records IMU angle at each step.
        Note: This relies purely on the camera's IMU, assuming the camera is fixed relative
              to the gantry's rotation axis in a known way, or fixed to the gantry itself.
              Pose tracking of a pattern might be irrelevant here unless the pattern is
              fixed in the room and the camera moves with the gantry.

        Args:
            output_dir (str): Directory to save the results JSON file.

        Returns:
            bool: True if the test completed and results were saved, False otherwise.
        """
        logger.info("Starting Gantry Angle QA Test...")
        test_name = "gantry_angle_test"
        results = {'test_name': test_name, 'steps': [], 'start_time': datetime.now().isoformat()}

        # This test primarily uses IMU data. We might not need pattern tracking.
        # We need a way to reliably get the *current* IMU reading.
        # Let's assume CameraHandler needs a method like `get_current_imu_reading()`
        # or we process the stream from Tracking.

        try:
            # Start tracking to get IMU stream (if Tracking provides it)
            # Or, interact directly with CameraHandler if needed.
            self.tracker.start_tracking(interval_s=0.2) # Faster interval for potentially faster moves

            # 1. Gantry 0 degrees
            self._prompt_user_and_wait("Set Gantry angle to 0 degrees")
            measurement = self._record_measurement("Gantry 0 deg") # Record includes IMU
            if measurement: results['steps'].append(measurement)

            # 2. Gantry 90 degrees
            self._prompt_user_and_wait("Rotate Gantry to 90 degrees")
            measurement = self._record_measurement("Gantry 90 deg")
            if measurement: results['steps'].append(measurement)

            # 3. Gantry 180 degrees
            self._prompt_user_and_wait("Rotate Gantry to 180 degrees")
            measurement = self._record_measurement("Gantry 180 deg")
            if measurement: results['steps'].append(measurement)

            # 4. Gantry 270 degrees
            self._prompt_user_and_wait("Rotate Gantry to 270 degrees")
            measurement = self._record_measurement("Gantry 270 deg")
            if measurement: results['steps'].append(measurement)

            # 5. Return to 0 (optional but good practice)
            self._prompt_user_and_wait("Rotate Gantry back to 0 degrees")
            measurement = self._record_measurement("Gantry Return 0 deg")
            if measurement: results['steps'].append(measurement)


            results['end_time'] = datetime.now().isoformat()
            self.test_results[test_name] = results
            logger.info("Gantry Angle QA Test finished.")

        except Exception as e:
            logger.exception(f"Error during Gantry Angle QA Test: {e}")
            return False
        finally:
            if self.tracker.is_tracking:
                self.tracker.stop_tracking()

        return self._save_test_results(test_name, output_dir)


    def run_collimator_angle_test(self, output_dir="qa_results/collimator_test"):
        """
        Executes the collimator angle QA test sequence.

        Guides the user through rotating the collimator and records IMU angle.
        Assumes camera orientation allows IMU to measure collimator rotation,
        or relies on pattern tracking if camera is fixed and pattern rotates.

        Args:
            output_dir (str): Directory to save the results JSON file.

        Returns:
            bool: True if the test completed and results were saved, False otherwise.
        """
        logger.info("Starting Collimator Angle QA Test...")
        test_name = "collimator_angle_test"
        results = {'test_name': test_name, 'steps': [], 'start_time': datetime.now().isoformat()}

        try:
            # Start tracking for IMU/Pose data
            self.tracker.start_tracking(interval_s=0.2)

            # Initial Setup: Gantry at 270
            self._prompt_user_and_wait("Set Gantry angle to 270 degrees")
            # No measurement needed here, just setup for collimator rotation

            # 1. Collimator 0 degrees
            self._prompt_user_and_wait("Set Collimator angle to 0 degrees")
            measurement = self._record_measurement("Collimator 0 deg (Gantry 270)")
            if measurement: results['steps'].append(measurement)

            # 2. Collimator 90 degrees
            self._prompt_user_and_wait("Rotate Collimator to 90 degrees")
            measurement = self._record_measurement("Collimator 90 deg (Gantry 270)")
            if measurement: results['steps'].append(measurement)

            # 3. Collimator back to 0 degrees
            self._prompt_user_and_wait("Rotate Collimator back to 0 degrees")
            measurement = self._record_measurement("Collimator Return 0 deg (Gantry 270)")
            if measurement: results['steps'].append(measurement)

            # 4. Collimator -90 degrees
            self._prompt_user_and_wait("Rotate Collimator to -90 degrees")
            measurement = self._record_measurement("Collimator -90 deg (Gantry 270)")
            if measurement: results['steps'].append(measurement)

            # 5. Return to 0 (optional)
            self._prompt_user_and_wait("Rotate Collimator back to 0 degrees")
            measurement = self._record_measurement("Collimator Final Return 0 deg (Gantry 270)")
            if measurement: results['steps'].append(measurement)


            results['end_time'] = datetime.now().isoformat()
            self.test_results[test_name] = results
            logger.info("Collimator Angle QA Test finished.")

        except Exception as e:
            logger.exception(f"Error during Collimator Angle QA Test: {e}")
            return False
        finally:
            if self.tracker.is_tracking:
                self.tracker.stop_tracking()

        return self._save_test_results(test_name, output_dir)


    def _save_test_results(self, test_name, output_dir):
        """Saves the results of a specific test to a JSON file."""
        if test_name not in self.test_results:
            logger.error(f"No results found for test '{test_name}' to save.")
            return False

        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                logger.info(f"Created results directory: {output_dir}")
            except Exception as e:
                logger.error(f"Failed to create results directory {output_dir}: {e}")
                return False

        filename = f"{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, 'w') as f:
                json.dump(self.test_results[test_name], f, indent=4)
            logger.info(f"Successfully saved test results to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save test results to {filepath}: {e}")
            return False

    def get_test_results(self, test_name=None):
        """
        Returns the results of a specific test or all tests.

        Args:
            test_name (str, optional): The name of the test to retrieve results for.
                                       If None, returns results for all tests run.

        Returns:
            dict or None: The results dictionary for the specified test, or all results,
                          or None if the test name is not found.
        """
        if test_name:
            return self.test_results.get(test_name)
        else:
            return self.test_results


# Example Usage (Optional - for testing)
if __name__ == '__main__':
    logger.info("Running QATests example...")

    # --- Configuration (same as Tracking example) ---
    CALIBRATION_FILE = "test_calibration.yaml"
    PATTERN_OUTPUT_FILE = "test_pattern_for_qa.png"
    RESULTS_BASE_DIR = "qa_test_results_example"

    # Define the pattern (ensure physical pattern matches this)
    pattern = {
        'dictionary_name': "DICT_5X5_100",
        'marker_size_m': 0.08,
        'rows': 4,
        'cols': 6,
        'marker_separation_m': 0.02,
        'type': 'board'
    }

    # --- Setup ---
    try:
        # Generate pattern if it doesn't exist (for visual reference)
        if not os.path.exists(PATTERN_OUTPUT_FILE):
             logger.info(f"Generating test pattern '{PATTERN_OUTPUT_FILE}'...")
             generate_pattern(
                 output_filepath=PATTERN_OUTPUT_FILE,
                 rows=pattern['rows'],
                 cols=pattern['cols'],
                 marker_size_pixels=100, # Example pixel size
                 marker_separation_pixels=25, # Example pixel separation
                 dictionary_name=pattern['dictionary_name']
             )


        # Ensure calibration file exists
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
            qa_tester = QATests(tracker)

            # --- Run Tests ---
            logger.info("--- Preparing for Couch Test ---")
            logger.info("Please position the pattern at the 'Home' location.")
            logger.info("Ensure the camera has a clear view of the pattern.")
            input("Press Enter when ready to set reference pose...")
            if qa_tester.tracker.set_reference_pose():
                logger.info("Reference pose set.")

                # Run Couch Test
                run_couch = input("Run Couch Test? (y/n): ").lower() == 'y'
                if run_couch:
                    couch_results_dir = os.path.join(RESULTS_BASE_DIR, "couch_test")
                    success = qa_tester.run_couch_test(output_dir=couch_results_dir)
                    logger.info(f"Couch Test completed: {'Success' if success else 'Failed'}")

                # Run Gantry Test
                run_gantry = input("Run Gantry Angle Test? (y/n): ").lower() == 'y'
                if run_gantry:
                    gantry_results_dir = os.path.join(RESULTS_BASE_DIR, "gantry_test")
                    success = qa_tester.run_gantry_angle_test(output_dir=gantry_results_dir)
                    logger.info(f"Gantry Angle Test completed: {'Success' if success else 'Failed'}")

                # Run Collimator Test
                run_collimator = input("Run Collimator Angle Test? (y/n): ").lower() == 'y'
                if run_collimator:
                    collimator_results_dir = os.path.join(RESULTS_BASE_DIR, "collimator_test")
                    success = qa_tester.run_collimator_angle_test(output_dir=collimator_results_dir)
                    logger.info(f"Collimator Angle Test completed: {'Success' if success else 'Failed'}")

                # Print summary of results collected
                all_results = qa_tester.get_test_results()
                logger.info("\n--- Test Results Summary ---")
                for test, data in all_results.items():
                    logger.info(f"Test: {test}, Steps Recorded: {len(data.get('steps', []))}")
                logger.info("--------------------------")


            else:
                logger.error("Could not set reference pose. Aborting tests.")


    except RuntimeError as e:
         logger.error(f"Runtime Error during example: {e}")
    except ValueError as e:
         logger.error(f"Configuration Error: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during example: {e}")
    finally:
        logger.info("QATests example finished.")