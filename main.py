from camera_handler import OAKDCamera
import cv2

def main():
    # Initialize camera
    camera = OAKDCamera()

    # Get an RGB image
    image = camera.getImage()
    cv2.imshow("RGB Image", image)

    # Get a Depth image
    depth_image = camera.getDepthImage()
    cv2.imshow("Depth Image", depth_image)

    # Get accelerometer values (averaged over 1 second)
    accel_values = camera.getAccelerometerValues()
    print("Accelerometer values (averaged):", accel_values)

    # Wait for a key press before closing
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
