# ArUco Marker Tracking and Distance Calculation

This script uses a camera to detect ArUco markers, track their positions, and calculate the distance a specific marker has moved between two captures.

## Requirements

- Python 3.x
- OpenCV (`opencv-python`)
- NumPy
- DepthAI
- A camera calibrated with a YAML file (e.g., `calibration.yaml`)

## Installation

1. Install the required libraries:
   ```bash
   pip install opencv-contrib-python numpy depthai
   ```

2. Ensure you have a camera calibration file (`calibration.yaml`) in the `../calibration/` directory relative to the script. (You should run the calibration script to generate this file.)

## Usage

1. Navigate to the directory containing the script (`udi_movement.py`).
2. Run the script using Python:
   ```bash
   python udi_movement.py
   ```

3. A live feed from the camera will display.

4. **Capture Positions:**
   - Press `c` to capture the first position of the marker. The first detected marker will be tracked.
   - Press `c` again to capture the second position of the same marker and calculate the distance moved.

5. **Results:**
   - The distance moved by the marker will be displayed on the screen in centimeters.
   - Additional details like pixel displacement and average pixel/cm ratio will also be shown.

6. **Quit:**
   - Press `q` to exit the program.

## Keyboard Controls

- `c`: Capture the marker's position
- `q`: Quit the program

## Notes

- Ensure the camera is properly calibrated for accurate distance measurements.
- The ArUco marker must be clearly visible in the camera feed.
- The marker size is set to 0.024 meters (2.4 cm). Adjust this value in the script if your marker size differs.
- For troubleshooting, check the script’s console output or refer to the source code comments.
