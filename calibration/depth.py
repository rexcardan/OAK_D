import cv2
import depthai as dai
import numpy as np


def create_pipeline():
    # Create pipeline
    pipeline = dai.Pipeline()

    # Define sources and outputs
    left = pipeline.create(dai.node.MonoCamera)
    right = pipeline.create(dai.node.MonoCamera)
    stereo = pipeline.create(dai.node.StereoDepth)
    depth_out = pipeline.create(dai.node.XLinkOut)

    depth_out.setStreamName("depth")

    # Properties
    left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    left.setBoardSocket(dai.CameraBoardSocket.LEFT)
    right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    right.setBoardSocket(dai.CameraBoardSocket.RIGHT)

    # Stereo depth configuration
    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
    stereo.setLeftRightCheck(True)
    stereo.setExtendedDisparity(False)
    stereo.setSubpixel(True)
    stereo.setDepthAlign(dai.CameraBoardSocket.RGB)

    # Linking
    left.out.link(stereo.left)
    right.out.link(stereo.right)
    stereo.depth.link(depth_out.input)

    return pipeline, stereo


def main():
    # Connect to device and start pipeline
    pipeline, stereo = create_pipeline()
    with dai.Device(pipeline) as device:
        # Output queue
        depth_queue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)

        print("Depth calibration running. Press 'q' to quit.")

        while True:
            # Get depth frame
            depth_data = depth_queue.get()
            depth_frame = depth_data.getFrame()

            # Normalize depth for visualization
            depth_frame = (depth_frame * (255 / stereo.initialConfig.getMaxDisparity())).astype(np.uint8)
            depth_frame = cv2.applyColorMap(depth_frame, cv2.COLORMAP_JET)

            # Display
            cv2.imshow("Depth Map", depth_frame)

            # Check for quit
            if cv2.waitKey(1) == ord('q'):
                break

        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()