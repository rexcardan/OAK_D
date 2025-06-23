import cv2
import cv2.aruco as aruco
import depthai as dai
import numpy as np

# Define ArUco dictionary and board (5x7 grid, 2.7 cm markers, 0.7 cm spacing)
dictionary = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
board = aruco.GridBoard((5, 7), 0.027, 0.007, dictionary)  # Sizes in meters

# Setup DepthAI pipeline for color camera
pipeline = dai.Pipeline()
cam = pipeline.createColorCamera()
cam.setPreviewSize(1920, 1080)  # High resolution for better detection
cam.setInterleaved(False)
xout = pipeline.createXLinkOut()
xout.setStreamName("preview")
cam.preview.link(xout.input)

# Initialize lists for calibration data
all_corners = []
all_ids = []
min_markers = 10  # Minimum markers to detect for a valid capture
captured_images = 0

# Start the device and display the feed
with dai.Device(pipeline) as device:
    q = device.getOutputQueue("preview")
    while True:
        frame = q.get().getCvFrame()  # Get BGR frame from DepthAI
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = aruco.detectMarkers(gray, dictionary)

        # Draw detected markers on the frame
        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)

        # Display instructions and image count
        instructions = "Position camera. Press 'c' to capture, 's' to calibrate, 'q' to quit"
        cv2.putText(frame, instructions, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Captured: {captured_images}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Camera Feed", frame)

        # Handle key presses
        key = cv2.waitKey(10) & 0xFF
        if key == ord('c'):
            if ids is not None and len(ids) >= min_markers:
                all_corners.append(corners)  # Store corners as list of (1, 4, 2) arrays
                all_ids.append(ids)         # Store ids as (n, 1) array
                captured_images += 1
                print(f"Captured image {captured_images} with {len(ids)} markers")
            else:
                print(f"Not enough markers detected ({len(ids) if ids is not None else 0}/{min_markers})")
        elif key == ord('s'):
            if captured_images >= 5:
                print("Starting calibration...")
                break
            else:
                print("Capture at least 5 images for better calibration.")
        elif key == ord('q'):
            print("Exiting without calibration.")
            exit(0)

    # Perform camera calibration
    imsize = (frame.shape[1], frame.shape[0])  # Width, height
    cameraMatrix = np.zeros((3, 3))
    distCoeffs = np.zeros((5, 1))

    if all_corners:
        # Flatten corners and IDs
        flat_corners = [c for image_corners in all_corners for c in image_corners]  # List of (1, 4, 2) arrays
        flat_ids = np.array([id for image_ids in all_ids for id in image_ids.flatten()], dtype=np.int32)  # Numpy array of integers
        counter = np.array([len(image_ids) for image_ids in all_ids], dtype=np.int32)  # Numpy array of marker counts per image

        # Debugging prints to verify types and shapes
        print(f"Type of flat_corners: {type(flat_corners)}")
        print(f"Type of flat_corners[0]: {type(flat_corners[0])}")
        print(f"Shape of flat_corners[0]: {flat_corners[0].shape}")
        print(f"Type of flat_ids: {type(flat_ids)}")
        print(f"Shape of flat_ids: {flat_ids.shape}")
        print(f"Dtype of flat_ids: {flat_ids.dtype}")
        print(f"Type of counter: {type(counter)}")
        print(f"Shape of counter: {counter.shape}")
        print(f"Dtype of counter: {counter.dtype}")

        # Perform calibration
        ret, cameraMatrix, distCoeffs, rvecs, tvecs = aruco.calibrateCameraAruco(
            flat_corners, flat_ids, counter, board, imsize, cameraMatrix, distCoeffs
        )

        # Check calibration result and save
        if ret:
            print(f"Calibration successful. Reprojection error: {ret:.4f}")
            fs = cv2.FileStorage("calibration.yaml", cv2.FILE_STORAGE_WRITE)
            fs.write("camera_matrix", cameraMatrix)
            fs.write("dist_coeffs", distCoeffs)
            fs.release()
            print("Calibration saved to 'calibration.yaml'")
        else:
            print("Calibration failed.")
    else:
        print("No corners captured for calibration.")

cv2.destroyAllWindows()