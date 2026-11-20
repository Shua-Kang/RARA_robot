"""Turn the raw rollout videos in videos/ (not published) into web videos in static/videos/.

Real robot: the 1280x720 global view is cropped to a 720x720 square (left cables and right empty table
removed), the 640x480 gripper view to a 480x480 square, and the gripper view is inset at the bottom right.
More real-robot rollouts: the 640x480 front view is kept whole, with the wrist view inset at the top right.
RoboTwin: the 23-px burned-in label bar at the top is cropped; labels are shown on the page instead.

Run from the repository root:  python tools/process_videos.py [real] [real_more] [robotwin] [robocasa]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'videos'
OUT = ROOT / 'static' / 'videos'
ENC = ['-c:v', 'libx264', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an']

# (raw stem relative to videos/real, output name). Episodes are paired by their initial scene.
REAL = [
    ('BlindVLA/pick_3_toys_20', 'toys_blindvla_1'),          # table with cloth
    ('RARA/pick_3_toys_19', 'toys_rara_1'),
    ('BlindVLA/pick_3_toys_21_failure', 'toys_blindvla_2'),  # lion in front
    ('RARA/pick_3_toys_20_success', 'toys_rara_2'),
    ('BlindVLA/pick_3_toys_26_failure', 'toys_blindvla_3'),  # zebra and monkey
    ('RARA/pick_3_toys_25_success', 'toys_rara_3'),
    ('BlindVLA/toaster_04', 'toaster_blindvla_1'),
    ('RARA/toaster_05', 'toaster_rara_1'),
]

# More RARA rollouts on the real robot (640x480 front and wrist cameras, recorded 2026-11-20):
# (raw folder under videos/real/rollouts_2026_11_20, output name, start s, end s or None).
REAL_MORE_RAW = 'rollouts_2026_11_20'
REAL_MORE = [
    ('toy_01', 'toys_1', 0, None),
    ('toy_02', 'toys_2', 0, None),
    ('toy_03', 'toys_3', 0, None),
    ('toaster_01', 'toaster_1', 0, None),
    ('toaster_02', 'toaster_2', 0, 12.0),     # the gripper closes again on nothing after 12 s
    ('toaster_03', 'toaster_3', 1.7, None),   # a hand adjusts the toaster in the first 1.5 s
    ('toaster_04', 'toaster_4', 0, None),
    ('lid_01_black', 'lid_1', 0, None),
    ('lid_02_gray', 'lid_2', 0, None),
    ('lid_03_green', 'lid_3', 0, None),
    ('lid_04_red', 'lid_4', 0, None),
    ('lid_05_white', 'lid_5', 0, None),
]

ROBOTWIN_TASKS = {'env200005_e300': 'click_alarm_clock', 'env300008_e300': 'move_pill_bottle'}
ROBOTWIN_METHODS = {'1_FT_fail': 'ft', '2_CoFT_fail': 'coft', '3_BlindVLA_fail': 'blindvla',
                    '4_STRAP-FT_fail': 'strap', '5_RARA-anchor_success': 'rara'}


ROBOCASA_TASKS = {'OpenBlenderLid': 'open_blender_lid', 'OpenCabinet': 'open_cabinet',
                  'PickPlaceCounterToDrawer': 'pick_place_drawer', 'TurnOnToaster': 'turn_on_toaster'}
ROBOCASA_METHODS = {'1_FT': 'ft', '2_BlindVLA': 'blindvla', '3_RARA': 'rara'}
ROBOCASA_EPISODES = 3  # first episodes (by seed) of each task and split


def run(args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + args, check=True)


def real():
    (OUT / 'real').mkdir(parents=True, exist_ok=True)
    graph = ('[0:v]crop=720:720:220:0,scale=540:540[g];'
             '[1:v]crop=480:480:80:0,scale=164:164,pad=170:170:3:3:white[r];'
             '[g][r]overlay=W-w-12:H-h-12:shortest=1')
    for stem, name in REAL:
        dst = OUT / 'real' / f'{name}.mp4'
        missing = [k for k in ('global', 'gripper') if not (RAW / 'real' / f'{stem}_{k}.mp4').exists()]
        if missing:
            print('SKIP', stem, '- missing', ', '.join(missing))
            continue
        run(['-i', str(RAW / 'real' / f'{stem}_global.mp4'), '-i', str(RAW / 'real' / f'{stem}_gripper.mp4'),
             '-filter_complex', graph, '-r', '30', '-crf', '26'] + ENC + [str(dst)])
        print(dst.relative_to(ROOT), dst.stat().st_size // 1024, 'KB')


def real_more():
    """Front view at full 640x480, with the wrist view (center 480x480 square) inset at the top right,
    where the front view only shows the background."""
    (OUT / 'real_more').mkdir(parents=True, exist_ok=True)
    graph = ('[1:v]crop=480:480:80:0,scale=150:150,pad=156:156:3:3:white[r];'
             '[0:v][r]overlay=W-w-10:10:shortest=1')
    for folder, name, start, end in REAL_MORE:
        src = RAW / 'real' / REAL_MORE_RAW / folder
        dst = OUT / 'real_more' / f'{name}.mp4'
        trim = ['-ss', str(start)] + (['-to', str(end)] if end is not None else [])
        run(trim + ['-i', str(src / 'front.mp4')] + trim + ['-i', str(src / 'wrist.mp4'),
            '-filter_complex', graph, '-r', '30', '-crf', '26'] + ENC + [str(dst)])
        print(dst.relative_to(ROOT), dst.stat().st_size // 1024, 'KB')


def robotwin():
    (OUT / 'robotwin').mkdir(parents=True, exist_ok=True)
    for env, task in ROBOTWIN_TASKS.items():
        for raw, method in ROBOTWIN_METHODS.items():
            dst = OUT / 'robotwin' / f'{task}_{method}.mp4'
            run(['-i', str(RAW / 'RoboTwin' / env / f'{raw}.mp4'),
                 '-vf', 'crop=640:456:0:24,scale=480:-2', '-crf', '28'] + ENC + [str(dst)])
            print(dst.relative_to(ROOT), dst.stat().st_size // 1024, 'KB')


def robocasa():
    (OUT / 'robocasa').mkdir(parents=True, exist_ok=True)
    for raw_task, task in ROBOCASA_TASKS.items():
        for split in ('ID', 'OOD'):
            episodes = sorted((RAW / 'robocasa' / raw_task / split).iterdir())[:ROBOCASA_EPISODES]
            for ep, folder in enumerate(episodes, start=1):
                for raw_prefix, method in ROBOCASA_METHODS.items():
                    src = next(folder.glob(f'{raw_prefix}_*.mp4'))
                    dst = OUT / 'robocasa' / f'{task}_{split.lower()}_{ep}_{method}.mp4'
                    run(['-i', str(src), '-vf', 'scale=384:384', '-crf', '28'] + ENC + [str(dst)])
                print(task, split, ep, folder.name)


if __name__ == '__main__':
    # Optional arguments pick the groups to process, e.g. "python tools/process_videos.py real_more".
    groups = {'real': real, 'real_more': real_more, 'robotwin': robotwin, 'robocasa': robocasa}
    for group in sys.argv[1:] or groups:
        groups[group]()
