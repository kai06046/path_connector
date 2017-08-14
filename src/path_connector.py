import tkinter as tk
from tkinter import ttk
import cv2
import time, os, pickle, copy
import numpy as np
from PIL import Image, ImageTk
import threading

from src.yoloreader import YOLOReader
from src.keyhandler import KeyHandler
from src.utils import Utils

# basic setup variables
WIN_NAME = 'Path Connector'
VIDEO_PATH = 'videos/[CH04] 2016-09-28 20.20.00_x264.avi'
COLOR_NAME = ['GREEN', 'BLUE', 'PURPLE', 'ORANGE', 'PINK', 'YELLOW', 'CYAN', 'WHITE', 'BLACK', 'RED']
COLOR = [(0, 255, 0), (255, 100, 10), (245, 10, 180), (0, 122, 255), (255, 102, 255), (0, 255, 255), (255, 255, 0), (255, 255, 255), (0, 0, 0), (100, 10, 255)]

# UI required variables
letter = [chr(i) for i in range(ord('a'), ord('z')+1)]
LARGE_FONT= ("Verdana", 12)
MULTI = False

class PathConnector(YOLOReader, KeyHandler, Utils):
    
    def __init__(self, maximum, tol):
        """
        ----------------------------------------------------------------------
        This is a GUI for connecting paths results that were detected by YOLO.
        ----------------------------------------------------------------------
        maximum: temp varible; maximum number of frames to display connected.
        tol: temp variable; maximum tolerance distance between context path coordinate.
        
        """
        # basic setup
        self.win_name = WIN_NAME
        self.video_path = None
        self.video = None
        self.video = None
        self.width = None
        self.height = None
        self.fps = None
        self.resolution = None
        self.total_frame = None
        self.__yolo_results__ = None

        # basic variables
        self.color = COLOR
        self.color_name = COLOR_NAME
        self.maximum = maximum
        self.tol = tol
        self.near_tol = 32
        self.start_time = 0

        # variables for displaying in canvas
        self._frame = None
        self._orig_frame = None
        self.n_frame = None
        self.stop_n_frame = None
        self.mv_x = 0
        self.mv_y = 0
        self.last_x = 0
        self.last_y = 0
        self.image = None
        self.image_tracked = None
        self.clear = False
        self.is_clear = 1 # right mouse click for removing drawing
        self.tmp_line = []

        # variables for recording things
        self.object_name = dict()
        self.results_dict = dict()
        self.dist_records = dict()
        self.label_dict = dict()
        self.tmp_results_dict = None
        self.undone_pts = None
        self.fp_pts = []
        self.undo_records = []
        self.tracked_frames = []
        self.multi = MULTI
        self.suggest_ind = []
        self.current_pts = None
        self.current_pts_n = None
        self.safe = True
        self.is_calculate = False
        self.is_manual = False
        self.label_ind = 1

        # tkinter widgets
        self.root = None
        self.display_label = None
        self.tv = None
        self.label_nframe = None
        self.label_fps = None
        self.label_elapsed = None
        self.label_mvpts = None
        self.scale_nframe = None
        self.n_frame_var = None
        self.maximum_var = None
        self.tol_var = None
        self.BUTTON_FRAME = None
        self.check_show_yolo = None
        self.check_show_drawing = None
        self.check_show_arrow = None
        self.all_buttons = []

        # threading
        self.lock = threading.Lock()
        
    def update_frame(self, ind=None):
        ind = ind if ind is not None else self.n_frame - 1
        self.video.set(cv2.CAP_PROP_POS_FRAMES, ind)
        ok, self._frame = self.video.read()
        self._orig_frame = self._frame.copy()

    def thread_update(self, ind):
        td = threading.Thread(target=self.update_frame, args=(ind, ))
        td.start()

    def thread_pop(self):
        td = threading.Thread(target=self.pop_msg, args=())
        td.start()

    def update_info(self):
        # update object information table
        if self.tv is not None:
            for n in sorted([k for k, v in self.object_name.items() if v['on']]):
                rd = self.results_dict[n]
                try:
                    is_detected = rd['n_frame'].index(self.n_frame)
                    is_detected = True
                except:
                    is_detected = False
                try:
                    self.tv.item(n, text=self.object_name[n]['display_name'], values=(self.color_name[self.object_name[n]['ind']], is_detected, rd['n_frame'][-1]))
                except:
                    self.object_name[n]['on'] = True
                    self.tv.insert('', 'end', n, text=n, values=(self.color_name[self.object_name[n]['ind']], is_detected, rd['n_frame'][-1]))

    def update_label(self):
        # text_nframe = 'Current Frame: '
        # text_video_name = self.video_path.split('/')[-1]
        sec = round(self.n_frame / self.fps, 2)
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        text_time = "%d:%02d:%02d" % (h, m, s)

        # text_fps = round(self.stop_n_frame / (time.clock() - self.start_time), 3)
        # text_elapsed = round(time.clock() - self.start_time)
        # text_mvpts = 'x: %s    y: %s' % (self.mv_x, self.mv_y)
        
        # self.label_video_name.configure(text=text_video_name)
        # self.label_nframe.configure(text=text_nframe)
        self.label_time.configure(text=text_time)
        # self.label_elapsed.configure(text=text_elapsed)
        # self.label_mvpts.configure(text=text_mvpts)
        self.scale_nframe.set(self.n_frame)

        self.root.after(200, self.update_label)

    def update_draw(self, tup=None):
        self.update_frame()
        self.update_info()
        self.draw(tup)
        if not self.is_calculate:
            self.image = ImageTk.PhotoImage(Image.fromarray(self._frame))
        self.display_label.configure(image=self.image)

        self.root.after(150, self.update_draw)

    def update_track(self, ind):
        if len(self.tracked_frames) > 0 and ind < (len(self.tracked_frames) - 1) and self.safe:
            frame = self.tracked_frames[ind] 
            if ind < (len(self.tracked_frames) - 1):
                ind += 1
                self.display_label.configure(image=frame)
                self.root.after(200, self.update_track, ind)
        else:
            self.safe = True
            self.display_label.configure(image=self.image)

    def update_image(self):
        self.display_label.configure(image=self.image)
        self.root.after(200, self.update_image)

    def start(self):
        root = tk.Tk()
        root.title(self.win_name)
        self.center(root)
        label = ttk.Label(root, text='請載入埋葬蟲影像。\n* 影像路徑底下請附上包含 YOLO 結果並和影像檔名相同的 txt。', font=LARGE_FONT)
        label.pack(padx=10, pady=10)

        label2 = ttk.Label(root, text='當下沒有影像。')
        label2.pack(padx=10, pady=10)

        button = ttk.Button(root, text='載入影像', command=lambda l = label2: self.get_path(l))
        button.pack(padx=10, pady=10)

        button2 = ttk.Button(root, text='開始', command=lambda r = root: self.ready(r))
        button2.pack(padx=10, pady=10)

        root.bind('<Escape>', lambda event: root.destroy())
        root.mainloop()

    def init_video(self):
        self.video = cv2.VideoCapture(self.video_path)
        self.width = int(self.video.get(3))
        self.height = int(self.video.get(4))
        self.fps = int(self.video.get(5))
        self.resolution = (self.width, self.height)
        self.total_frame = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
        self.__yolo_results__ = self.read_yolo_result()

    def ready(self, r):
        if self.video_path is not None:
            r.destroy()
            self.init_video()
            # start
            self.run()
        else:
            self.msg('Please load a video first.')

    def save_records(self):
        
        records = (copy.deepcopy(self.results_dict), self.stop_n_frame, self.undone_pts, self.current_pts, self.current_pts_n, copy.deepcopy(self.suggest_ind), copy.deepcopy(self.object_name))
        if len(self.undo_records) > 0:
            if self.stop_n_frame != self.undo_records[-1][1]:
                self.undo_records.append(records)
        else:
            self.undo_records.append(records)

    # main logic for runing UI
    def run(self):
        
        self.n_frame = 1
        self.video.set(cv2.CAP_PROP_POS_FRAMES, self.n_frame - 1)
        ok, self._frame = self.video.read()
        self._orig_frame = self._frame.copy()
        self.draw_legend()
        
        if not ok:
            self.msg("Can't open the video")

        self.root = tk.Tk()
        self.root.title(self.win_name)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.bind('<Left>', self.on_left)
        self.root.bind('<Right>', self.on_right)        
        self.root.bind('<Up>', self.on_up)        
        self.root.bind('<Down>', self.on_down)        
        self.root.bind('<Prior>', self.on_page_up)
        self.root.bind('<Next>', self.on_page_down)
        self.root.focus_force()
        self.root.option_add('*tearOff', False)
        self.root.option_add("*Font", "verdana 10")
        tk.Grid.rowconfigure(self.root, 0, weight=1)
        tk.Grid.columnconfigure(self.root, 0, weight=1)

        file = self.video_path.split('.avi')[0] + '.dat'
        if os.path.isfile(file):
            self.results_dict, self.stop_n_frame, self.undone_pts, self.current_pts, self.current_pts_n, self.suggest_ind, self.object_name = pickle.load(open(file, "rb" ))[-1]
            self.n_frame = self.stop_n_frame
        else:
            self.calculate_path()
        self.update_frame()
        self.update_info()
        self.draw()
        self.center(self.root)

        # create a menu instance
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        # create the file object
        file = tk.Menu(menu)
        file.add_command(label='Load', command=self.on_load)
        menu.add_cascade(label='File', menu=file)

        # create the help object
        help = tk.Menu(menu)
        help.add_command(label='設定', command=self.on_settings)
        menu.add_cascade(label='Help', menu=help)

        # label for frame information
        self.n_frame_var = tk.IntVar()
        self.n_frame_var.set(self.n_frame)
        self.maximum_var = tk.IntVar()
        self.maximum_var.set(self.maximum)
        self.tol_var = tk.DoubleVar()
        self.tol_var.set(self.tol)
        self.check_show_yolo = tk.IntVar()
        self.check_show_yolo.set(1)
        self.check_show_drawing = tk.IntVar()
        self.check_show_drawing.set(1)
        self.check_show_arrow = tk.IntVar()
        self.check_show_arrow.set(1)
        self.check_is_clear = tk.IntVar()
        self.check_is_clear.set(1)


        text_nframe = '當前幀數: '
        text_video_name =self.video_path.split('/')[-1]
        sec = round(self.n_frame / self.fps, 2)
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        text_time = "%d:%02d:%02d" % (h, m, s)
        # text_elapsed = round(time.clock() - self.start_time)
        # text_mvpts = 'x: %s    y: %s' % (self.mv_x, self.mv_y)

        # convert to format that ImageTk require
        self.image = ImageTk.PhotoImage(Image.fromarray(self._frame))
        
        # frame for displaying image label
        IMAGE_FRAME = ttk.Frame(self.root)
        IMAGE_FRAME.grid(row=0, column=0)
        self.display_label = ttk.Label(IMAGE_FRAME, image=self.image)
        self.display_label.grid(row=0, column=0, columnspan=2)
        # self.display_label.bind('<Double-Button-1>', self.on_mouse)
        self.display_label.bind('<B1-Motion>', self.on_mouse_draw)
        self.display_label.bind('<Double-Button-1>', self.on_mouse)
        self.display_label.bind('<Button-3>', self.on_mouse)
        self.display_label.bind('<Button-1>', self.on_mouse_manual_label)
        self.display_label.bind('<MouseWheel>', self.on_mouse_wheel)
        self.display_label.bind('<ButtonRelease-1>', self.reset)
        self.display_label.bind('<Motion>', self.on_mouse_mv)
        
        IMAGE_LABEL_FRAME = ttk.LabelFrame(IMAGE_FRAME)
        IMAGE_LABEL_FRAME.grid(sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)

        self.label_nframe = ttk.Label(IMAGE_LABEL_FRAME, text=text_nframe)
        self.label_nframe.grid(row=0, column=0, sticky=tk.W, rowspan=2)
        label_nframe_v = ttk.Label(IMAGE_LABEL_FRAME, textvariable=self.n_frame_var)
        label_nframe_v.grid(row=0, column=1)
        self.scale_nframe = ttk.Scale(IMAGE_LABEL_FRAME, from_=1, to_=self.total_frame, length=1200, command=self.set_nframe)
        self.scale_nframe.set(self.n_frame)
        self.scale_nframe.grid(row=1, column=1)

        # operation frame that will display all application relevent information
        OP_FRAME = ttk.Frame(self.root)
        OP_FRAME.grid(row=0, column=1, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)

        # frame for displaying current statement
        STATE_FRAME = ttk.Frame(OP_FRAME)
        STATE_FRAME.grid(sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        
        # subframe for displaying frame information
        INFO_FRAME = ttk.LabelFrame(STATE_FRAME, text='影像訊息')
        INFO_FRAME.grid(sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)

        label_video_name = ttk.Label(INFO_FRAME, text='影像檔名: ')
        label_video_name.grid(row=0, column=0, sticky=tk.W)
        self.label_video_name = ttk.Label(INFO_FRAME, text=text_video_name)
        self.label_video_name.grid(row=0, column=1, sticky=tk.W)
        label_time = ttk.Label(INFO_FRAME, text='影像時間: ')
        label_time.grid(row=1, column=0, sticky=tk.W)
        self.label_time = ttk.Label(INFO_FRAME, text=text_time)
        self.label_time.grid(row=1, column=1, sticky=tk.W)
        # label_elapsed = ttk.Label(INFO_FRAME, text='Elapsed time: ')
        # label_elapsed.grid(row=2, column=0, sticky=tk.W)
        # self.label_elapsed = ttk.Label(INFO_FRAME, text=text_elapsed)
        # self.label_elapsed.grid(row=1, column=1, sticky=tk.W)
        # self.label_mvpts = ttk.Label(INFO_FRAME, text=text_mvpts)
        # self.label_mvpts.grid(row=3, columnspan=2, sticky=tk.W)

        # label_tol = ttk.Label(INFO_FRAME, text='Maximum distance: ')
        # label_tol.grid(row=6, column=0, rowspan=2)
        # label_tol_v = ttk.Label(INFO_FRAME, textvariable=self.tol_var)
        # label_tol_v.grid(row=6, column=1)
        # scale_tol = ttk.Scale(INFO_FRAME, from_=1, to_=100, length=300, command=self.set_tol)
        # scale_tol.set(self.tol)
        # scale_tol.grid(row=7, column=1)

        # subframe for displaying object information
        OBJ_FRAME = ttk.LabelFrame(STATE_FRAME, text='目標資訊')
        OBJ_FRAME.grid(sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        
        self.tv = ttk.Treeview(OBJ_FRAME, height = 5)
        self.tv['columns'] = ('color', 'lastpoint', 'lastdetectedframe')
        self.tv.heading('#0', text='名稱', anchor='center')
        self.tv.column('#0', anchor='w', width=50)
        self.tv.heading('color', text='顏色')
        self.tv.column('color', anchor='center', width=60)
        self.tv.heading('lastpoint', text='在本幀是否有被偵測到')
        self.tv.column('lastpoint', anchor='center', width=140)
        self.tv.heading('lastdetectedframe', text='最後被偵測到的幀數')
        self.tv.column('lastdetectedframe', anchor='center', width=140)
        self.tv.grid()

        for n in sorted(self.object_name.keys()):
            rd = self.results_dict[n]
            try:
                is_detected = rd['n_frame'].index(self.n_frame)
                is_detected = True
            except:
                is_detected = False
            self.tv.insert('', 'end', n, text=n, values=(self.color_name[self.object_name[n]['ind']], is_detected, rd['n_frame'][-1]))
        self.tv.bind('<Double-Button-1>', self.tvitem_click) 

        # frame for legend
        LEGENG_FRAME = ttk.LabelFrame(STATE_FRAME, text='圖例說明')
        LEGENG_FRAME.grid(sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        LEGENG_FRAME.grid_columnconfigure(1, weight=1)
        LEGENG_FRAME.grid_rowconfigure(1, weight=1)
        l_1 = ImageTk.PhotoImage(Image.fromarray(self.legend_1))
        l_2 = ImageTk.PhotoImage(Image.fromarray(self.legend_2))
        l_3 = ImageTk.PhotoImage(Image.fromarray(self.legend_3))
        l_4 = ImageTk.PhotoImage(Image.fromarray(self.legend_4))

        legend_2 = ttk.Label(LEGENG_FRAME, image=l_2, width=10)
        legend_2.grid(row=0, column=0, padx=5, pady=5)
        legend_1 = ttk.Label(LEGENG_FRAME, image=l_1, width=10)
        legend_1.grid(row=0, column=1, padx=5, pady=5)
        legend_3 = ttk.Label(LEGENG_FRAME, image=l_3, width=10)
        legend_3.grid(row=0, column=2, padx=5, pady=5)
        legend_4 = ttk.Label(LEGENG_FRAME, image=l_4, width=10)
        legend_4.grid(row=0, column=3, padx=5, pady=5)

        label_legend_2 = ttk.Label(LEGENG_FRAME, text='需被標註的\nbbox', width=10, anchor='center')
        label_legend_2.grid(row=1, column=0, padx=5, pady=5)        
        label_legend_1 = ttk.Label(LEGENG_FRAME, text='目標路徑起點', width=10, anchor='center')
        label_legend_1.grid(row=1, column=1, padx=5, pady=5)        
        label_legend_3 = ttk.Label(LEGENG_FRAME, text='目標在本幀的位置', width=13, anchor='center')
        label_legend_3.grid(row=1, column=2, padx=5, pady=5)        
        label_legend_4 = ttk.Label(LEGENG_FRAME, text='目標路徑終點', width=10, anchor='center')
        label_legend_4.grid(row=1, column=3, padx=5, pady=5)        

        # frame for display buttons
        self.BUTTON_FRAME = ttk.LabelFrame(OP_FRAME, text="需被標註的 bbox 應該是哪一個目標呢？")
        self.BUTTON_FRAME.grid(row=1, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        
        for i, k in enumerate(['誤判', '新目標'] + sorted(self.object_name.keys())):
            if i in [0, 1]:
                bg = None
                fg = None
                b = ttk.Button(self.BUTTON_FRAME, text=k, command=lambda clr=k: self.on_click(clr), bg=bg, fg=fg, width=40)
                b.grid(row=i, column=0, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)

            else:
                bg = self.color_name[self.object_name[k]['ind']].lower()
                fg = 'white'
                b = tk.Button(self.BUTTON_FRAME, text=k, command=lambda clr=k: self.on_click(clr), bg=bg, fg=fg)
                b.grid(row=i, column=0, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)

            self.all_buttons.append(b)

        self.BUTTON_FRAME_2 = ttk.LabelFrame(OP_FRAME, text='操作')
        self.BUTTON_FRAME_2.grid(row=2, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)

        button_go = ttk.Button(self.BUTTON_FRAME_2, text='回到需被標註的幀數', command=self.on_return)
        button_go.grid(row=0, rowspan=2, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S, padx=10, pady=5)
        
        button_remove = ttk.Button(self.BUTTON_FRAME_2, text='刪除目標', command=self.on_remove)
        button_remove.grid(row=2, rowspan=2, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S, padx=10, pady=5)

        button_replay = ttk.Button(self.BUTTON_FRAME_2, text='播放當前為止的追踪結果', command=self.on_view_results)
        button_replay.grid(row=4, rowspan=2, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S, padx=10, pady=5)

        label_max = ttk.Label(self.BUTTON_FRAME_2, text='顯示路徑的長度: ')
        label_max.grid(row=6, column=0, rowspan=2, sticky=tk.W)
        label_max_v = ttk.Label(self.BUTTON_FRAME_2, textvariable=self.maximum_var)
        label_max_v.grid(row=6, column=1)
        scale_max = ttk.Scale(self.BUTTON_FRAME_2, from_=2, to_=3000, length=200, command=self.set_max)
        scale_max.set(self.maximum)
        scale_max.grid(row=6, column=1)

        button_show_box = ttk.Checkbutton(self.BUTTON_FRAME_2, variable=self.check_show_yolo, onvalue=1, offvalue=0, text='顯示 YOLO bounding box')
        button_show_box.grid(row=8, rowspan=2, column=0, sticky=tk.W+tk.E+tk.N+tk.S, padx=10, pady=5)

        button_is_clear = ttk.Checkbutton(self.BUTTON_FRAME_2, variable=self.check_is_clear, onvalue=1, offvalue=0, text='Eraser')
        button_is_clear.grid(row=10, rowspan=2, column=0, sticky=tk.W+tk.E+tk.N+tk.S, padx=10, pady=5)
        
        button_show_arrow = ttk.Checkbutton(self.BUTTON_FRAME_2, variable=self.check_show_arrow, onvalue=1, offvalue=0, text='顯示路徑方向')
        button_show_arrow.grid(row=8, rowspan=2, column=1, sticky=tk.W+tk.E+tk.N+tk.S, padx=10, pady=5)

        button_show_drawing = ttk.Checkbutton(self.BUTTON_FRAME_2, variable=self.check_show_drawing, onvalue=1, offvalue=0, text='顯示已追踪路徑')
        button_show_drawing.grid(row=10, rowspan=2, column=1, sticky=tk.W+tk.E+tk.N+tk.S, padx=10, pady=5)

        # update changes
        if self.multi:
            pass
        else:
            pass
            self.update_track(0)
            # self.root.after(0, self.update_track, 0)

        # suggest default option
        print(self.suggest_ind)
        if self.suggest_ind[0][0] == 'fp':
            self.all_buttons[0].focus_force()
        elif self.suggest_ind[0][0] == 'new':
            self.all_buttons[1].focus_force()
        else:
            self.all_buttons[self.object_name[self.suggest_ind[0][0]]['ind'] + 2].focus_force()

        self.update_label()
        self.update_draw()

        # bind key and corresponding function
        self.root.bind('<Return>', self.on_return)
        self.root.bind('<z>', self.undo)
        self.root.bind('<BackSpace>', self.undo)
        self.root.bind('<Escape>', self.on_close)
        self.root.bind('<h>', self.on_settings)
        self.root.bind('1', self.on_key)
        self.root.bind('2', self.on_key)
        self.root.bind('3', self.on_key)
        self.root.bind('4', self.on_key)
        self.root.bind('<Delete>', self.on_key)
        self.root.bind('d', self.on_key)
        self.root.bind('n', self.on_key)
        self.root.bind('l', self.on_key)
        self.root.bind('s', self.break_loop)
        self.root.mainloop()