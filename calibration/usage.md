# ArUco Board Calibration

This script uses a DepthAI camera to detect an ArUco board and perform camera calibration based on multiple captures of the board. This is relevant to the gui.py script in this directory

## Requirements

- Python 3.x
- OpenCV (`opencv-python`)
- NumPy
- DepthAI

## Installation

1. Install the required libraries:
   ```bash
   pip install opencv-python numpy depthai
   ```

2. Ensure you have an ArUco board ready. The script is configured for a 5x7 grid with 2.7 cm markers and 0.7 cm spacing.

## Usage

1. Navigate to the directory containing the script (`gui.py`).
2. Run the script using Python:
   ```bash
   python gui.py
   ```

3. A live feed from the camera will display at 1920x1080 resolution.

4. **Capture Positions:**
   - Position the camera so that the ArUco board is clearly visible.
   - Press `c` to capture the current frame if at least 10 markers are detected.
   - Repeat this process to capture multiple images (at least 5 are recommended for better calibration).

5. **Calibrate:**
   - Once you have captured enough images (minimum 5), press `s` to start the calibration process.
   - The calibration results, including the camera matrix and distortion coefficients, will be saved to `calibration.yaml`.

6. **Quit:**
   - Press `q` to exit the program without calibrating.

## Keyboard Controls

- `c`: Capture the current frame if at least 10 markers are detected
- `s`: Start calibration (requires at least 5 captures)
- `q`: Quit the program

## Notes

- Ensure the ArUco board is clearly visible and well-lit for accurate detection.
- The script uses a 5x7 grid board with 2.7 cm markers and 0.7 cm spacing. Adjust these values in the script (`board = aruco.GridBoard((5, 7), 0.027, 0.007, dictionary)`) if your board differs.
- The camera feed runs at 1920x1080 for high-resolution detection. Modify `cam.setPreviewSize(1920, 1080)` if needed.
- For troubleshooting, check the console output for details like the number of markers detected or calibration errors.
- Try to cover a multitude of angles/distances for the best calibration results
- Make a quick check in the yaml to ensure that the matrix of values contains numbers on the order of 100-500, anything higher, and a re-calibration is likely, since the camera should not have significant distortion out of the box. 
