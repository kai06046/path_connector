import cv2
import numpy as np
from PIL import Image, ImageTk

LENGTH_ARROW = 20

class Utils(object):

    def draw(self, tup=None):

        results_dict = self.results_dict if not self.is_manual else self.tmp_results_dict
        # draw connected paths
        for i, k in enumerate(sorted([k for k, v in self.object_name.items() if v['on']])):
            # if not self.is_manual:
            pts = np.array(results_dict[k]['path'])
            flag = results_dict[k]['n_frame']
            # else:
            #     pts = np.array(results_dict[k]['path'])
            #     flag = results_dict[k]['n_frame']

            color = self.color[self.object_name[k]['ind']]

            try:
                ind = flag.index(self.n_frame)
            except:
                ind = None

            if ind is not None:
                width = 5
                if ind != 0:
                    last_pt = tuple(pts[ind - 1])
                else:
                    last_pt = tuple(pts[ind])
                pt = tuple(pts[ind])
                tri_pts = tri(pt)
                # draw path end point triangle
                cv2.polylines(self._frame, tri_pts, True, color, 4)
                # position of text info
                if last_pt[1] > pt[1]:
                    cv2.putText(self._frame, self.object_name[k]['display_name'], (pt[0] - 25, pt[1] - 15), cv2.FONT_HERSHEY_TRIPLEX, 0.8, color, 1)
                else:
                    cv2.putText(self._frame, self.object_name[k]['display_name'], (pt[0] + 15, pt[1] + 25), cv2.FONT_HERSHEY_TRIPLEX, 0.8, color, 1)
            else:
                try:
                    last_pt = tuple(pts[-2])
                except:
                    last_pt = tuple(pts[-1])
                pt = tuple(pts[-1])
                tri_pts = tri(pt)
                # draw path end point triangle
                cv2.polylines(self._frame, tri_pts, True, color, 1)
                # position of text info
                if last_pt[1] > pt[1]:
                    cv2.putText(self._frame, self.object_name[k]['display_name'], (pt[0] - 25, pt[1] - 15), cv2.FONT_HERSHEY_TRIPLEX, 0.8, color, 1)
                else:
                    cv2.putText(self._frame, self.object_name[k]['display_name'], (pt[0] + 15, pt[1] + 25), cv2.FONT_HERSHEY_TRIPLEX, 0.8, color, 1)

            if self.check_show_drawing is None or self.check_show_drawing.get() == 1:
                # show until current if ind is not None
                # pts = pts[-self.maximum:ind]
                pts = pts[-self.maximum:(ind + 1) if ind is not None else None]
                if len(pts) > 0:
                    # start point
                    cv2.circle(self._frame, tuple(pts[0]), 10, color, 1)
                    cv2.circle(self._frame, tuple(pts[0]), 13, color, 1)

                    for i in range(1, len(pts)):
                        p1 = pts[i-1]
                        p2 = pts[i]
                        dist = np.linalg.norm(p1 - p2)
                        # draw dotted line
                        if dist < 48:
                            cv2.line(self._frame, tuple(p1), tuple(p2), color, 1)
                        else:
                            drawline(self._frame, tuple(p1), tuple(p2), color, 1, style='dotted', gap=7)
                        # draw arrow
                        if i % 6 == 0:
                            if self.check_show_arrow is not None and self.check_show_arrow.get() == 1:
                                if dist > 3:
                                    draw_arrow(self._frame, tuple(p1), tuple(p2), color, dist=dist, thickness=2, line_type=16)
                else:
                    pass
                    # print(ind)
                    # pts = pts.reshape((-1, 1, 2))
                    # cv2.polylines(self._frame, [pts], False, color)

        # draw coordinate (stop point) that needed to be assigned
        if self.current_pts is not None:
            p, nframe = self.current_pts, self.current_pts_n
            color = (50, 50, 255)
            x, y = p
            thickness = 2 if nframe == self.n_frame else 1
            cv2.circle(self._frame, p, 15, color, thickness)
            cv2.putText(self._frame, '?', (x - 9, y + 9), cv2.FONT_HERSHEY_TRIPLEX, 0.8, color, thickness)

        # draw YOLO bounding boxes
        if self.check_show_yolo is None or self.check_show_yolo.get() == 1:
            _, boxes = eval(self.__yolo_results__[self.n_frame - 1])

            for b in boxes:
                ymin, xmin, ymax, xmax, score = b
                x_c = int((xmin+xmax) / 2 + 0.5)
                y_c = int((ymin+ymax) / 2 + 0.5)

                p1, p2 = (int(xmin), int(ymin)), (int(xmax), int(ymax))

                color = None
                # find corresponding color of YOLO bounding boxes
                for k in sorted([k for k, v in self.object_name.items() if v['on']]):
                    pts = results_dict[k]['path']
                    flag = results_dict[k]['n_frame']
                    ind = None                    
                    try:
                        ind = flag.index(self.n_frame)
                    except:
                        pass

                    if ind is not None:
                        if pts[ind] == (x_c, y_c):
                            color = self.color[self.object_name[k]['ind']]
                            break
                if color:
                    cv2.rectangle(self._frame, p1, p2, color, 1)
                else:
                    cv2.rectangle(self._frame, p1, p2, (0, 255, 255), 1)

        # remove drawing on specific region
        n = 60
        e = 100
        if self.clear and self.check_is_clear.get() == 1:
            x, y = self.mv_x, self.mv_y
            xmin, xmax = max(0, (x-n)), min((x+n), self.width)
            ymin, ymax = max(0, (y-n)), min((y+n), self.height)
            self._frame[ymin:ymax, xmin:xmax] = self._orig_frame[ymin:ymax, xmin:xmax].copy()
            drawrect(self._frame, (xmin, ymin), (xmax, ymax), (0, 255, 255), 1, style='dotted')
            if not (x >= (self.last_x - e) and x <= (self.last_x + e) and y >= (self.last_y - e) and  y <= (self.last_y + e)):
                self.clear = False

        # draw status
        if not self.is_manual:
            if self.stop_n_frame == self.n_frame:
                cv2.putText(self._frame, 'Label', (30, 30), cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 255), 1)
            elif self.stop_n_frame > self.n_frame:
                cv2.putText(self._frame, 'Pre-Label', (30, 30), cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 255), 1)
            elif self.stop_n_frame < self.n_frame:
                cv2.putText(self._frame, 'Post-Label', (30, 30), cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 255), 1)
        else:
            cv2.putText(self._frame, 'Manual Label', (30, 30), cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 255), 1)
            # color = self.color[self.label_ind - 1]
            # if self.stop_n_frame == self.n_frame:
            #     cv2.putText(self._frame, 'Manual Label', (30, 30), cv2.FONT_HERSHEY_TRIPLEX, 1, color, 1)
            # elif self.stop_n_frame > self.n_frame:
            #     cv2.putText(self._frame, 'Manual Pre-Label', (30, 30), cv2.FONT_HERSHEY_TRIPLEX, 1, color, 1)
            # elif self.stop_n_frame < self.n_frame:
            #     cv2.putText(self._frame, 'Manual Post-Label', (30, 30), cv2.FONT_HERSHEY_TRIPLEX, 1, color, 1)

            # # draw label results
            # for k, v in self.label_dict.items():
            #     try:
            #         color = self.color[self.object_name[k]['ind']]
            #     except:
            #         color = self.color[-1]

            #     flag = v['n_frame']
            #     pts = v['path']

            #     # current frame label
            #     try:
            #         ind = flag.index(self.n_frame)
            #         p = pts[ind]
            #         cv2.circle(self._frame, p, 3, color, 2)
            #     except:
            #         ind = None

            #     # label history
            #     for i, p in enumerate(pts):
            #         if i != ind:
            #             cv2.circle(self._frame, p, 3, color, 1)

        # draw manual label paths
        if len(self.tmp_line) > 1:
            color = (255, 255, 255)
            for i in range(1, len(self.tmp_line)):
                cv2.line(self._frame, self.tmp_line[i - 1], self.tmp_line[i], color, 2)

        # convert frame into rgb
        self._frame = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)

    def draw_legend(self):
        shape = (40, 40, 3)
        c = (20, 20)
        fg = (0, 0, 0)
        color = (50, 50, 255)

        # origin
        self.legend_1 = np.ones(shape, dtype='uint8') * 255
        cv2.circle(self.legend_1, c, 10, fg, 1)
        cv2.circle(self.legend_1, c, 13, fg, 1)
        self.legend_1 = cv2.cvtColor(self.legend_1, cv2.COLOR_BGR2RGB)

        # to be decided
        self.legend_2 = np.ones(shape, dtype='uint8') * 255
        cv2.circle(self.legend_2, c, 15, color, 1)
        cv2.putText(self.legend_2, '?', (20 - 8, 20 + 9), cv2.FONT_HERSHEY_TRIPLEX, 0.8, color, 1)
        self.legend_2 = cv2.cvtColor(self.legend_2, cv2.COLOR_BGR2RGB)

        # current location
        self.legend_3 = np.ones(shape, dtype='uint8') * 255
        tri_pts = tri(c)
        cv2.polylines(self.legend_3, tri_pts, True, fg, 3)

        # last detected location
        self.legend_4 = np.ones(shape, dtype='uint8') * 255
        tri_pts = tri(c)
        cv2.polylines(self.legend_4, tri_pts, True, fg, 1)

