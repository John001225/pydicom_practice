import customtkinter as ctk
from tkinter import filedialog, messagebox
import yt_dlp
import threading
import os
import sys

class YTDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title('YouTube Video/Music Downloader')
        self.geometry('600x550')
        ctk.set_appearance_mode('dark')

        # --UI setting--
        # title
        self.header = ctk.CTkLabel(self, text='YouTube Downloader', font=('Microsoft JhengHei', 24, 'bold'))
        self.header.pack(pady=20)

        # url enter area (multiple lines)
        self.url_label = ctk.CTkLabel(self, text='Please enter URL (one per line):')
        self.url_label.pack(anchor='w', padx=50)
        self.url_textbox = ctk.CTkTextbox(self, width=500, height=120)
        self.url_textbox.pack(pady=5)

        # format and quality selection area
        self.option_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.option_frame.pack(pady=10)
        
        self.type_var = ctk.StringVar(value='mp4')
        self.type_menu = ctk.CTkOptionMenu(self.option_frame, values=['mp4', 'mp3'], variable=self.type_var, width=120)
        self.type_menu.pack(side='left', padx=10)

        self.quality_var = ctk.StringVar(value='best quality')
        self.quality_menu = ctk.CTkOptionMenu(self.option_frame, values=['best quality', '1080p', '720p', '480p'], variable=self.quality_var, width=120)
        self.quality_menu.pack(side='left', padx=10)

        # check box for loundnorm
        self.check_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.check_frame.pack(pady=5)

        self.norm_var = ctk.BooleanVar(value=False)
        self.norm_checkbox = ctk.CTkCheckBox(
            self.check_frame,
            text='Automatic volume unification (will increase processing time)',
            variable=self.norm_var,
            font=('Microsoft JhengHei', 12)
        )
        self.norm_checkbox.pack()

        # save path
        self.path_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.path_frame.pack(pady=10)
        self.path_var = ctk.StringVar(value=os.getcwd())
        self.path_entry = ctk.CTkEntry(self.path_frame, textvariable=self.path_var, width=350)
        self.path_entry.pack(side='left', padx=5)
        self.path_btn = ctk.CTkButton(self.path_frame, text='change folder', command=self.select_path, width=100)
        self.path_btn.pack(side='left')

        # download button
        self.download_btn = ctk.CTkButton(self, text='start downloading', command=self.start_download_thread,
                                          fg_color='#24a0ed', hover_color='#007aac', font=('Microsoft JhengHei', 16, 'bold'))
        self.download_btn.pack(pady=20)

        # showing status
        self.status_label = ctk.CTkLabel(self, text='wait for command...', text_color='gray')
        self.status_label.pack()

    def select_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)


    def start_download_thread(self):
        # get all the urls and filter out blank lines
        urls = self.url_textbox.get('1.0', 'end-1c').split('\n')
        urls = [url.strip() for url in urls if url.strip()]

        folder = self.path_var.get()
        file_type = self.type_var.get()
        quality = self.quality_var.get()

        do_norm = self.norm_var.get()

        if not urls:
            messagebox.showwarning('warning', 'atleat enter one url')
            return
        
        # diable the button to prevent repeated clicks
        self.download_btn.configure(state='diabled')
        # start thread to download
        thread = threading.Thread(
            target=self.run_downloads, 
            args=(urls, folder, file_type, quality, do_norm))
        thread.daemon = True # 設定為守護執行緒，視窗關閉時會自動結束
        thread.start()

    def get_tool_path(self, filename):
        # 如果是打包後的環境，PyInstaller 會將檔案解壓縮到 _MEIPASS 臨時目錄
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, filename)
        # 如果是開發環境，則尋找當前目錄下的 ffmpeg.exe
        return os.path.abspath(filename)
    
    def run_downloads(self, urls, folder, file_type, quality, do_norm):
        # set the args of ty-dlp
        for i, url in enumerate(urls):
            self.status_label.configure(text=f'now downloading {i+1}/{len(urls)} videos...', text_color='yellow')
            
            # set the download args (core)
            ydl_opts = self.get_ydl_options(folder, file_type, quality, do_norm)

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                print(f'Error: {e}')
                continue

        self.after(0, self.finish_ui_update, len(urls))

    def finish_ui_update(self, count):
        # 這個函數會在主執行緒執行，所以可以安全呼叫 GUI 元件
        self.status_label.configure(text='All Downloading Tasks Finished!', text_color='green')
        self.download_btn.configure(state='normal')
        messagebox.showinfo('Finished', f'Complete {count} downloading tasks')


    def get_ydl_options(self, folder, file_type, quality, do_norm):
        # basic saving path and file format
        ffmpeg_path = self.get_tool_path('ffmpeg.exe')
        qjs_path = self.get_tool_path('qjs.exe')
        opts = {
            'outtmpl': f'{folder}/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': ffmpeg_path,
            'extra_js_runtimes': [f'quickjs:{qjs_path}'],
            'prefer_ffmpeg': True,
        }

        # volume normalize
        if do_norm:
            opts['postprocessor_args'] = {
                'ffmpeg': ['-af', 'loudnorm=I=-16:TP=-1.5:LRA=11']
            }

        if file_type == 'mp3':
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],

            })
        else:
            q_map = {
                '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]',
                '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]',
                '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]',
                'best quality': 'bestvideo+bestaudio/best',
            }
            opts['format'] = q_map.get(quality, 'bestvideo+bestaudio/best')
            opts['merge_utput_format'] = 'mp4'

        return opts
    
if __name__ == '__main__':
    app = YTDownloaderApp()
    app.mainloop()

