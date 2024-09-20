import depthai as dai
import cv2
import numpy as np

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

        # Create and set up Mono cameras (left and right)
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

        # Placeholder for inclinometer setup (mock values or sensor)
        self.inclinometer_values = {"roll": 0, "pitch": 0, "yaw": 0}

        # Start the device and pipeline
        self.device = dai.Device(self.pipeline)
        self.q_rgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        self.q_depth = self.device.getOutputQueue(name="depth", maxSize=4, blocking=False)

    def getImage(self):
        # Get frame from the RGB camera
        frame = self.q_rgb.get()
        return frame.getCvFrame()

    def getDepthImage(self):
        # Get depth map from the stereo depth node
        frame = self.q_depth.get()
        return frame.getCvFrame()

    def getInclinometerValues(self):
        # For now, return static inclinometer values (replace with real sensor data)
        return self.inclinometer_values
