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


letter = [chr(i) for i in range(ord('a'), ord('z')+1)]

class KeyHandler(Interface, Common):

    def on_load(self):
        print('load')
        # self.__init__(self.maximum, self.tol)

    def on_settings(self, event=None):
        settings_root = tk.Tk()
        tk.Grid.rowconfigure(settings_root, 0, weight=1)
        tk.Grid.columnconfigure(settings_root, 0, weight=1)

        # center(settings_root) # center the widget
        # settings_root.geometry('380x240')
        def exit(event):
            settings_root.destroy()

        self.center(settings_root)
        settings_root.focus_force()
        settings_root.title('設定')

        ACTION = ['標註對應的目標 (a/b/c/d)', '誤判', '新目標', '回到上一步', '前一幀', '後一幀', '前五幀', '後五幀', '回到需被標註的幀數', '設定']
        HOTKEY = ['1/2/3/4', 'd/DELETE', 'n', 'u/BACKSPACE', 'LEFT', 'RIGHT', 'PAGE DOWN', 'PAGE UP', 'ENTER', 'h']

        hotkey = ttk.LabelFrame(settings_root, text="快捷鍵")
        action = ttk.LabelFrame(settings_root, text="操作")
        hotkey.grid(row=0, column=0, padx=5, pady=5)
        action.grid(row=0, column=1, padx=5, pady=5)

        # action description section
        for i, a in enumerate(ACTION):
            ttk.Label(action, text=a).grid(column=0, row=i, sticky=tk.W, padx=5, pady=5)
            ttk.Label(hotkey, text=HOTKEY[i]).grid(column=0, row=i, padx=5, pady=5)

        settings_root.bind('<Escape>', exit)
        settings_root.bind('<h>', exit)
        settings_root.mainloop()

    def on_mouse(self, event):
        self.is_clear = not self.is_clear
        # cv2.circle(self._frame, (event.x, event.y), 10, (255, 255, 255), 1)
        # self.tmp_line.append((event.x, event.y))
        print(event.x, event.y)

    def on_mouse_draw(self, event):
        # self.is_clear = not self.is_clear
        cv2.circle(self._frame, (event.x, event.y), 10, (255, 255, 255), 1)
        self.tmp_line.append((event.x, event.y))
        # print(event.x, event.y)

    def reset(self, event):
        self.tmp_line = []

    def on_mouse_mv(self, event):
        self.clear = True
        self.last_x = self.mv_x
        self.last_y = self.mv_y
        self.mv_x = event.x
        self.mv_y = event.y

    def on_click(self, clr):
        # TODO: multi undone?
        print(self.undone_pts)
        p, n = self.current_pts, self.current_pts_n
        run = True
        replace = False

        if clr in self.object_name:
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
            self.object_name.append(new_key)
            try:
                self.dist_records[n][new_key] = dict()
            except:
                self.dist_records[n] = dict()
                self.dist_records[n][new_key] = dict()
            self.dist_records[n][new_key]['dist'] = [0]
            self.dist_records[n][new_key]['center'] = [p]
            self.dist_records[n][new_key]['below_tol'] = [True]

            # add buttons
            bg = self.color_name[len(self.object_name) - 1].lower()
            b = tk.Button(self.BUTTON_FRAME, text=new_key, command=lambda clr=new_key: self.on_click(clr), bg=bg, fg='white')
            b.grid(row=len(self.all_buttons) + 1, column=0, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
            self.all_buttons.append(b)
            # add table info
            rd = self.results_dict[new_key]
            self.tv.insert('', 'end', new_key, text=new_key, values=(self.color_name[len(self.object_name) - 1], rd['path'][-1], rd['n_frame'][-1]))
            self.root.update_idletasks()
            print('added!')
        elif clr == '誤判了':
            self.fp_pts.append(p)
            print('deleted!')

        if run:
            if len(self.undone_pts) == 0:
                # self.tracked_frames = []
                self.root.update_idletasks()
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
                        self.all_buttons[self.object_name.index(self.suggest_ind[0][0]) + 2].focus_force()
                else:
                    self.all_buttons[0].focus_force()
                    # self.root.focus_force()

                print('just pass')

    def on_page_up(self, event):
        if self.n_frame > 1:
            self.n_frame -= 5
            self.n_frame = max(self.n_frame, 1)
        else:
            self.msg('Already the first frame!')

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
    
    def on_left(self, event):
        if self.n_frame > 1:
            self.n_frame -= 1
        else:
            self.msg('Already the first frame!')
        
    def on_right(self, event):
        if self.n_frame == self.total_frame:
            self.msg('Already the last frame!')
        else:
            self.n_frame += 1

    def on_key(self, event):
        if event.keysym not in ['n', 'Delete', 'd']:
            try:

                i = int(event.char)
                self.on_click(self.object_name[i-1])
            except Exception as e:
                print(e)
                print(event.keysym)
                pass
        elif event.keysym == 'n':
            self.on_click('New object, add one.')
        elif event.keysym in ['Delete', 'd']:
            self.on_click('False positive, delete it')
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

    def on_last_detected(self, event=None):
        self.n_frame = self.stop_n_frame

    def on_remove(self):
        def destroy(i):
            # root.grab_release()
            k = self.object_name[i]
            result = askyesno('Are you sure?', 'Do you really want to remove %s?' %k, icon='warning')
            if result:
                button = self.all_buttons[i+2]
                button.grid_forget()
                root.destroy()
                top.destroy()

                # delete all info
                self.tv.delete(k)
                self.deleted_name.append(k)
                # self.object_name.pop(i)

                del self.results_dict[k]
                del self.dist_records[k]
            else:
                # root.grab_set_global()
                pass
                # root.grab_set()
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
        for i, k in enumerate(self.object_name):
            b = ttk.Button(top, text=k, command=lambda i = i: destroy(i))
            b.pack(expand=True, fill=tk.BOTH)
        self.root.wait_window(top)
        root.mainloop()
        # root.grab_release()

    def on_show_boxes(self):
        self.is_show_boxes = not self.is_show_boxes

    def break_loop(self, event=None):
        self.safe = False
        # pass

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

                    for j, k in enumerate(object_name):
                        flag = results_dict[k]['n_frame']
                        color = COLOR[j]
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
        temp_root.destroy()
        temp_root.mainloop()

    def undo(self, event=None):
        if len(self.undo_records) > 1:
            self.results_dict, self.stop_n_frame, self.undone_pts, self.current_pts, self.current_pts_n, self.suggest_ind, self.object_name, self.deleted_name = self.undo_records[-2]
            print(self.object_name)
            self.undo_records = self.undo_records[:-1]
            self.n_frame = self.stop_n_frame
            if len(self.suggest_ind) > 0:
                if self.suggest_ind[0][0] == 'fp':
                    self.all_buttons[0].focus_force()
                elif self.suggest_ind[0][0] == 'new':
                    self.all_buttons[1].focus_force()
                else:
                    self.all_buttons[self.object_name.index(self.suggest_ind[0][0]) + 2].focus_force()

        else:
            self.msg('Nothing can undo.')