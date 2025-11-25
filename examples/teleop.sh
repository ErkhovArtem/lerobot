lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=follower_arm \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM2 \
    --teleop.id=leader_arm \
    # --display_data=true \
    # --robot.cameras="{ SideLeft: {type: opencv, index_or_path: /dev/video2, width: 640, height: 480, fps: 30},
    # Wrist: {type: opencv, index_or_path: /dev/video4, width: 640, height: 480, fps: 30}}" \

