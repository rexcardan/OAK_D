# QA Cam
## Overview
The QA Cam project is a library to automate mechanical QA for medical physicists. Its core components rely on the OAK-D Lite camera for color image and depth image acquisition. 

## Main Functions
1. qa_cam.calibrate(): using a preset printed calibration Aruco code pattern, an image is taken with both the color and depth camera and the intrinsic and extrinsic parameters are calculated. 
2. qa_cam.generate_pattern(): generate a calibration pattern with a specified number of Aruco codes, the size of the pattern, and the distance between the codes. The pattern is saved as a png file.
3. qa_cam.find_pattern(): using a preset pattern Aruco code print, the 3D coordinates of all of the poinnts of the Aruco patterns and ids are returned
4. qa_cam.orient(): the find_pattern() method is called, and the coordinates are stored as the "home" position for the session
5. qa_cam.start_tracking(int s): once every s seconds, a snapshot is taken of the pattern, the coordinates are stored with a timestamp. the result is stored as a json file
6. qa_cam.stop_tracking(): stop the tracking
7. qa_cam.get_level_angle(): return the angular (level) reading from the accelerometer of the camera

### QA Test Capabilities
1. Couch tracking - x,y,z tracking of pattern attached to couch
    * Take initial image
    * Move couch to 20 cm to right, take image
    * Move couch back to baseline, take image
    * Move couch to 20 cm to left, take image
    * Move couch back to baseline, take image
    * Move couch 20 cm toward gantry, take image
    * Move couch back to baseline, take image
    * Move couch -20 cm away from gantry, take image
    * Move couch back to baseline
    * Move couch toward ceiling 10 cm, take image
    * Move couch back to baseline, take image
    * Move couch toward floor 10 cm, take image
    * Rotate couch 90 degrees, take image
    * Rotate couch back to home, take image
    * Rotate couch -90 degrees, take image

2. Gantry Angle Tracking
    * Set gantry to 0, take angle
    * Rotate gantry to 90 degrees, take angle
    * Rotate gantry to 180 degrees, take angle
    * Rotate gantry to 270 degrees, take angle

3. Collimator Angle Tracking
    * Set gantry to 270 degrees, set collimator to 0 degrees, take angle
    * Set collimator angle to 90 degrees, take angle
    * Set collimator angle to 0 degrees, take angle
    * Set collimator angle to -90 degrees, take angle

