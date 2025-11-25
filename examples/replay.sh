/home/erkhovartem/miniconda3/envs/lerobot/bin/lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=follower_arm \
    --dataset.repo_id=${HF_USER}/record-test \
    --dataset.root=/home/erkhovartem/lerobot_datasets/record_test \
    --dataset.episode=7 # choose the episode you want to replay