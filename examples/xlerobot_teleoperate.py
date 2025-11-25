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

from lerobot.processor import make_default_processors

from lerobot.robots.so101_follower.config_so101_follower import SO101FollowerConfig

from lerobot.robots.so101_follower.so101_follower import SO101Follower
from lerobot.teleoperators.so101_leader.config_so101_leader import SO101LeaderConfig
from lerobot.teleoperators.so101_leader.so101_leader import SO101Leader
from lerobot.robots.xlerobot import XLerobotClientConfig, XLerobotClient
from lerobot.utils.robot_utils import busy_wait
from lerobot.utils.visualization_utils import init_rerun, log_rerun_data

FPS = 30

# Initialize the robot and teleoperator config
# follower_config = SO101FollowerConfig(
#     port="/dev/ttyACM0", id="follower_arm")
follower_config = XLerobotClientConfig(remote_ip = '10.16.116.33')

leader_config = SO101LeaderConfig(port="/dev/ttyACM1", id="leader_arm")


# Initialize the robot and teleoperator
# follower = SO101Follower(follower_config)
leader = SO101Leader(leader_config)
follower = XLerobotClient(follower_config)
teleop_action_processor, robot_action_processor, robot_observation_processor = make_default_processors()

# Connect to the robot and teleoperator
follower.connect()
leader.connect()

# Init rerun viewer
# init_rerun(session_name="so100_so100_EE_teleop")

print("Starting teleop loop...")
while True:
    t0 = time.perf_counter()

    obs = follower.get_observation()

    # Get teleop action
    action = leader.get_action()
    action = {f"left_arm_{k}": v for k, v in action.items()}
    action["head_motor_1.pos"] = 0.
    action["head_motor_2.pos"] = 0.

    # Send processed action to robot (robot_action_processor.to_output should return dict[str, Any])
    _ = follower.send_action(action)

    # Visualize
    # log_rerun_data(observation=leader_ee_act, action=follower_joints_act)

    busy_wait(max(1.0 / FPS - (time.perf_counter() - t0), 0.0))
