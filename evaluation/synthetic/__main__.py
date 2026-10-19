import argparse
from pathlib import Path

from evaluation.synthetic.generator import DEFAULT_SEED, write_dataset

parser = argparse.ArgumentParser(description="Genera datos SINTÉTICOS de ejemplo (semilla fija).")
parser.add_argument("--out", type=Path, default=Path("evaluation/synthetic/muestras"))
parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
args = parser.parse_args()
for path in write_dataset(args.out, args.seed):
    print(path)
