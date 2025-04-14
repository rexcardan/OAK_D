# QA Cam - Proposed Architecture

## 1. Overview

This document outlines a refined architecture for the QA Cam library, building upon the initial concepts in `overview.md`. The goal is to create a modular and maintainable structure by grouping functionalities into distinct components.

## 2. Core Components

The library can be structured into the following main components:

*   **`CameraHandler`**: Responsible for direct interaction with the OAK-D Lite camera using the `depthai` Python library.
    *   Initializing the device.
    *   Acquiring synchronized RGB and Depth frames.
    *   Accessing IMU (accelerometer/gyroscope) data.
    *   Lower-level ArUco pattern detection within a given frame (can be called by other modules).
*   **`Calibration`**: Manages camera calibration.
    *   Orchestrates the calibration process using a known pattern.
    *   Calculates intrinsic and extrinsic parameters.
    *   Loads and saves calibration parameters persistently.
*   **`PatternUtils`**: Utility functions related to ArUco patterns.
    *   Generating printable ArUco pattern images based on specified parameters (size, number of codes, etc.).
*   **`Tracking`**: Handles the state and logic for tracking the pattern's pose over time.
    *   Setting a reference ("home") pose using the pattern.
    *   Starting and stopping periodic pose detection.
    *   Storing timestamped pose data during a tracking session.
    *   Saving tracking data to a file (e.g., JSON).
*   **`QATests`**: Implements the specific QA test sequences.
    *   Contains methods for each test (Couch, Gantry Angle, Collimator Angle).
    *   Uses the `Tracking` module to acquire pose data during test steps.
    *   May include logic to compare measured positions/angles against expected values (though analysis might be separate).

## 3. Component Interaction Diagram

```mermaid
graph TD
    subgraph UserInterface[User Interface / Main Script]
        UI_Calibrate[Calibrate Camera]
        UI_Generate[Generate Pattern]
        UI_RunTest[Run QA Test]
    end

    subgraph QACamLibrary[QA Cam Library]
        subgraph CameraHandler[CameraHandler]
            CH_Init[__init__(device_info)]
            CH_GetFrames[get_rgbd_frames()]
            CH_GetIMU[get_imu_data()]
            CH_FindPattern[find_pattern(frame, pattern_params)]
        end

        subgraph Calibration[Calibration]
            C_Init[__init__(camera_handler)]
            C_Calibrate[calibrate(pattern_image)]
            C_LoadParams[load_parameters()]
            C_SaveParams[save_parameters(params)]
            C_Params[Calibration Parameters]
        end

        subgraph PatternUtils[PatternUtils]
            PU_Generate[generate_pattern(params)]
            PU_Params[Pattern Parameters]
        end

        subgraph Tracking[Tracking]
            T_Init[__init__(camera_handler, calibration_params)]
            T_SetRef[set_reference_pose()]
            T_Start[start_tracking(interval_s)]
            T_Stop[stop_tracking()]
            T_GetData[get_tracking_data()]
            T_SaveData[save_tracking_data(filepath)]
            T_RefPose[Reference Pose]
            T_TrackData[Tracking Data (Timestamped Poses)]
        end

        subgraph QATests[QATests]
            QT_Init[__init__(tracking_module)]
            QT_Couch[run_couch_test(steps)]
            QT_Gantry[run_gantry_test(angles)]
            QT_Collimator[run_collimator_test(angles)]
        end
    end

    UserInterface -- Uses --> QACamLibrary

    UI_Calibrate --> Calibration
    UI_Generate --> PatternUtils
    UI_RunTest --> QATests

    QATests -- Uses --> Tracking
    Tracking -- Uses --> CameraHandler
    Tracking -- Uses --> Calibration
    Calibration -- Uses --> CameraHandler
    CameraHandler -- Interacts with --> Hardware[OAK-D Camera Hardware]

    %% Data Flow
    PatternUtils --> PU_Params
    Calibration --> C_Params
    Tracking --> T_RefPose
    Tracking --> T_TrackData
```

## 4. Data Management

*   **Calibration Parameters**: Stored persistently (e.g., in a configuration file like YAML or JSON) and loaded by the `Calibration` module.
*   **Pattern Parameters**: Defined when generating or detecting patterns.
*   **Tracking Data**: Collected by the `Tracking` module, likely as a list of timestamped poses (position + orientation), and saved to a user-specified file (e.g., JSON).

## 5. Next Steps

*   Refine method signatures and data structures within each component.
*   Implement the core logic for each module.
*   Develop the user interface or main script to utilize the library components.