import asyncio
import base64
import json

import cv2
import numpy as np
import websockets


class ImageDisplayServer:
    def __init__(self, host='0.0.0.0', port=39999):
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
        try:
            data = json.loads(message)
            
            if data.get('type') == 'frame':
                # 解码base64图片数据
                frame_data = base64.b64decode(data['data'])
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # 显示图片
                    cv2.imshow('Received Frame', frame)
                    
                    # 检查按键
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        print("收到退出信号，正在关闭服务器...")
                        self.running = False
                        return
                    
                    # 显示时间戳
                    timestamp = data.get('timestamp', 0)
                    print(f"收到frame，时间戳: {timestamp:.3f}")
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
                async with websockets.serve(self.handle_client, self.host, self.port) as server:
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
        cv2.destroyAllWindows()
        if self.server:
            self.server.close()
        print("服务器已停止")


async def main():
    # 创建并启动服务器
    server = ImageDisplayServer(host='0.0.0.0', port=39999)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止服务器...")
        server.stop()
    except Exception as e:
        print(f"服务器运行错误: {e}")
        server.stop()


if __name__ == "__main__":
    asyncio.run(main()) 