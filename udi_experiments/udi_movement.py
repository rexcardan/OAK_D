import cv2
import numpy as np
import depthai as dai

# Load camera calibration from YAML
cv_file = cv2.FileStorage('calibration.yaml', cv2.FILE_STORAGE_READ)
camera_matrix = cv_file.getNode('camera_matrix').mat()
dist_coeffs = cv_file.getNode('dist_coeffs').mat()
cv_file.release()

# Set up DepthAI pipeline
pipeline = dai.Pipeline()
cam_rgb = pipeline.createColorCamera()
cam_rgb.setPreviewSize(640, 480)  # Adjust this to match the resolution used during calibration
cam_rgb.setInterleaved(False)
cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
xout_rgb = pipeline.createXLinkOut()
xout_rgb.setStreamName("rgb")
cam_rgb.preview.link(xout_rgb.input)

# Define ArUco dictionary and parameters
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_1000)
aruco_params = cv2.aruco.DetectorParameters()
marker_size = 0.04  # Marker size in meters (4 cm)

# Start device
with dai.Device(pipeline) as device:
    q_rgb = device.getOutputQueue("rgb", maxSize=4, blocking=False)

    captures = []  # Store translation vectors for two captures
    corner_captures = []  # Store corners for pixel displacement
    tracked_id = None  # Track the selected marker ID

    print("Instructions:")
    print("- Press 'c' to capture the marker's position. The first detected marker will be tracked.")
    print("- Press 'c' again to capture the second position of the same marker and calculate the distance moved.")
    print("- Press 'q' to quit.")

    while True:
        in_rgb = q_rgb.tryGet()
        if in_rgb is not None:
            frame = in_rgb.getCvFrame()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, rejected = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=aruco_params)
            if ids is not None:
                cv2.aruco.drawDetectedMarkers(frame, corners, ids)
                rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(corners, marker_size, camera_matrix, dist_coeffs)
                for i in range(len(ids)):
                    # Ensure tvecs[i] is valid
                    tvec = np.squeeze(tvecs[i])  # Convert (1, 3) to (3,)
                    if tvec.shape == (3,):
                        cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvecs[i], tvecs[i], 0.1)
                        # Compute bounding box size in pixels and cm
                        corner = corners[i][0]
                        pixel_width = np.max(corner[:, 0]) - np.min(corner[:, 0])
                        pixel_height = np.max(corner[:, 1]) - np.min(corner[:, 1])
                        # Pixel/cm conversion using bounding box
                        pixel_per_cm = pixel_width / 4.0  # Physical marker size is 4 cm
                        # Pixel/cm conversion using focal length and distance
                        Z_cm = tvec[2] * 100  # Convert meters to cm
                        pixel_per_cm_focal = camera_matrix[0, 0] / Z_cm if Z_cm > 0 else float('inf')
                        # Bounding box in cm
                        width_cm = pixel_width / pixel_per_cm
                        height_cm = pixel_height / pixel_per_cm
                        # Display metrics on frame
                        cv2.putText(frame, f"ID {ids[i][0]}: {width_cm:.2f} x {height_cm:.2f} cm",
                                    (int(corner[0, 0]), int(corner[0, 1]) - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        cv2.putText(frame, f"Pixel/cm: {pixel_per_cm:.2f} (box), {pixel_per_cm_focal:.2f} (focal)",
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    else:
                        print(f"Warning: tvecs[{i}] has unexpected shape: {tvec.shape}")

                if cv2.waitKey(1) == ord('c'):
                    if tracked_id is None:
                        if len(ids) > 0 and np.squeeze(tvecs[0]).shape == (3,):
                            tracked_id = ids[0][0]
                            captures.append(np.squeeze(tvecs[0]))
                            corner_captures.append(corners[0][0])  # Store corners of first marker
                            print(f"Tracking marker ID {tracked_id}. Capture 1 recorded.")
                        else:
                            print("No valid marker pose detected for capture.")
                    else:
                        if tracked_id in ids:
                            idx = np.where(ids == tracked_id)[0][0]
                            if np.squeeze(tvecs[idx]).shape == (3,):
                                captures.append(np.squeeze(tvecs[idx]))
                                corner_captures.append(corners[idx][0])
                                print(f"Capture 2 recorded for marker ID {tracked_id}.")
                                if len(captures) == 2:
                                    # Compute 3D distance
                                    diff = captures[1] - captures[0]
                                    distance = np.linalg.norm(diff)
                                    print(f"Distance moved: {distance:.4f} meters")
                                    # Compute pixel displacement
                                    center1 = np.mean(corner_captures[0], axis=0)  # Centroid of first capture
                                    center2 = np.mean(corner_captures[1], axis=0)  # Centroid of second capture
                                    pixel_diff = np.linalg.norm(center2 - center1)
                                    print(f"Pixel displacement: {pixel_diff:.2f} pixels")
                                    # Reset captures
                                    captures = []
                                    corner_captures = []
                                    tracked_id = None
                            else:
                                print(f"Invalid pose for marker ID {tracked_id}.")
                        else:
                            print(f"Marker ID {tracked_id} not detected.")
            else:
                if cv2.waitKey(1) == ord('c'):
                    print("No markers detected.")
            cv2.imshow("ArUco Tracking", frame)

        if cv2.waitKey(1) == ord('q'):
            break

cv2.destroyAllWindows()