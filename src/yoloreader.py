import numpy as np
import cv2
import copy
from PIL import Image, ImageTk

# from mahotas.features import haralick, zernike
# from skimage.feature import hog, local_binary_pattern
from skimage.measure import compare_ssim

letter = [chr(i) for i in range(ord('a'), ord('z')+1)]
N_SHOW = 20

# threshold
THRES_FORWARD_DIST = 30
THRES_FORWARD_N_MAX = 30
THRES_FORWARD_N = 10
THRES_NEAR_DIST = 80 # for pass false positive

THRES_NEAR_DIST_NOT_ASSIGN = 48 # for append if very near not assigned key
THRES_NOT_ASSIGN_FORWARD_N_MAX = 100
THRES_NOT_ASSIGN_FORWARD_DIST = 35
THRES_NOT_ASSIGN_FORWARD_N = 10
THRES_NOT_ASSIGN_FP_DIST = 20

class YOLOReader(object):

    def read_yolo_result(self):
        # yolo_results_path = 'testing_0928.txt'
        yolo_results_path = self.video_path.split('.avi')[0] + '.txt'
        with open(yolo_results_path, 'r') as f:
            lines = f.readlines()
        return lines

    def calculate_path(self, ind=None, n_show=N_SHOW):
        """
        A algorithm that connects YOLO bounding info as continuous bounding box
        -----------------------------------------------------------------------
        ind: run this function start from ind-th frames
        n_show: records every n_show for displaying tracked results
        """
        n_key_used = len(self.object_name.keys())
        
        self.is_calculate = True
        n_frame = ind if ind is not None else self.n_frame
        print('calculate_path %s' % n_frame)
        undone_pts = []
        self.suggest_ind = []

        while self.is_calculate:
            # self.root.update_idletasks()
            nframe, boxes = eval(self.__yolo_results__[n_frame - 1])
            assert nframe == n_frame
            boxes = np.array(boxes)

            # append history manual label result
            label_ind = [k for k, v in self.label_dict.items() if n_frame in v['n_frame']]
            for k in label_ind:
                i = self.label_dict[k]['n_frame'].index(n_frame)
                self.results_dict[k]['n_frame'].append(n_frame)
                self.results_dict[k]['path'].append(self.label_dict[k]['path'][i])

            # initiate frame for recording animation
            if n_frame % n_show == 0:
                self.update_frame(n_frame)
            if len(boxes) > 0:
                self.dist_records[n_frame] = dict()

                on_keys = [k for k, v in self.object_name.items() if v['on']]

                for i, box in enumerate(boxes):
                    ymin, xmin, ymax, xmax, score = box
                    x_c = int((xmin+xmax) / 2 + 0.5)
                    y_c = int((ymin+ymax) / 2 + 0.5)
                    p = (x_c, y_c)
                    # if there is no keys, initiate
                    if n_key_used == 0 or n_frame == 1:
                        temp = 0
                        forward_points = [eval(self.__yolo_results__[i])[1] for i in range(n_frame, n_frame + THRES_FORWARD_N_MAX)]
                        p_tmp = p
                        for i, res in enumerate(forward_points):
                            min_dist = 99999
                            for b in res:
                                ymin, xmin, ymax, xmax, score = b
                                x_c = int((xmin+xmax) / 2 + 0.5)
                                y_c = int((ymin+ymax) / 2 + 0.5)
                                p_forward = (x_c, y_c)
                                dist = np.linalg.norm(np.array(p_forward) - np.array(p_tmp))
                                if dist <= min(THRES_FORWARD_DIST, min_dist):
                                    min_dist = dist
                                    p_tmp = p_forward
                            if min_dist < THRES_FORWARD_DIST:
                                temp += 1

                        # if was connected 10 frames in next 30 frames
                        if temp > THRES_FORWARD_N:
                            # append first point to results
                            chrac = letter[n_key_used]
                            self.results_dict[chrac] = dict()
                            self.results_dict[chrac]['path'] = [p]
                            self.results_dict[chrac]['n_frame'] = [n_frame]

                            self.object_name[chrac] = {'ind': n_key_used, 'on': True, 'display_name': chrac}
                            n_key_used += 1

                            # record distance history
                            self.dist_records[n_frame][chrac] = dict()
                            self.dist_records[n_frame][chrac]['dist'] = [0]
                            self.dist_records[n_frame][chrac]['center'] = [p]
                            self.dist_records[n_frame][chrac]['below_tol'] = [True]

                    else:
                        # record all distance history first
                        for i, k in enumerate(on_keys):
                            v = self.results_dict[k]['path']
                            dist = np.linalg.norm(np.array(v[-1]) - np.array(p))

                            if k not in self.dist_records[n_frame].keys():
                                self.dist_records[n_frame][k] = dict()
                                self.dist_records[n_frame][k]['dist'] = [dist]
                                self.dist_records[n_frame][k]['center'] = [p]
                                self.dist_records[n_frame][k]['below_tol'] = [True if dist <= self.tol else False]
                            else:
                                self.dist_records[n_frame][k]['dist'].append(dist)
                                self.dist_records[n_frame][k]['center'].append(p)
                                self.dist_records[n_frame][k]['below_tol'].append(True if dist <= self.tol else False)

                # start judgement
                tmp_dist_record = copy.deepcopy(self.dist_records[n_frame])
                # sorted dist index by dist
                sorted_indexes = {k: sorted(range(len(v['dist'])), key=lambda k: v['dist'][k]) for k, v in tmp_dist_record.items()}
                hit_condi = [(k, sorted_indexes[k][0]) for k in on_keys if tmp_dist_record[k]['below_tol'][sorted_indexes[k][0]]]
                
                # if n_frame > 450 and n_frame < 455:
                #     print(n_frame)
                #     print(tmp_dist_record)

                # the easiest part: the length of hit_condi is same as the number of objects
                if n_frame == 1:
                    pass
                elif len(set([v[1] for v in hit_condi])) == len(on_keys):

                	# pending assessment
                    for k, ind in hit_condi:
                        if k not in label_ind:
                            self.results_dict[k]['path'].append(tmp_dist_record[k]['center'][ind])
                            self.results_dict[k]['n_frame'].append(n_frame)
                # the length of hit_condi is same as the number of nearest indexes
                elif len(set([v for k, v in hit_condi])) == len(hit_condi):

                	# pending, assessment
                    for k, ind in hit_condi:
                        if k not in label_ind:
                            self.results_dict[k]['path'].append(tmp_dist_record[k]['center'][ind])
                            self.results_dict[k]['n_frame'].append(n_frame)
                    # a boxes was assigned to multi object, choose the nearest one
                    # else:
                    #     print('multi')
                    #     print(tmp_dist_record)
                    #     print(hit_condi)

                    # if there are boxes were not assigned
                    if len(hit_condi) != len(boxes):
                        assigned_boxes = [ind for k, ind in hit_condi]
                        assigned_keys = [k for k, ind in hit_condi]
                        not_assigned_boxes = set([i for i in range(len(boxes))]).difference(assigned_boxes)
                        not_assigned_keys = [k for k in on_keys if k not in assigned_keys]                        

                        for ind in not_assigned_boxes:

                            # if the not assigned boxes are too near with assigned keys, got thres
                            if any([v['dist'][ind] <= THRES_NEAR_DIST for k, v in tmp_dist_record.items() if k in assigned_keys]):
                                pass
                            else:
                                # less strict distance condition for not assigned object
                                min_dist = 9999
                                min_key = None
                                for k in not_assigned_keys:
                                    if tmp_dist_record[k]['dist'][ind] < min_dist:
                                        min_dist = tmp_dist_record[k]['dist'][ind]
                                        if min_dist <= THRES_NEAR_DIST_NOT_ASSIGN:
                                            min_key = k
                                # append the record if any object was found
                                if min_key is not None:
                                    if min_key not in label_ind:
                                        self.results_dict[min_key]['path'].append(tmp_dist_record[min_key]['center'][ind])
                                        self.results_dict[min_key]['n_frame'].append(n_frame)
                                        not_assigned_keys.pop(-1)
                                else:
                                    # forward next 100 points
                                    temp = 0
                                    forward_points = [eval(self.__yolo_results__[i])[1] for i in range(n_frame - 1, n_frame + (THRES_NOT_ASSIGN_FORWARD_N_MAX - 1))]
                                    p = tmp_dist_record[on_keys[0]]['center'][ind]
                                    for i, res in enumerate(forward_points):
                                        min_dist = 99999
                                        for b in res:
                                            ymin, xmin, ymax, xmax, score = b
                                            x_c = int((xmin+xmax) / 2 + 0.5)
                                            y_c = int((ymin+ymax) / 2 + 0.5)
                                            p_forward = (x_c, y_c)
                                            dist = np.linalg.norm(np.array(p_forward) - np.array(p))
                                            if dist <= min(THRES_NOT_ASSIGN_FORWARD_DIST, min_dist):
                                                min_dist = dist
                                                p = p_forward
                                        if min_dist < THRES_NOT_ASSIGN_FORWARD_DIST:
                                            temp += 1

                                    # if this center is potential, compare it with false positive point.
                                    if temp > THRES_NOT_ASSIGN_FORWARD_N:
                                        compare = False
                                        for fp in self.fp_pts:
                                            fp_dist = np.linalg.norm(np.array(fp) - np.array(tmp_dist_record[on_keys[0]]['center'][ind]))
                                            if fp_dist < THRES_NOT_ASSIGN_FP_DIST:
                                                compare = True
                                        # stop the function and ask user only if this center is not near with false positive points
                                        if not compare:
                                            undone_pts.append((tmp_dist_record[on_keys[0]]['center'][ind], n_frame))

                                            print('not assigned boxes')
                                            print(tmp_dist_record)
                                            print(hit_condi)
                                            print('index of not assigned bounding boxes: %s' % ind)
                                            lost_box_key = [k for k in on_keys if k not in [j for j, _ in hit_condi]]
                                            print(lost_box_key)
                                            if (tmp_dist_record[lost_box_key[0]]['center'][ind], n_frame) not in undone_pts:
                                                undone_pts.append((tmp_dist_record[lost_box_key[0]]['center'][ind], n_frame))
                                            self.is_calculate = False
                                    # if this center of bounding box is not potentially connected in next 100 frames, just ignored it.
                                    else:
                                        pass
                # there are boxes that hit condition with multi objects
                else:
                    hit_boxes = [v for k, v in hit_condi]
                    non_duplicate_key = [k for k, v in hit_condi if hit_boxes.count(v) == 1]
                    duplicate_ind = set([x for x in hit_boxes if hit_boxes.count(x) > 1]) # boxes indexes with multi objects
                    duplicate_key = [k for k, v in hit_condi if hit_boxes.count(v) > 1] # boxes indexes with multi objects

                    # if this is duplicate indexes case, assign the nearest one
                    if len(duplicate_ind) > 0 :
                        """
                        Try compare difference.
                        """
                        # print('frame: %s\nDuplicated index: %s\nDuplicated key: %s' % (n_frame, duplicate_ind, duplicate_key) )
                        min_key = []
                        # compare_diff = {}
                        # for ind in duplicate_ind:
                        #     tmp_keys = [k for k, v in hit_condi if v == ind]
                        #     compare_diff[ind] = dict()
                        #     compare_diff[ind]['similarity'] = []
                        #     p = tmp_dist_record[on_keys[0]]['center'][ind]
                            
                        #     # get current bounding box
                        #     _, boxes = eval(self.__yolo_results__[n_frame- 1])
                        #     for b in boxes:
                        #         ymin, xmin, ymax, xmax, score = b
                        #         x_c = int((xmin+xmax) / 2 + 0.5)
                        #         y_c = int((ymin+ymax) / 2 + 0.5)
                        #         if p == (x_c, y_c):
                        #             xmin, ymin, xmax, ymax = int(xmin), int(ymin), int(xmax), int(ymax)
                        #             img = self._orig_frame[ymin:ymax, xmin:xmax].copy()
                        #             img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        #             img = cv2.resize(img, (64, 64))
                        #             break

                        #     # compare nearest keys
                        #     for key in tmp_keys:
                        #         last_p = self.results_dict[key]['path'][-1]
                        #         last_n = self.results_dict[key]['n_frame'][-1]
                        #         _, boxes = eval(self.__yolo_results__[last_n - 1])
                                
                        #         # get this key's last bounding box
                        #         for b in boxes:
                        #             ymin, xmin, ymax, xmax, score = b
                        #             x_c = int((xmin+xmax) / 2 + 0.5)
                        #             y_c = int((ymin+ymax) / 2 + 0.5)
                        #             if last_p == (x_c, y_c):
                        #                 xmin, ymin, xmax, ymax = int(xmin), int(ymin), int(xmax), int(ymax)
                        #                 last_img = self._orig_frame[ymin:ymax, xmin:xmax].copy()
                        #                 last_img = cv2.cvtColor(last_img, cv2.COLOR_BGR2GRAY)
                        #                 last_img = cv2.resize(last_img, (64, 64))
                        #                 break
                        #         diff = compare_ssim(img, last_img)
                        #         compare_diff[ind]['similarity'].append((key, diff))
                        #         # Haralick = haralick(img).mean(axis=0)
                        #     sim = compare_diff[ind]['similarity']
                        #     compare_diff[ind]['nearest_key'] = sim[sorted(range(len(sim)), key=lambda i: sim[i][1], reverse=True)[0]][0]
                        #     min_key.append(compare_diff[ind]['nearest_key'])

                        # # if n_frame > 450 and n_frame < 455:
                        # #     print(n_frame, compare_diff)

                        # if len(set(min_key)) != len(min_key):
                        #     print('duplicate box and key!')
                        #     self.is_calculate = False
                        #     print(tmp_dist_record)
                        #     print(hit_condi)
                        #     undone_pts.append((tmp_dist_record[duplicate_key[0]]['center'][duplicate_ind.pop()], n_frame))

                        # just use nearest distance
                        for ind in duplicate_ind:
                            duplicate_key = [k for k, v in hit_condi if v == ind]
                            sorted_keys_by_dist = sorted(range(len(duplicate_key)), key=lambda k: tmp_dist_record[duplicate_key[k]]['dist'][ind])
                            min_dist_key = sorted_keys_by_dist[0]
                            min_key.append(duplicate_key[min_dist_key])

                        hit_condi_reduced = [(k, v) for k, v in hit_condi if k in non_duplicate_key + min_key]
                        for k, ind in hit_condi_reduced:
                            if k not in label_ind:
                                self.results_dict[k]['path'].append(tmp_dist_record[k]['center'][ind])
                                self.results_dict[k]['n_frame'].append(n_frame)

                        # pending, not assigned key

                    # if there is any condition that wasn't considered
                    else:
                        self.is_calculate = False
                        print("A not considered case happened!")
                        print(tmp_dist_record)
                        print(hit_condi)
            # just ignored if there is no bounding box in this frame
            else:
                on_keys = [k for k, v in self.object_name.items() if v['on']]
                pass

            # record animation
            if n_frame % n_show == 0:

                cv2.putText(self._frame, 'Calculating...', (30, 30), cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 255), 1)
                for k in on_keys:
                    color = self.color[self.object_name[k]['ind']]
                    flag = self.results_dict[k]['n_frame']
                    try:
                        last = np.where(np.array(flag) > (n_frame - 300))[0][0]
                    except:
                        last = None
                    # draw only for last 300 frame
                    if last is not None:
                        pts = self.results_dict[k]['path'][last:]
                        for i in range(1, len(pts)):
                            thickness = int(np.sqrt((1 + i * 0.01)  * 2) * 1.5)
                            cv2.line(self._frame, pts[i - 1], pts[i], color, thickness)

                self._frame = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)
                self.image = ImageTk.PhotoImage(Image.fromarray(self._frame))
                if self.display_label is not None:
                    self.display_label.configure(image=self.image)
                    self.scale_nframe.set(n_frame)
                    self.root.update_idletasks()
                else:
                # if not self.multi:
                    self.tracked_frames.append(ImageTk.PhotoImage(Image.fromarray(self._frame)))

            if self.is_calculate:
                n_frame += 1
            else:
                print('paths connecting stops at %s' % n_frame)

        # print('condition %s' % hit_condi)
        # print('undone points %s' % self.undone_pts)
        # print('lost key %s' % [tmp for tmp in self.object_name if tmp not in [j for j, _ in hit_condi]])

        # algorithm for suggesting a reasonable option
        for i, tup in enumerate(undone_pts):
            p, nframe = tup
            tmp_record = self.dist_records[nframe]
            min_dist_not_assigned = 9999
            min_key_not_assigned = None
            # compare with not assigned key
            for k, v in tmp_record.items():
                if k in [tmp for tmp in on_keys if tmp not in [j for j, _ in hit_condi]]:
                    ind = tmp_record[k]['center'].index(p)
                    if tmp_record[k]['dist'][ind] < min_dist_not_assigned:
                        min_dist_not_assigned = tmp_record[k]['dist'][ind]
                        min_key_not_assigned = k
            # compare with assigned key
            min_dist_assigned = 9999
            min_key_assigned = None
            for k, v in tmp_record.items():
                if k in [tmp for tmp in on_keys if tmp in [j for j, _ in hit_condi]]:
                    ind = tmp_record[k]['center'].index(p)
                    if tmp_record[k]['dist'][ind] < min_dist_assigned:
                        min_dist_assigned = tmp_record[k]['dist'][ind]
                        min_key_assigned = k

            # suggest new object if far with both assigned and not assigned keys
            if min_dist_not_assigned >= 80 and min_dist_assigned > 100:
                self.suggest_ind.append(('new', {'assigned': (min_key_assigned, min_dist_assigned), 'not_assigned': (min_key_not_assigned, min_dist_not_assigned)}))
            # suggest false positive if far with not assigned keys but near with assigned keys
            elif min_dist_not_assigned >= 80 and min_dist_assigned < 100:
                self.suggest_ind.append(('fp', {'assigned': (min_key_assigned, min_dist_assigned), 'not_assigned': (min_key_not_assigned, min_dist_not_assigned)}))
            # suggest the nearest not assigned key for other cases
            else:
                self.suggest_ind.append((min_key_not_assigned, {'assigned': (min_key_assigned, min_dist_assigned), 'not_assigned': (min_key_not_assigned, min_dist_not_assigned)}))

        # update default option if button has been already created
        if len(self.all_buttons) > 0:
            print(self.suggest_ind[0])

            if self.suggest_ind[0][0] == 'fp':
                self.all_buttons[0].focus_force()
            elif self.suggest_ind[0][0] == 'new':
                self.all_buttons[1].focus_force()
            else:
                self.all_buttons[self.object_name[self.suggest_ind[0][0]]['ind'] + 2].focus_force()

        # update new value
        self.n_frame = n_frame
        self.stop_n_frame = n_frame
        self.current_pts, self.current_pts_n = undone_pts.pop(0)
        self.undone_pts = undone_pts
        
        # record value for undoing
        self.save_records()

        # ensure don't enter manual mode and reset variable
        # self.is_manual = False
        self.min_label_ind = None