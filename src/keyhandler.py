import cv2
from src.interface import Interface
from src.utils import Common
from PIL import Image, ImageTk
import tkinter as tk
import threading
from tkinter import ttk
import imageio
from tkinter.messagebox import askyesno
import numpy as np
import copy

letter = [chr(i) for i in range(ord('a'), ord('z')+1)]

class KeyHandler(Interface, Common):

    def on_load(self):
        print('load')
        # self.__init__(self.maximum, self.tol)

    def on_settings(self, event=None):
        self.setting()

    def reset(self, event):
        self.tmp_line = []

    def on_mouse_mv(self, event):
        self.clear = True
        self.last_x = self.mv_x
        self.last_y = self.mv_y
        self.mv_x = event.x
        self.mv_y = event.y

    def chg_mode(self):
        self.is_manual = not self.is_manual
        for b in self.all_buttons:
            b['state'] = 'disabled' if self.is_manual else 'normal'

        if self.is_manual:
            self.label_dict = {k: {'path': [], 'n_frame': []} for k in [k for k, v in self.object_name.items() if v['on']]}
            # temporally results for manual label
            self.tmp_results_dict = copy.deepcopy(self.results_dict)

    def on_mouse(self, event):
        n = event.num
        # if double click, enter manual label mdoe
        if n == 1 and not self.is_manual:
            self.chg_mode()

        # if right click
        elif n == 3:
            if self.is_manual:
                k = [k for k, v in self.object_name.items() if v['ind'] == self.label_ind - 1][0]
                # remove current label if any exists
                try:
                    ind = self.label_dict[k]['n_frame'].index(self.n_frame)
                    self.label_dict[k]['n_frame'].pop(ind)
                    self.label_dict[k]['path'].pop(ind)
                except:
                    pass

                try:
                    ind = self.results_dict[k]['n_frame'].index(self.n_frame)
                    self.tmp_results_dict[k]['path'][ind] = self.results_dict[k]['path'][ind]
                except Exception as e:
                    try:
                        ind = self.tmp_results_dict[k]['n_frame'].index(self.n_frame)
                        self.tmp_results_dict[k]['n_frame'].pop(ind)
                        self.tmp_results_dict[k]['path'].pop(ind)
                    except Exception as e:
                        print(e)
            # self.is_clear = not self.is_clear

    def on_mouse_draw(self, event):
        if not self.is_manual:
            cv2.circle(self._frame, (event.x, event.y), 10, (255, 255, 255), 1)
            self.tmp_line.append((event.x, event.y))

    def on_mouse_manual_label(self, event):
        # execute only if it is manual label mode
        if self.is_manual:
            k = [k for k, v in self.object_name.items() if v['ind'] == self.label_ind - 1][0]
            p = (event.x, event.y)
            # record label points
            if self.n_frame not in self.label_dict[k]['n_frame']:
                self.label_dict[k]['n_frame'].append(self.n_frame)
                self.label_dict[k]['path'].append(p)
            else:
                self.label_dict[k]['path'][self.label_dict[k]['n_frame'].index(self.n_frame)] = p

            # modify label point if it conflicts with original result dicts
            try:
                ind = self.tmp_results_dict[k]['n_frame'].index(self.n_frame)
                self.tmp_results_dict[k]['path'][ind] = p
            except:
                self.tmp_results_dict[k]['n_frame'].append(self.n_frame)
                self.tmp_results_dict[k]['path'].append(p)

    # mouse wheel event
    def on_mouse_wheel(self, event):

        if self.is_manual:
            if event.delta == -120:
                self.label_ind = max(1 + min([v['ind'] for k, v in self.object_name.items() if v['on']]), self.label_ind - 1)
            elif event.delta == 120:
                self.label_ind = min(len([k for k, v in self.object_name.items() if v['on']]), self.label_ind + 1)
            print(self.label_ind)

    # button event
    def on_click(self, clr):
        self.n_frame = self.stop_n_frame
        p, n = self.current_pts, self.current_pts_n
        run = True
        replace = False

        if clr in [k for k, v in self.object_name.items() if v['on']]:
            is_assigned = self.results_dict[clr]['n_frame'][-1] == self.stop_n_frame
            if not is_assigned:
                self.results_dict[clr]['path'].append(p)
                self.results_dict[clr]['n_frame'].append(n)
                print('appended!')
            else:
                res = self.ask_yes_no(clr)
                if res:
                    self.undone_pts.append((self.results_dict[clr]['path'][-1], n))
                    print(self.undone_pts)
                    self.results_dict[clr]['path'][-1] = p
                    print('appended!')
                    run = True
                    replace = True
                else:
                    run = False
        elif clr == '新目標':
            # append results
            new_key = letter[len(self.object_name)]
            self.results_dict[new_key] = {'path': [p, p], 'n_frame': [n, n]}
            print(len(self.object_name), self.object_name)
            self.object_name[new_key] = {'ind': len(self.object_name), 'on': True, 'display_name': new_key}
            print(len(self.object_name))
            try:
                self.dist_records[n][new_key] = dict()
            except:
                self.dist_records[n] = dict()
                self.dist_records[n][new_key] = dict()
            self.dist_records[n][new_key]['dist'] = [0]
            self.dist_records[n][new_key]['center'] = [p]
            self.dist_records[n][new_key]['below_tol'] = [True]

            # add buttons
            bg = self.color_name[self.object_name[new_key]['ind']].lower()
            b = tk.Button(self.BUTTON_FRAME, text=new_key, command=lambda clr=new_key: self.on_click(clr), bg=bg, fg='white')
            b.grid(row=len(self.all_buttons) + 2, column=0, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
            self.all_buttons.append(b)
            # add table info
            rd = self.results_dict[new_key]
            self.tv.insert('', 'end', new_key, text=new_key, values=(self.color_name[self.object_name[new_key]['ind']], rd['path'][-1], rd['n_frame'][-1]))
            print('added!')
        elif clr == '誤判':
            self.fp_pts.append(p)
            print('deleted!')

        if run:
            if len(self.undone_pts) == 0:
                # self.tracked_frames = []
                self.root.update()
                self.calculate_path(self.stop_n_frame + 1)
                # self.root.after(0, self.update_track, 0)
            else:
                self.current_pts, self.current_pts_n = self.undone_pts.pop(0)
                self.suggest_ind.pop(0)
                if len(self.suggest_ind) > 0:
                    print(self.suggest_ind[0])
                    if self.suggest_ind[0][0] == 'fp':
                        self.all_buttons[0].focus_force()
                    elif self.suggest_ind[0][0] == 'new':
                        self.all_buttons[1].focus_force()
                    else:
                        self.all_buttons[self.object_name[self.suggest_ind[0][0]]['ind']].focus_force()
                else:
                    self.all_buttons[0].focus_force()

    # move to previous frame
    def on_left(self, event):
        if self.n_frame > 1:
            self.n_frame -= 1
        else:
            self.msg('Already the first frame!')
    
    # move to next frame
    def on_right(self, event):
        if self.n_frame == self.total_frame:
            self.msg('Already the last frame!')
        else:
            self.n_frame += 1

    # move to previous 5 frames
    def on_page_up(self, event):
        if self.n_frame > 1:
            self.n_frame -= 5
            self.n_frame = max(self.n_frame, 1)
        else:
            self.msg('Already the first frame!')

    # move to next 5 frames
    def on_page_down(self, event):
        if self.n_frame == self.total_frame:
            self.msg('Already the last frame!')
        else:
            self.n_frame += 5
            self.n_frame = min(self.n_frame, self.total_frame)

    def on_up(self, event):
        print('up')

    def on_down(self, event):
        print('down')

    # on some key pressed event
    def on_key(self, event):
        sym = event.keysym
        if not self.is_manual:
            if sym not in ['n', 'Delete', 'd', 'l']:
                try:
                    i = int(event.char)
                    self.on_click([k for k, v in self.object_name.items() if v['ind'] == i - 1][0])
                except Exception as e:
                    print(e)

            elif sym == 'n':
                if not self.is_manual:
                    self.on_click('New object, add one.')
                else:
                    # pending; add new object while manual label mode.
                    pass
            elif sym in ['Delete', 'd']:
                self.on_click('False positive, delete it')
            elif sym == 'l':
                self.chg_mode()
        else:
            if sym not in ['n', 'Delete', 'd', 'l']:
                self.label_ind = int(sym)

    def set_max(self, s):
        v = int(float(s))
        self.maximum_var.set(v)
        self.maximum = v

    def set_tol(self, s):
        v = round(float(s), 1)
        self.tol_var.set(v)
        self.tol = v

    def set_nframe(self, s):
        v = int(float(s))
        self.n_frame_var.set(v)
        self.n_frame = v

    def on_return(self, event=None):
        self.n_frame = self.stop_n_frame

        if self.is_manual:
            # pending; a confirm UI
            self.chg_mode()

            string = '是否把以上標註加入目前的目標路徑？'
            result = askyesno('確認', string, icon='warning')
            if result:
                self.results_dict = copy.deepcopy(self.tmp_results_dict)

            self.label_dict = {k: {'path': [], 'n_frame': []} for k in [v['ind'] for k, v in self.object_name if v['on']]}

    def on_remove(self):
        # pending; a better workflow for undo
        def destroy(i):
            # root.grab_release()
            k = [k for k, v in self.object_name.items() if v['ind'] == i][0]
            result = askyesno('確認', '確定要刪除 %s 嗎？' %k, icon='warning')
            if result:
                button = self.all_buttons[i+2]
                button.grid_forget()
                root.destroy()
                top.destroy()

                # delete all info
                self.tv.delete(k)
                self.object_name[k]['on'] = False

                del self.results_dict[k]
                if k in self.dist_records.keys():
                    del self.dist_records[k]
            else:
                pass
        def close():
            root.destroy()

        root = tk.Tk()
        root.protocol('WM_DELETE_WINDOW', close)
        root.withdraw()
        top = tk.Toplevel()
        top.grab_set()
        ## Display the window and wait for it to close
        root.title('Remove object')
        self.center(top)
        for k in sorted([k for k, v in self.object_name.items() if v['on']]):
            b = ttk.Button(top, text=k, command=lambda i = self.object_name[k]['ind']: destroy(i))
            b.pack(expand=True, fill=tk.BOTH)
        self.root.wait_window(top)
        root.mainloop()

    def on_show_boxes(self):
        self.is_show_boxes = not self.is_show_boxes

    def break_loop(self, event=None):
        self.safe = False

    def on_view_results(self):
        """
        TODO:
        interpolation for results.
        """
        results_dict = self.results_dict
        video = imageio.get_reader(self.video_path)
        COLOR = self.color
        object_name = self.object_name
        break_pt = max([max(v['n_frame']) for k, v in results_dict.items()])

        # nested function
        def stream(label):

            for i, frame in enumerate(video.iter_data()):
                if i % 20 == 0:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                    for k in sorted([k for k, v in object_name.items() if v['on']]):
                        flag = results_dict[k]['n_frame']
                        color = self.color[object_name[k]['ind']]
                        try:
                            ind = np.where(np.array(flag) > i)[0][0]
                        except Exception as e:
                            # print(e)
                            ind = None
                        if ind is not None:
                            path = results_dict[k]['path'][:ind][-150:]
                            for l in range(1, len(path)):
                                thickness = int(np.sqrt((1 + l * 0.01) * 2) * 1.5)
                                cv2.line(frame, path[l - 1], path[l], color, thickness)

                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = ImageTk.PhotoImage(Image.fromarray(frame))
                    label.configure(image=image)
                    label.image = image
                if i == break_pt:
                    master.destroy()
                    temp_root.destroy()
                    break
        def exit(event):
            master.destroy()
            temp_root.destroy()

        temp_root = tk.Tk()
        temp_root.withdraw()
        self.center(temp_root)
        master = tk.Toplevel()
        master.focus_force()
        master.title('Results')
        my_label = tk.Label(master)
        my_label.pack()
        thread = threading.Thread(target=stream, args=(my_label,))
        thread.daemon = 1
        thread.start()
        master.bind('<Escape>', exit)
        # temp_root.destroy()
        temp_root.mainloop()

    def tvitem_click(self, event):
        sel_items = self.tv.selection()
        if sel_items:
            popup = Interface.popupEntry(self.root)
            self.root.wait_window(popup.top)
            sel_item = sel_items[0]

            try:
                new_key = popup.value
                if new_key in [v['display_name'] for k, v in self.object_name.items()]:
                    self.msg('%s 已經被使用了。' % new_key)
                elif new_key in [" " * i for i in range(10)]:
                    self.msg('請輸入空白鍵以外的字串。')
                else:
                    self.object_name[sel_item]['display_name'] = new_key
                    self.all_buttons[self.object_name[sel_item]['ind'] + 2].config(text=new_key)
            except:
                pass

    def undo(self, event=None):
        if len(self.undo_records) > 0:
            self.results_dict, self.stop_n_frame, self.undone_pts, self.current_pts, self.current_pts_n, self.suggest_ind, self.object_name = self.undo_records[-2 if len(self.undo_records) > 1 else -1]
            print(self.object_name)
            self.undo_records = self.undo_records[:-1]
            self.n_frame = self.stop_n_frame
            if len(self.suggest_ind) > 0:
                if self.suggest_ind[0][0] == 'fp':
                    self.all_buttons[0].focus_force()
                elif self.suggest_ind[0][0] == 'new':
                    self.all_buttons[1].focus_force()
                else:
                    self.all_buttons[self.object_name[self.suggest_ind[0][0]]['ind']].focus_force()

            # update buttons number
            on_ind = [v['ind'] for k, v in self.object_name.items()]
            for i, b in enumerate(self.all_buttons):
                if i in [0, 1]:
                    pass
                elif i - 2 in on_ind:
                    b.grid(row=i + 2, column=0, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
                else:
                    try:
                        self.tv.delete(letter[i-2])
                    except:
                        print(letter[i-2])

                    b.grid_forget()

        else:
            self.msg('Nothing can undo.')