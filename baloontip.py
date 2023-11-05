# -- coding: utf-8 --

# Credits: Jason Chen (https://github.com/wontoncc)
# Gist: https://gist.github.com/wontoncc/1808234
# Edited by Simone Angeloni
 
from win32api import *
from win32gui import *
import win32con
import time
 

class WindowsBalloonTip:
    def __init__(self, title, msg, icon_path, duration):
        message_map = {
                win32con.WM_DESTROY: self.OnDestroy,
        }
        
        # Register the Window class.
        wc = WNDCLASS()
        hinst = wc.hInstance = GetModuleHandle(None)
        wc.lpszClassName = "PythonTaskbar"
        wc.lpfnWndProc = message_map # could also specify a wndproc.
        classAtom = RegisterClass(wc)

        # Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = CreateWindow( classAtom, "Taskbar", style, \
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, \
                0, 0, hinst, None)
        UpdateWindow(self.hwnd)

        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        try:
            hicon = LoadImage(hinst, icon_path, win32con.IMAGE_ICON, 0, 0, icon_flags)
        except:
            hicon = LoadIcon(0, win32con.IDI_APPLICATION)
          
        Shell_NotifyIcon(NIM_ADD, (self.hwnd, 0, NIF_ICON | NIF_MESSAGE | NIF_TIP, win32con.WM_USER+20, hicon, "tooltip"))
        Shell_NotifyIcon(NIM_MODIFY, (self.hwnd, 0, NIF_INFO, win32con.WM_USER+20, hicon, "Balloon  tooltip", title, 200, msg))

        time.sleep(duration)
        DestroyWindow(self.hwnd)


    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        Shell_NotifyIcon(NIM_DELETE, nid)
        PostQuitMessage(0)
