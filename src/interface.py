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

    # ask question
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