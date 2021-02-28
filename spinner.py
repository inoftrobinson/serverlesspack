"""
NOT CURRENTLY USED : COPIED FROM https://github.com/tqdm/tqdm/issues/1131
"""

from tqdm import trange
from time import sleep

# Number of columns in the middle part of the process bar
pbar_cols = 10
halfspins = 3
# Sequence of symbols for animation of each column in the process bar
animation = "".join(("·", r"/-\|" * halfspins, "#"))
fps = 8
params = dict((
    ("ascii", animation),
    ("bar_format", r"{percentage:3.0f}% {bar} {remaining}"),
    ("ncols", pbar_cols + 11), # 11 is the number of other characters around the process bar
    ))
for it in trange(pbar_cols * len(animation), **params):
    if it % len(animation) == 0:
        continue
    sleep(1 / fps)
