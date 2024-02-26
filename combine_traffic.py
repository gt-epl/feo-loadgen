import argparse
import simpy
import random
import sys
import numpy as np
import os
import pandas as pd


parser = argparse.ArgumentParser(description="Federared Orchestration Simulation")
parser.add_argument("--dirname", type=str, nargs="?", default=200)
args = parser.parse_args()

allarr = []
for i in [0, 4, 6, 9]:
    arr = np.load(f'../loadgen/{args.dirname}/sfcabs-load-site{i}.npy')
    newarr = arr.cumsum()
    allarr.append(newarr)
    
finalarr = np.concatenate(allarr)
finalarr.sort()
arr2 = np.diff(finalarr)
np.save(f'../loadgen/{args.dirname}/sfcabs-load-site_r.npy', arr2) 