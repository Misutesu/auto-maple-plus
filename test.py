import time
import cv2
import threading
import ctypes
import mss
import mss.windows
import numpy as np
from src.common import config, utils
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

frame = None
sct = None
window = {
    'left': 0,
    'top': 0,
    'width': 1366,
    'height': 768
}

mss.windows.CAPTUREBLT = 0

handle = user32.FindWindowW(None, 'MapleStory')
rect = wintypes.RECT()
user32.GetWindowRect(handle, ctypes.pointer(rect))
rect = (rect.left, rect.top, rect.right, rect.bottom)
rect = tuple(max(0, x) for x in rect)

window['left'] = rect[0]
window['top'] = rect[1]
window['width'] = rect[2] - rect[0]
window['height'] = rect[3] - rect[1]


def screenshot(delay=1):
    try:
        return np.array(sct.grab(window))
    except mss.exception.ScreenShotError:
        print(f'\n[!] Error while taking screenshot, retrying in {delay} second'
              + ('s' if delay != 1 else ''))
        time.sleep(delay)


with mss.mss() as sct:
    frame = screenshot()

print(utils.multi_match(frame, cv2.imread('assets/insidecashshop.png', 0), threshold=0.9) == [])
