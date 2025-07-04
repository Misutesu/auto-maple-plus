"""A module for tracking useful in-game information."""

import asyncio
import base64
import json
import threading
import time

import cv2
import numpy as np
import websockets

from src.common import config, utils

MINIMAP_LEFT_BORDER = 9
MINIMAP_TOP_BORDER = 9
MINIMAP_RIGHT_BORDER = 9
MINIMAP_BOTTOM_BORDER = 9

# The top-left and bottom-right corners of the minimap
MM_TL_TEMPLATE = cv2.imread("assets/minimap_tl_template.png", 0)
MM_BR_TEMPLATE = cv2.imread("assets/minimap_br_template.png", 0)

MMT_HEIGHT = max(MM_TL_TEMPLATE.shape[0], MM_BR_TEMPLATE.shape[0])
MMT_WIDTH = max(MM_TL_TEMPLATE.shape[1], MM_BR_TEMPLATE.shape[1])

# The player's symbol on the minimap
PLAYER_TEMPLATE = cv2.imread("assets/player_template.png", 0)
PT_HEIGHT, PT_WIDTH = PLAYER_TEMPLATE.shape


# 全局变量存储从 WebSocket 接收到的帧
ws_frame = None


class ImageDisplayServer:
    def __init__(self, host="0.0.0.0", port=39999):
        self.host = host
        self.port = port
        self.clients = set()
        self.running = False
        self.server = None
        self.reconnect_delay = 1  # 重连延迟（秒）

    async def handle_client(self, websocket):
        """处理客户端连接"""
        self.clients.add(websocket)
        client_id = id(websocket)
        print(f"新客户端连接: {client_id}")

        try:
            async for message in websocket:
                await self.process_message(message)
        except websockets.exceptions.ConnectionClosed:
            print(f"客户端 {client_id} 连接断开")
        except Exception as e:
            print(f"客户端 {client_id} 处理错误: {e}")
        finally:
            self.clients.remove(websocket)
            print(f"客户端断开连接: {client_id}")
            if len(self.clients) == 0:
                print("所有客户端已断开，等待新客户端连接...")

    async def process_message(self, message):
        """处理接收到的消息"""
        global ws_frame
        try:
            data = json.loads(message)

            if data.get("type") == "frame":
                # 解码base64图片数据
                frame_data = base64.b64decode(data["data"])
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is not None:
                    # 将接收到的帧存储到全局变量中
                    ws_frame = frame
                    # 显示时间戳
                    timestamp = data.get("timestamp", 0)
                    # print(f"收到frame，时间戳: {timestamp:.3f}")
                else:
                    print("无法解码图片数据")
            else:
                print(f"收到未知消息类型: {data.get('type', 'unknown')}")

        except json.JSONDecodeError:
            print("无效的JSON消息")
        except Exception as e:
            print(f"处理消息时出错: {e}")

    async def start(self):
        """启动WebSocket服务器"""
        self.running = True
        print(f"WebSocket服务器启动在 ws://{self.host}:{self.port}")

        while self.running:
            try:
                async with websockets.serve(
                    self.handle_client, self.host, self.port
                ) as server:
                    self.server = server
                    print("等待客户端连接...")
                    await asyncio.Future()  # 运行直到被中断
            except Exception as e:
                print(f"服务器错误: {e}")
                if self.running:
                    print(f"等待 {self.reconnect_delay} 秒后重新启动服务器...")
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    break

    def stop(self):
        """停止服务器"""
        self.running = False
        if self.server:
            self.server.close()
        print("服务器已停止")


class Capture:
    """
    A class that tracks player position and various in-game events. It constantly updates
    the config module with information regarding these events. It also annotates and
    displays the minimap in a pop-up window.
    """

    def __init__(self):
        """Initializes this Capture object's main thread."""

        config.capture = self

        self.frame = None
        self.minimap = {}
        self.minimap_ratio = 1
        self.minimap_sample = None
        self.window = {"left": 0, "top": 0, "width": 1366, "height": 768}

        self.server = ImageDisplayServer(host="0.0.0.0", port=39999)
        self.ready = False
        self.calibrated = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True

    def start(self):
        """Starts this Capture's thread."""

        print("\n[~] Started video capture")
        # 启动 WebSocket 服务器
        server_thread = threading.Thread(target=self._start_server)
        server_thread.daemon = True
        server_thread.start()
        self.thread.start()

    def _start_server(self):
        """在单独的线程中启动 WebSocket 服务器"""
        asyncio.run(self.server.start())

    def _main(self):
        """Constantly monitors the player's position and in-game events."""

        while True:
            if ws_frame is None:
                time.sleep(0.01)  # 等待帧数据
                continue

            self.frame = ws_frame.copy()
            tl, _ = utils.single_match(self.frame, MM_TL_TEMPLATE)
            _, br = utils.single_match(self.frame, MM_BR_TEMPLATE)
            mm_tl = (tl[0] + MINIMAP_BOTTOM_BORDER, tl[1] + MINIMAP_TOP_BORDER)
            mm_br = (
                max(mm_tl[0] + PT_WIDTH, br[0] - MINIMAP_BOTTOM_BORDER),
                max(mm_tl[1] + PT_HEIGHT, br[1] - MINIMAP_BOTTOM_BORDER),
            )
            self.minimap_ratio = (mm_br[0] - mm_tl[0]) / (mm_br[1] - mm_tl[1])
            self.minimap_sample = self.frame[mm_tl[1] : mm_br[1], mm_tl[0] : mm_br[0]]
            self.calibrated = True

            while True:
                if not self.calibrated:
                    break

                if ws_frame is None:
                    time.sleep(0.01)  # 等待帧数据
                    continue

                self.frame = ws_frame.copy()

                # Crop the frame to only show the minimap
                minimap = self.frame[mm_tl[1] : mm_br[1], mm_tl[0] : mm_br[0]]

                # Determine the player's position
                player = utils.multi_match(minimap, PLAYER_TEMPLATE, threshold=0.8)
                if player:
                    config.player_pos = utils.convert_to_relative(player[0], minimap)

                # Package display information to be polled by GUI
                self.minimap = {
                    "minimap": minimap,
                    "rune_active": getattr(config.bot, 'rune_active', False) if config.bot else False,
                    "rune_pos": getattr(config.bot, 'rune_pos', None) if config.bot else None,
                    "path": config.path,
                    "player_pos": config.player_pos,
                }

                if not self.ready:
                    self.ready = True
                time.sleep(0.001)
