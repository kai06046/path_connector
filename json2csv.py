# Usage: python json2csv.py -d videos
import json
import numpy as np
from glob import glob
import pandas as pd
import argparse

# construct the argument parser
ap = argparse.ArgumentParser()
ap.add_argument('-d', '--directory', default='videos', help='path to the json files')
args = vars(ap.parse_args())

dirs = [f for f in glob('%s/*.json' % args['directory']) if 'rat' not in f]
print('Converting ', dirs)
for file_path in dirs:
    file_name = file_path.split('.json')[0]

    with open(file_path, 'r') as f:
        data = json.load(f)

    df = {'name': [], 'nframe': [], 'x_center': [], 'y_center': [], 'width': [], 'height': []}
    for k in sorted(data.keys()):
        frame = data[k]['n_frame']
        paths = np.array(data[k]['path'])
        wh = np.array(data[k]['wh'])
        x, y = paths[:, 0].tolist(), paths[:, 1].tolist()
        w, h = wh[:, 0].tolist(), wh[:, 1].tolist()
        df['name'].extend([k]*len(frame))
        df['nframe'].extend(frame)
        df['x_center'].extend(x)
        df['y_center'].extend(y)
        df['width'].extend(w)
        df['height'].extend(h)
    df = pd.DataFrame(df)
    df = df.reindex_axis(['name', 'nframe', 'x_center', 'y_center', 'width', 'height'], axis=1)
    df.to_csv(file_name+'.csv', index=False)
    
    print('Done ', file_path)
