${HOME}/miniconda3/envs/lerobot/bin/lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=follower_arm \
    --robot.cameras="{ SideLeft: {type: opencv, index_or_path: /dev/video2, width: 640, height: 480, fps: 30},
    Wrist: {type: opencv, index_or_path: /dev/video4, width: 640, height: 480, fps: 30}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=leader_arm \
    --display_data=true \
    --dataset.root=${HOME}/lerobot_datasets/Toy2Can \
    --dataset.repo_id=${HF_USER}/Toy2Can \
    --dataset.num_episodes=100 \
    --dataset.single_task="Grab the toy bucket of popcorn and place it in a tabletop trash can." \
    --dataset.push_to_hub=False \
    --dataset.episode_time_s=30 \
    --dataset.reset_time_s=20 \
    --resume=true