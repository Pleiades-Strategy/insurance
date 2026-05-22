"""
CLI for training the multi-label bill classifier.
Usage:
    python cli/train.py
    python cli/train.py --test-size 0.3
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tagging.classifier import train_classifier


def main():
    parser = argparse.ArgumentParser(description="Train multi-label bill classifier on tagged bills.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction of data for testing (default: 0.2)")
    args = parser.parse_args()

    model, mlb = train_classifier(test_size=args.test_size)
    if model:
        print("\nTraining complete. Model saved to model/bill_classifier.pkl")
    else:
        print("\nTraining failed — not enough labeled data.")


if __name__ == "__main__":
    main()
