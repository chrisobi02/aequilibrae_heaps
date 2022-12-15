#!/usr/bin/env python3
import numpy as np
from argparse import ArgumentParser
import warnings
import sys
from typing import List



def validate(skim1, skim2, atol: float = 1e-01):
    """
    Detect discrepencies in the provided skims with a tolerance. Prints the
    relevant locations, number of unique values, and max absolute difference.
    """
    isclose = np.isclose(skim1, skim2, atol=atol)
    if isclose.all():
        return True
    else:
        loc = np.where(~isclose)
        for x, y in zip(*loc):
            print(f"{x}, {y}: {skim1[x, y]:.2f} != {skim2[x, y]:.2f}")
        print("[x, y: value1 != value2]")
        print(f"\nThe skims differ at {len(loc[0])} points")
        print(f"There are {len(np.unique(loc[0]))} unique x values", f"and {len(np.unique(loc[1]))} unique y values")
        print(f"The max absolute difference is {np.abs(skim1 - skim2).max()}\n\n")
        return False



if __name__ == "__main__":
    main()
