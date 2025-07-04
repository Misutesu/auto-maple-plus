"""A module for simulating low-level keyboard and mouse key presses."""

import ctypes
import time
from ctypes import wintypes
from random import random

from src.common.box_utils import DHZBOX

key_type = 3

user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

MAPVK_VK_TO_VSC = 0

# https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes?redirectedfrom=MSDN
KEY_MAP = {
    "left": 0x25,  # Arrow keys
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "backspace": 0x08,  # Special keys
    "tab": 0x09,
    "enter": 0x0D,
    "shift": 0x10,
    "ctrl": 0x11,
    "alt": 0x12,
    "caps lock": 0x14,
    "esc": 0x1B,
    "space": 0x20,
    "page up": 0x21,
    "page down": 0x22,
    "end": 0x23,
    "home": 0x24,
    "insert": 0x2D,
    "delete": 0x2E,
    "0": 0x30,  # Numbers
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "5": 0x35,
    "6": 0x36,
    "7": 0x37,
    "8": 0x38,
    "9": 0x39,
    "a": 0x41,  # Letters
    "b": 0x42,
    "c": 0x43,
    "d": 0x44,
    "e": 0x45,
    "f": 0x46,
    "g": 0x47,
    "h": 0x48,
    "i": 0x49,
    "j": 0x4A,
    "k": 0x4B,
    "l": 0x4C,
    "m": 0x4D,
    "n": 0x4E,
    "o": 0x4F,
    "p": 0x50,
    "q": 0x51,
    "r": 0x52,
    "s": 0x53,
    "t": 0x54,
    "u": 0x55,
    "v": 0x56,
    "w": 0x57,
    "x": 0x58,
    "y": 0x59,
    "z": 0x5A,
    "f1": 0x70,  # Functional keys
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    "num lock": 0x90,
    "scroll lock": 0x91,
    ";": 0xBA,  # Special characters
    "=": 0xBB,
    ",": 0xBC,
    "-": 0xBD,
    ".": 0xBE,
    "/": 0xBF,
    "`": 0xC0,
    "[": 0xDB,
    "\\": 0xDC,
    "]": 0xDD,
    "'": 0xDE,
}

BOX_KEY_MAP = {
    # 方向键
    "left": "KEY_LEFT",  # [1,2,5](@ref)
    "up": "KEY_UP",  # [1,5,10](@ref)
    "right": "KEY_RIGHT",  # [1,5,10](@ref)
    "down": "KEY_DOWN",  # [1,5,10](@ref)
    # 特殊功能键
    "backspace": "KEY_BACKSPACE",  # [1,3,8](@ref)
    "tab": "KEY_TAB",  # [1,3](@ref)
    "enter": "KEY_ENTER",  # [1,3](@ref)
    "shift": "KEY_LEFTSHIFT",  # 无直接匹配（分左右键）
    "ctrl": "KEY_LEFTCTRL",  # 无直接匹配（分左右键）
    "alt": "KEY_LEFTALT",  # 无直接匹配（分左右键）
    "caps lock": "KEY_CAPSLOCK",  # [1,5](@ref)
    "esc": "KEY_ESC",  # [1,5](@ref)
    "space": "KEY_SPACE",  # [1,5](@ref)
    "page up": "KEY_PAGEUP",  # [1,3](@ref)
    "page down": "KEY_PAGEDOWN",  # [1,3](@ref)
    "end": "KEY_END",  # [1,3](@ref)
    "home": "KEY_HOME",  # [1,3](@ref)
    "insert": "KEY_INSERT",  # [1,3](@ref)
    "delete": "KEY_DELETE",  # [1,3](@ref)
    # 数字键
    "0": "KEY_0",
    "1": "KEY_1",
    "2": "KEY_2",
    "3": "KEY_3",
    "4": "KEY_4",
    "5": "KEY_5",
    "6": "KEY_6",
    "7": "KEY_7",
    "8": "KEY_8",
    "9": "KEY_9",  # [1,9](@ref)
    # 字母键
    "a": "KEY_A",
    "b": "KEY_B",
    "c": "KEY_C",
    "d": "KEY_D",
    "e": "KEY_E",
    "f": "KEY_F",
    "g": "KEY_G",
    "h": "KEY_H",
    "i": "KEY_I",
    "j": "KEY_J",
    "k": "KEY_K",
    "l": "KEY_L",
    "m": "KEY_M",
    "n": "KEY_N",
    "o": "KEY_O",
    "p": "KEY_P",
    "q": "KEY_Q",
    "r": "KEY_R",
    "s": "KEY_S",
    "t": "KEY_T",
    "u": "KEY_U",
    "v": "KEY_V",
    "w": "KEY_W",
    "x": "KEY_X",
    "y": "KEY_Y",
    "z": "KEY_Z",  # [1,4](@ref)
    # 功能键
    "f1": "KEY_F1",
    "f2": "KEY_F2",
    "f3": "KEY_F3",
    "f4": "KEY_F4",
    "f5": "KEY_F5",
    "f6": "KEY_F6",
    "f7": "KEY_F7",
    "f8": "KEY_F8",
    "f9": "KEY_F9",
    "f10": "KEY_F10",
    "f11": "KEY_F11",
    "f12": "KEY_F12",  # [1,4](@ref)
    "num lock": "KEY_NUMLOCK",  # [1,3](@ref)
    "scroll lock": "KEY_SCROLLLOCK",  # [1,3](@ref)
    # 特殊符号键
    ";": "KEY_SEMICOLON",  # [1,10](@ref)
    "=": "KEY_EQUAL",  # [1,10](@ref)
    ",": "KEY_COMMA",  # [1,10](@ref)
    "-": "KEY_MINUS",  # [1,10](@ref)
    ".": "KEY_DOT",  # [1,10](@ref)
    "/": "KEY_SLASH",  # [1,10](@ref)
    "`": "KEY_GRAVE",  # [1,10](@ref)
    "[": "KEY_LEFTBRACE",  # [1,10](@ref)
    "\\": "KEY_BACKSLASH",  # [1,10](@ref)
    "]": "KEY_RIGHTBRACE",  # [1,10](@ref)
    "'": "KEY_APOSTROPHE",  # [1,10](@ref)
}

