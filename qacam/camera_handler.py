import depthai as dai
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CameraHandler:
    """
    Handles interactions with the OAK-D Lite camera using the depthai library.
    Responsible for device initialization, frame acquisition, and IMU data retrieval.
    """
    def __init__(self, device_info=None):
        """
        Initializes the CameraHandler.

        Args:
            device_info: Optional specific device info to connect to.
                         If None, connects to the first available device.
        """
        self.pipeline = None
        self.device = None
        self.rgb_queue = None
        self.depth_queue = None
        self.imu_queue = None
        self.device_info = device_info
        logger.info("CameraHandler initialized.")
        # Connect and configure pipeline during a separate setup method
        # self.setup_pipeline() # Example: Call setup later

    def setup_pipeline(self):
        """
        Creates the depthai pipeline, configures nodes (RGB, Depth, IMU),
        and connects to the device.
        """
        logger.info("Setting up depthai pipeline...")
        self.pipeline = dai.Pipeline()

        # --- RGB Camera Node ---
        cam_rgb = self.pipeline.create(dai.node.ColorCamera)
        cam_rgb.setPreviewSize(640, 480) # Example resolution
        cam_rgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
        cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        cam_rgb.setInterleaved(False)
        cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)

        # Output for RGB frames
        xout_rgb = self.pipeline.create(dai.node.XLinkOut)
        xout_rgb.setStreamName("rgb")
        cam_rgb.preview.link(xout_rgb.input)

        # --- Depth Perception Nodes ---
        mono_left = self.pipeline.create(dai.node.MonoCamera)
        mono_right = self.pipeline.create(dai.node.MonoCamera)
        stereo = self.pipeline.create(dai.node.StereoDepth)

        # Properties
        mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        mono_left.setCamera("left")
        mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        mono_right.setCamera("right")

        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
        # Options: MEDIAN_OFF, KERNEL_3x3, KERNEL_5x5, KERNEL_7x7 (default)
        stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7)
        stereo.setLeftRightCheck(True)
        stereo.setExtendedDisparity(False)
        stereo.setSubpixel(False)

        # Linking
        mono_left.out.link(stereo.left)
        mono_right.out.link(stereo.right)

        # Output for Depth frames
        xout_depth = self.pipeline.create(dai.node.XLinkOut)
        xout_depth.setStreamName("depth")
        stereo.depth.link(xout_depth.input)

        # --- IMU Node ---
        imu = self.pipeline.create(dai.node.IMU)
        # Enable ACCELEROMETER_RAW and GYROSCOPE_RAW at 100 hz
        imu.enableIMUSensor([dai.IMUSensor.ACCELEROMETER_RAW, dai.IMUSensor.GYROSCOPE_RAW], 100)
        # Above this threshold packets will be sent in batch of X, if the host is slow to receive them.
        # Specify this value based on the required frequency.
        imu.setBatchReportThreshold(5)
        # Link IMU output to XLink
        xout_imu = self.pipeline.create(dai.node.XLinkOut)
        xout_imu.setStreamName("imu")
        imu.out.link(xout_imu.input)

        # --- Connect to Device ---
        try:
            logger.info("Connecting to OAK-D device...")
            # Add timeout to device search
            found, device_info_obj = dai.Device.getFirstAvailableDevice()
            if not found:
                 logger.error("No OAK-D device found.")
                 raise RuntimeError("No OAK-D device found.")

            self.device = dai.Device(self.pipeline, device_info_obj)
            logger.info("Connected to OAK-D device successfully.")

            # --- Get Output Queues ---
            self.rgb_queue = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            self.depth_queue = self.device.getOutputQueue(name="depth", maxSize=4, blocking=False)
            self.imu_queue = self.device.getOutputQueue(name="imu", maxSize=50, blocking=False) # IMU packets are smaller/faster

        except Exception as e:
            logger.error(f"Failed to setup pipeline or connect to device: {e}")
            self.pipeline = None
            self.device = None # Ensure device is None if setup fails
            raise # Re-raise the exception

    def get_rgbd_frames(self):
        """
        Acquires the latest synchronized RGB and Depth frames.

        Returns:
            tuple: (rgb_frame, depth_frame) or (None, None) if frames are not available.
                   Frames are numpy arrays.
        """
        if not self.device or not self.rgb_queue or not self.depth_queue:
            logger.warning("Device not setup or queues not available. Call setup_pipeline() first.")
            return None, None

        rgb_frame = None
        depth_frame = None

        in_rgb = self.rgb_queue.tryGet()
        if in_rgb is not None:
            rgb_frame = in_rgb.getCvFrame()

        in_depth = self.depth_queue.tryGet()
        if in_depth is not None:
            # Depth frame needs conversion for visualization if needed
            # raw_depth = in_depth.getFrame() # Raw depth data
            depth_frame = in_depth.getFrame() # Or use getCvFrame() if appropriate post-processing is done in pipeline

        return rgb_frame, depth_frame

    def get_imu_data(self):
        """
        Acquires the latest IMU data packet.

        Returns:
            dai.IMUData: The IMU data packet containing accelerometer and gyroscope readings,
                         or None if no new data is available.
        """
        if not self.device or not self.imu_queue:
            logger.warning("Device not setup or IMU queue not available. Call setup_pipeline() first.")
            return None

        imu_packet = self.imu_queue.tryGet()
        if imu_packet is not None:
            # Process imu_packet.imuPackets here if needed
            # For example:
            # imu_data = imu_packet.imuPackets
            # for imu_report in imu_data:
            #     accel = imu_report.acceleroMeter
            #     gyro = imu_report.gyroscope
            #     print(f"Accel: {accel.x}, {accel.y}, {accel.z}")
            #     print(f"Gyro: {gyro.x}, {gyro.y}, {gyro.z}")
            return imu_packet
        return None

    def find_pattern(self, frame, pattern_params):
        """
        (Placeholder) Detects an ArUco pattern within a given frame.
        Note: This might be better placed in a dedicated pattern detection module
              or within the Tracking/Calibration components that use it.

        Args:
            frame: The image frame (numpy array) to search within.
            pattern_params: Dictionary defining the ArUco pattern (e.g., dictionary type, marker size).

        Returns:
            list: Detected marker corners and IDs, or None.
        """
        logger.warning("find_pattern is a placeholder and not implemented yet.")
        # Implementation would use OpenCV's ArUco module (cv2.aruco)
        # import cv2.aruco as aruco
        # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # aruco_dict = aruco.getPredefinedDictionary(pattern_params['dictionary'])
        # parameters = aruco.DetectorParameters()
        # corners, ids, rejected = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
        # return corners, ids
        return None

    def close(self):
        """
        Closes the connection to the device.
        """
        if self.device is not None:
            logger.info("Closing connection to OAK-D device.")
            self.device.close()
            self.device = None
            self.pipeline = None
            self.rgb_queue = None
            self.depth_queue = None
            self.imu_queue = None
        logger.info("CameraHandler closed.")

    def __enter__(self):
        """Support context manager entry."""
        self.setup_pipeline() # Setup pipeline when entering context
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support context manager exit."""
        self.close() # Ensure device is closed on exit

# Example Usage (Optional - for testing)
if __name__ == '__main__':
    logger.info("Running CameraHandler example...")
    try:
        # Using context manager ensures the device is closed properly
        with CameraHandler() as handler:
            start_time = time.time()
            while time.time() - start_time < 10: # Run for 10 seconds
                rgb, depth = handler.get_rgbd_frames()
                imu_data = handler.get_imu_data()

                if rgb is not None:
                    logger.info(f"Received RGB frame with shape: {rgb.shape}")
                    # Display frame (requires opencv-python)
                    # import cv2
                    # cv2.imshow("RGB", rgb)

                if depth is not None:
                    logger.info(f"Received Depth frame with shape: {depth.shape}")
                    # Display depth (requires normalization and opencv-python)
                    # import cv2
                    # depth_colormap = cv2.normalize(depth, None, 255,0, cv2.NORM_INF, cv2.CV_8UC1)
                    # depth_colormap = cv2.equalizeHist(depth_colormap)
                    # depth_colormap = cv2.applyColorMap(depth_colormap, cv2.COLORMAP_JET)
                    # cv2.imshow("Depth", depth_colormap)


                if imu_data is not None:
                    logger.info(f"Received {len(imu_data.imuPackets)} IMU packets.")
                    # Example: Print latest accelerometer reading
                    if imu_data.imuPackets:
                         accel = imu_data.imuPackets[-1].acceleroMeter
                         logger.info(f"  Latest Accel: X={accel.x:.2f} Y={accel.y:.2f} Z={accel.z:.2f}")


                # Add a small delay and check for exit key if displaying images
                # key = cv2.waitKey(1)
                # if key == ord('q'):
                #    break
                time.sleep(0.05) # Small delay

    except RuntimeError as e:
         logger.error(f"Runtime Error: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}") # Log full traceback
    finally:
        # Ensure OpenCV windows are destroyed if they were used
        # import cv2
        # cv2.destroyAllWindows()
        logger.info("CameraHandler example finished.")