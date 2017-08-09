import pywt._extensions._cwt
from scipy.linalg import _fblas
import scipy.spatial.ckdtree
import sys
import argparse
import tkinter as tk

from src.path_connector import PathConnector

parser = argparse.ArgumentParser(description='Some arguement for path connector')
parser.add_argument('-m', '--max', type=int, default=500, help='maximum frame for displaying path')
parser.add_argument('-t', '--tolerance', type=int, default=38, help='maximum tolerance of distance')
args = vars(parser.parse_args())

if __name__ == '__main__':
    pc = PathConnector(args['max'], args['tolerance'])
    pc.start()