#################################
#     C Struct Definitions      #
#################################

wintypes.ULONG_PTR = wintypes.WPARAM

if key_type == 3:
    box = DHZBOX("192.168.50.31", 8888, 88)


class KeyboardInput(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG_PTR),
    )

    def __init__(self, *args, **kwargs):
        super(KeyboardInput, self).__init__(*args, **kwargs)
        if not self.dwFlags & KEYEVENTF_UNICODE:
            self.wScan = user32.MapVirtualKeyExW(self.wVk, MAPVK_VK_TO_VSC, 0)


class MouseInput(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG_PTR),
    )


class HardwareInput(ctypes.Structure):
    _fields_ = (
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    )


class Input(ctypes.Structure):
    class _Input(ctypes.Union):
        _fields_ = (("ki", KeyboardInput), ("mi", MouseInput), ("hi", HardwareInput))

    _anonymous_ = ("_input",)
    _fields_ = (("type", wintypes.DWORD), ("_input", _Input))


LPINPUT = ctypes.POINTER(Input)


def err_check(result, _, args):
    if result == 0:
        raise ctypes.WinError(ctypes.get_last_error())
    else:
        return args


user32.SendInput.errcheck = err_check
user32.SendInput.argtypes = (wintypes.UINT, LPINPUT, ctypes.c_int)


#################################
#           Functions           #
#################################
def key_down(key):
    """
    Simulates a key-down action. Can be cancelled by Bot.toggle_enabled.
    :param key:     The key to press.
    :return:        None
    """

    key = key.lower()
    if key not in KEY_MAP.keys():
        print(f"Invalid keyboard input: '{key}'.")
    else:
        if key_type == 2:
            keycode = KEY_MAP[key]
            x = Input(type=INPUT_KEYBOARD, ki=KeyboardInput(wVk=keycode))
            user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))
        elif key_type == 3:
            key_str = BOX_KEY_MAP[key]
            box.keydown(key_str)
        else:
            print(f"Unknown key type: '{key}'.")


def key_up(key):
    """
    Simulates a key-up action. Cannot be cancelled by Bot.toggle_enabled.
    This is to ensure no keys are left in the 'down' state when the program pauses.
    :param key:     The key to press.
    :return:        None
    """

    key = key.lower()
    if key not in KEY_MAP.keys():
        print(f"Invalid keyboard input: '{key}'.")
    else:
        if key_type == 2:
            keycode = KEY_MAP[key]
            x = Input(
                type=INPUT_KEYBOARD,
                ki=KeyboardInput(wVk=keycode, dwFlags=KEYEVENTF_KEYUP),
            )
            user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))
        elif key_type == 3:
            key_str = BOX_KEY_MAP[key]
            box.keyup(key_str)
        else:
            print(f"Unknown key type: '{key}'.")


def press(key, n=1, down_time=0.05, up_time=0.1):
    """
    Presses KEY N times, holding it for DOWN_TIME seconds, and releasing for UP_TIME seconds.
    :param key:         The keyboard input to press.
    :param n:           Number of times to press KEY.
    :param down_time:   Duration of down-press (in seconds).
    :param up_time:     Duration of release (in seconds).
    :return:            None
    """

    key = key.lower()
    for _ in range(n):
        key_down(key)
        time.sleep(down_time * (0.8 + 0.4 * random()))
        key_up(key)
        time.sleep(up_time * (0.8 + 0.4 * random()))
