# Usage: python extract_rat_contour.py -d videos -s 1000
# Note that contour 的格式是 [[x, y]]
import cv2
from glob import glob
import argparse
import json

# construct the argument parser
ap = argparse.ArgumentParser()
ap.add_argument('-d', '--directory', default='videos', help='path to the video files')
ap.add_argument('-s', '--step', default=100, type=int, help="detect and export rat contour every 's' frames")
args = vars(ap.parse_args())

class RatDetector(object):

    def detect_rat_contour(self, gray):

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        _, th = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        _, cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # find contour with the biggest area
        self.rat_cnt = sorted(cnts, key=cv2.contourArea)[-1]

        return self.rat_cnt

class VideoReader(object):

    def __init__(self, video_path):
        self.video_path = video_path
        self.__video__ = cv2.VideoCapture(self.video_path)
        self.width = int(self.__video__.get(3))
        self.height = int(self.__video__.get(4))
        self.fps = int(self.__video__.get(5))
        self.resolution = (self.width, self.height)
        self.total_frame = int(self.__video__.get(cv2.CAP_PROP_FRAME_COUNT))

    def set_frame(self, frame_index):
        self.__video__.set(cv2.CAP_PROP_POS_FRAMES, frame_index-1)
        ok, self.frame = self.__video__.read()
        return ok, self.frame


dirs = glob('%s/*.avi' % args['directory'])

print('Detecting rat contours from %s every %s frames', (dirs, args['step']))

rd = RatDetector()

for file_path in dirs:
    filename = "%s_rat_contour.json" % file_path.split('.avi')[0]
    video = VideoReader(video_path=file_path)
    contours = dict()
    frame_index = 1
    while True:
        ok, frame = video.set_frame(frame_index)
        if not ok:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        contour = rd.detect_rat_contour(gray)
        contours[frame_index] = contour.tolist()
        frame_index += args['step']
        if frame_index > video.total_frame:
            break
    # save rat contour
    with open(filename, 'a') as f:
        json.dump(contours, f)

    print('Saved rat contours into %s' % filename)
