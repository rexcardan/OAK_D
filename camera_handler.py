import depthai as dai
import numpy as np
import time

class OAKDCamera:
    def __init__(self):
        # Initialize pipeline
        self.pipeline = dai.Pipeline()

        # Create and set up RGB camera node
        self.cam_rgb = self.pipeline.create(dai.node.ColorCamera)
        self.cam_rgb.setBoardSocket(dai.CameraBoardSocket.RGB)
        self.cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        self.cam_rgb.setInterleaved(False)
        self.cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)
        self.cam_rgb.setFps(40)

        # Create and set up Mono cameras (left and right) for depth
        cam_left = self.pipeline.create(dai.node.MonoCamera)
        cam_left.setBoardSocket(dai.CameraBoardSocket.LEFT)
        cam_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)

        cam_right = self.pipeline.create(dai.node.MonoCamera)
        cam_right.setBoardSocket(dai.CameraBoardSocket.RIGHT)
        cam_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)

        # Create and set up stereo depth node
        self.stereo = self.pipeline.create(dai.node.StereoDepth)
        self.stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
        self.stereo.setDepthAlign(dai.CameraBoardSocket.RGB)
        
        # Link Mono cameras to stereo depth inputs
        cam_left.out.link(self.stereo.left)
        cam_right.out.link(self.stereo.right)

        # Create output streams for RGB and depth
        self.xout_rgb = self.pipeline.create(dai.node.XLinkOut)
        self.xout_rgb.setStreamName("rgb")
        self.cam_rgb.video.link(self.xout_rgb.input)

        self.xout_depth = self.pipeline.create(dai.node.XLinkOut)
        self.xout_depth.setStreamName("depth")
        self.stereo.depth.link(self.xout_depth.input)

        # Create and set up IMU node for accelerometer and gyroscope data
        self.imu = self.pipeline.create(dai.node.IMU)
        self.imu.enableIMUSensor([dai.IMUSensor.ACCELEROMETER_RAW, dai.IMUSensor.GYROSCOPE_RAW], 500)  # 500 Hz
        self.imu.setBatchReportThreshold(1)
        self.imu.setMaxBatchReports(10)

        self.xout_imu = self.pipeline.create(dai.node.XLinkOut)
        self.xout_imu.setStreamName("imu")
        self.imu.out.link(self.xout_imu.input)

        # Start the device and pipeline
        self.device = dai.Device(self.pipeline)
        self.q_rgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        self.q_depth = self.device.getOutputQueue(name="depth", maxSize=4, blocking=False)
        self.q_imu = self.device.getOutputQueue(name="imu", maxSize=50, blocking=False)

    def getImage(self):
        # Get frame from the RGB camera
        frame = self.q_rgb.get()
        return frame.getCvFrame()

    def getDepthImage(self):
        # Get depth map from the stereo depth node
        frame = self.q_depth.get()
        return frame.getCvFrame()

    def getAccelerometerValues(self):
        # Collect accelerometer values for one second
        start_time = time.time()
        accel_x, accel_y, accel_z = [], [], []

        while time.time() - start_time < 1:  # Collect data for 1 second
            imu_data = self.q_imu.get()  # Get IMU data
            imuPackets = imu_data.packets

            for imuPacket in imuPackets:
                acceleroValues = imuPacket.acceleroMeter

                # Append the x, y, z values to their respective lists
                accel_x.append(acceleroValues.x)
                accel_y.append(acceleroValues.y)
                accel_z.append(acceleroValues.z)

        # Calculate the average values for x, y, and z
        avg_x = np.mean(accel_x) if accel_x else 0
        avg_y = np.mean(accel_y) if accel_y else 0
        avg_z = np.mean(accel_z) if accel_z else 0

        return {'x': avg_x, 'y': avg_y, 'z': avg_z}