class Common(object):

    # see if a points is inside a circle
    def in_circle(self, pt, center, radius=10):
        x, y = pt
        x_c, y_c = center
        dx, dy = (x - x_c)**2, (y - y_c)**2
        if dx + dy <= radius**2:
            return True
        else:
            return False

    # see if a points is inside a rectangle
    def in_rect(pt, rect):  
        x_condition = pt[0] > rect[0][0] and pt[0] < rect[1][0]
        y_condition = pt[1] > rect[0][1] and pt[1] < rect[1][1]
        
        if x_condition and y_condition:
            return True
        else:
            return False
    # center a tkinter window
    def center(self, win):
        win.update_idletasks()
        width = win.winfo_reqwidth()
        height = win.winfo_reqheight()
        x = (win.winfo_screenwidth() // 2.25) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry('+%d+%d' % (x, y))

# return a triangle with pt as center
def tri(pt):
    x, y = pt
    x1 = 13
    y1 = 13
    return [np.array([(x-x1, y+y1), (x+x1, y+y1), (x, y-y1)]).reshape((-1, 1, 2))]

def drawline(img,pt1,pt2,color,thickness=1,style='dotted',gap=15):
    dist =((pt1[0]-pt2[0])**2+(pt1[1]-pt2[1])**2)**.5
    pts= []
    for i in  np.arange(0,dist,gap):
        r=i/dist
        x=int((pt1[0]*(1-r)+pt2[0]*r)+.5)
        y=int((pt1[1]*(1-r)+pt2[1]*r)+.5)
        p = (x,y)
        pts.append(p)

    if style=='dotted':
        for p in pts:
            cv2.circle(img,p,thickness,color,-1)
    else:
        s=pts[0]
        e=pts[0]
        i=0
        for p in pts:
            s=e
            e=p
            if i%2==1:
                cv2.line(img,s,e,color,thickness)
            i+=1

def drawpoly(img,pts,color,thickness=1,style='dotted',):
    s=pts[0]
    e=pts[0]
    pts.append(pts.pop(0))
    for p in pts:
        s=e
        e=p
        drawline(img,s,e,color,thickness,style)

def drawrect(img,pt1,pt2,color,thickness=1,style='dotted'):
    pts = [pt1,(pt2[0],pt1[1]),pt2,(pt1[0],pt2[1])] 
    drawpoly(img,pts,color,thickness,style)

def draw_arrow(image, p, q, color, dist, arrow_magnitude=9, thickness=1, line_type=8, shift=0):
# adapted from http://mlikihazar.blogspot.com.au/2013/02/draw-arrow-opencv.html
    
    if dist > 48:
    # draw arrow tail
        drawline(image, p, q, color, thickness, gap=7)
    else:
        cv2.line(image, p, q, color, thickness, line_type, shift)

    # calc angle of the arrow 
    angle = np.arctan2(p[1]-q[1], p[0]-q[0])
    # starting point of first line of arrow head 
    p = (int(q[0] + arrow_magnitude * np.cos(angle + np.pi/4)),
    int(q[1] + arrow_magnitude * np.sin(angle + np.pi/4)))
    # draw first half of arrow head
    cv2.line(image, p, q, color, thickness, line_type, shift)
    # starting point of second line of arrow head 
    p = (int(q[0] + arrow_magnitude * np.cos(angle - np.pi/4)),
    int(q[1] + arrow_magnitude * np.sin(angle - np.pi/4)))
    # draw second half of arrow head
    cv2.line(image, p, q, color, thickness, line_type, shift)