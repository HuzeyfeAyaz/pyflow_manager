import argparse
# import time
# time.sleep(10)  # Open to simulate a long running task

args = argparse.ArgumentParser()
args.add_argument('--output', type=str, required=True)

args = args.parse_args()

with open(args.output, 'w') as f:
    f.write('Hello, world!\n')
