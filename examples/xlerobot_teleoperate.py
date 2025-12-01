# !/usr/bin/env python

# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import numpy as np

from lerobot.processor import make_default_processors

from lerobot.teleoperators.bi_so100_leader.config_bi_so100_leader import BiSO100LeaderConfig
from lerobot.teleoperators.bi_so100_leader.bi_so100_leader import BiSO100Leader
from lerobot.teleoperators.keyboard.teleop_keyboard import KeyboardTeleop, KeyboardTeleopConfig
from lerobot.robots.xlerobot import XLerobotClientConfig, XLerobotClient
from lerobot.utils.robot_utils import busy_wait
from lerobot.utils.visualization_utils import init_rerun, log_rerun_data
from lerobot.cameras.configs import CameraConfig, Cv2Rotation, ColorMode
from lerobot.cameras.realsense import RealSenseCamera, RealSenseCameraConfig

from phone_server import PhoneServer

FPS = 30

# Initialize the robot and teleoperator config

camera_config = {
            "head": RealSenseCameraConfig(
            serial_number_or_name="141722076677",  # Replace with camera SN
            fps=30,
            width=1280,
            height=720,
            color_mode=ColorMode.BGR, # Request BGR output
            rotation=Cv2Rotation.NO_ROTATION,
            use_depth=False
        )
}

def transform_arm_keys(original_dict: dict) -> dict:
    """
    Преобразует ключи формата left_* и right_* в left_arm_* и right_arm_*
    """
    transformed = {}
    
    for key, value in original_dict.items():
        if key.startswith('left_'):
            new_key = key.replace('left_', 'left_arm_', 1)
        elif key.startswith('right_'):
            new_key = key.replace('right_', 'right_arm_', 1)
        else:
            new_key = key  # Оставляем без изменений
            
        transformed[new_key] = value
    
    return transformed

follower_config = XLerobotClientConfig(remote_ip = '10.16.116.39', cameras=camera_config)

leader_config = BiSO100LeaderConfig(left_arm_port="/dev/ttyACM0", right_arm_port="/dev/ttyACM1", id="leader_arm")

# Initialize the robot and teleoperator
leader = BiSO100Leader(leader_config)
follower = XLerobotClient(follower_config)
headset_server = PhoneServer()

#Init the keyboard instance
keyboard_config = KeyboardTeleopConfig()
keyboard = KeyboardTeleop(keyboard_config)
keyboard.connect()

# Connect to the robot and teleoperator
follower.connect()
leader.connect()
headset_server.run()

# Init rerun viewer
# init_rerun(session_name="so100_so100_EE_teleop")

print("Starting teleop loop...")
while True:
    t0 = time.perf_counter()

    obs = follower.get_observation()
    headset_server.update_frame(obs['head'])

    # Get teleop action
    action = leader.get_action()
    action = transform_arm_keys(action)
    head_action = headset_server.get_angles()
    action["head_motor_1.pos"] = head_action['yaw'] + follower.head_base_pose["head_motor_1.pos"]
    action["head_motor_2.pos"] = head_action['roll'] + follower.head_base_pose["head_motor_2.pos"]
    # action["head_motor_1.pos"] = 0.
    # action["head_motor_2.pos"] = 0.

    pressed_keys = set(keyboard.get_action().keys())
    keyboard_keys = np.array(list(pressed_keys))
    base_action = follower._from_keyboard_to_base_action(keyboard_keys) or {}
    # base_action = {"x.vel": 0.,
    #             "y.vel": 0.,
    #             "theta.vel": 0.}
    action = {**action, **base_action}
    
    # Send processed action to robot (robot_action_processor.to_output should return dict[str, Any])
    _ = follower.send_action(action)
    # Visualize
    # log_rerun_data(observation=leader_ee_act, action=follower_joints_act)

    busy_wait(max(1.0 / FPS - (time.perf_counter() - t0), 0.0))
