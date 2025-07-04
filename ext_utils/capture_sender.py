import argparse
import asyncio
import base64
import ctypes
import json
import os
import threading
import time
from ctypes import wintypes

import cv2
import mss
import mss.windows
import numpy as np
import websockets

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

# 全局变量用于控制线程
stop_capture = False
websocket_client = None


class WebSocketClient:
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.connected = False
        self.connection_thread = None
        self.lock = threading.Lock()
        self.loop = None  # 保存事件循环

    async def connect(self):
        try:
            self.ws = await websockets.connect(f"ws://{self.url}")
            self.connected = True
            print(f"WebSocket已连接到: ws://{self.url}")
        except Exception as e:
            self.ws = None
            self.connected = False
            print(f"WebSocket连接失败: {e}")

    async def _connection_manager(self):
        while not stop_capture:
            if not self.connected:
                await self.connect()
            await asyncio.sleep(1)

    def start_connection(self):
        def run_loop():
            loop = asyncio.new_event_loop()
            self.loop = loop  # 保存事件循环
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._connection_manager())

        self.connection_thread = threading.Thread(target=run_loop, daemon=True)
        self.connection_thread.start()

    async def send_frame(self, frame):
        if not self.connected or self.ws is None:
            return False
        try:
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_base64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
            message = {"type": "frame", "data": frame_base64, "timestamp": time.time()}
            await self.ws.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"发送frame失败: {e}")
            self.connected = False
            return False

    async def close(self):
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
        self.connected = False
        if self.connection_thread:
            self.connection_thread.join(timeout=2)


def capture_screen(window_name):
    """屏幕捕获线程函数"""
    global stop_capture, websocket_client

    mss.windows.CAPTUREBLT = 0

    while not stop_capture:
        try:
            hwnd = user32.FindWindowW(None, window_name)
            if not hwnd:
                time.sleep(0.5)
                continue
            # 检查窗口是否最小化
            if user32.IsIconic(hwnd):
                time.sleep(0.5)
                continue
            
            # 获取客户区域相对于窗口的位置
            client_rect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.pointer(client_rect))
            client_rect = (client_rect.left, client_rect.top, client_rect.right, client_rect.bottom)
            client_rect = tuple(max(0, x) for x in client_rect)

            # 将客户区域的左上角坐标转换为屏幕坐标
            point = wintypes.POINT()
            point.x = client_rect[0]  # 通常是0
            point.y = client_rect[1]  # 通常是0
            user32.ClientToScreen(hwnd, ctypes.pointer(point))
            
            left = max(point.x, 0)
            top = max(point.y, 0)
            
            width = max(client_rect[2] - client_rect[0], 0)
            height = max(client_rect[3] - client_rect[1], 0)
            
            with mss.mss() as sct:
                frame = np.array(
                    sct.grab(
                        {"left": left, "top": top, "width": width, "height": height}
                    )
                )
                # cv2.imwrite("tmp.png", frame)
                # cv2.imshow("frame", frame)
                # cv2.waitKey(1)
            if (
                frame is not None
                and websocket_client
                and websocket_client.connection_thread
                and websocket_client.loop
            ):
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        websocket_client.send_frame(frame), websocket_client.loop
                    )
                    future.result()
                except Exception as e:
                    pass
            time.sleep(0.01)
        except Exception as e:
            print(f"捕获屏幕失败: {e}")
            time.sleep(0.5)


def parse_args():
    parser = argparse.ArgumentParser(description="屏幕捕获WebSocket客户端")
    parser.add_argument(
        "--window",
        "-w",
        type=str,
        default="MapleStory",
        help="要捕获的窗口名称 (默认: MapleStory)",
    )
    parser.add_argument(
        "--websocket",
        "-ws",
        type=str,
        default="192.168.50.11:39999",
        help="WebSocket地址（如 127.0.0.1:39999）",
    )
    return parser.parse_args()


async def main():
    global stop_capture, websocket_client

    os.system("title OBS 31.0.4 - 配置文件:未命名 - 场景:未命名")

    # 解析命令行参数
    args = parse_args()

    # 创建WebSocket客户端
    websocket_client = WebSocketClient(args.websocket)

    # 启动WebSocket连接
    websocket_client.start_connection()

    # 等待连接建立
    await asyncio.sleep(1)

    if not websocket_client.connected:
        print("WebSocket连接失败，程序将继续运行但不发送frame")
    else:
        print(f"WebSocket已连接到: {args.websocket}")

    # 创建并启动屏幕捕获线程
    capture_thread = threading.Thread(
        target=capture_screen, args=(args.window,), daemon=True
    )
    capture_thread.start()

    print(f"屏幕捕获线程已启动，正在捕获窗口: {args.window}")
    print("按 Ctrl+C 停止程序")

    try:
        # 主线程等待
        while not stop_capture:
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        print("\n正在停止程序...")
        stop_capture = True
        capture_thread.join(timeout=2)
        await websocket_client.close()
        print("程序已停止")


if __name__ == "__main__":
    asyncio.run(main())
