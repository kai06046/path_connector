import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import askyesno, askokcancel, showerror, showwarning, showinfo
from tkinter.filedialog import askopenfilename
import pickle

class Interface(object):

    # show warning
    def msg(self, string):
        self.temp_root = tk.Tk()
        self.temp_root.withdraw()
        showinfo('Info', string)
        self.temp_root.destroy()
        self.temp_root.mainloop()

    # confirm leave
    def on_close(self, event=None):
        if askokcancel('離開', '你確定要關閉程式了嗎？'):
            if askyesno('存檔', '你要把操作結果存檔嗎？') and len(self.undo_records) > 1:
                pickle.dump(self.undo_records, open( "%s.dat" % self.video_path.split('.avi')[0], "wb" ) )
                print('file saved.')
            self.root.destroy()

    # confirm for replacement
    def ask_yes_no(self, clr, title='確認', icontype='warning'):
        string = '%s 在本幀已經有被分配的 bounding box 咯!\n你確定要取代原本的嗎？' % clr
        result = askyesno(title, string, icon=icontype)

        return result

    # ask for desired file name
    def get_path(self, label=None):
        path = askopenfilename(title='請選擇影像路徑', filetypes=[('video file (*.avi;*.mp4)','*.avi;*.mp4')])

        if path != "":
            self.video_path = path
            if label is not None:
                label.configure(text='%s' % self.video_path.split('/')[-1])

    def pop_msg(self):
        self.temp_root = tk.Tk()
        label = tk.Label(self.temp_root, text='Calculating...please wait...')
        label.pack()
        self.temp_root.mainloop()

    def setting(self):
        settings_root = tk.Tk()
        tk.Grid.rowconfigure(settings_root, 0, weight=1)
        tk.Grid.columnconfigure(settings_root, 0, weight=1)

        def exit(event):
            settings_root.destroy()

        self.center(settings_root)
        settings_root.focus_force()
        settings_root.title('設定')

        ACTION = ['標註對應的目標 (a/b/c/d)', '誤判', '新目標', '返回', '前一幀', '後一幀', '前五幀', '後五幀', '進入 Manual Label 模式', '回到需被標註的幀數/離開 Manual Label', '設定']
        HOTKEY = ['1/2/3/4', 'd/DELETE', 'n', 'u/BACKSPACE', 'LEFT', 'RIGHT', 'PAGE DOWN', 'PAGE UP', 'l', 'ENTER', 'h']

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
