import socket
import select
from datetime import datetime

# 配置参数
LISTEN_PORT = 8888        # 本地监听端口
TARGET_IP = "192.168.8.88"  # 目标服务器IP
TARGET_PORT = 8888        # 目标服务器端口
RELAY_PORT = 8889         # 用于与目标服务器通信的本地端口

def main():
    try:
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_socket.bind(("0.0.0.0", LISTEN_PORT))

        relay_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        relay_socket.bind(("0.0.0.0", RELAY_PORT))
    except Exception as e:
        print(f"套接字初始化或绑定失败: {e}")
        return

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] UDP转发服务已启动")
    print(f"监听端口: {LISTEN_PORT} -> 转发目标: {TARGET_IP}:{TARGET_PORT}")

    # 记录最后通信的客户端地址
    last_client_addr = None

    while True:
        try:
            readable, _, _ = select.select([recv_socket, relay_socket], [], [])
            for sock in readable:
                if sock is recv_socket:
                    try:
                        data, client_addr = recv_socket.recvfrom(4096)
                        last_client_addr = client_addr
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 收到来自 {client_addr} 的数据 ({len(data)}字节)")

                        # 转发数据到目标服务器
                        relay_socket.sendto(data, (TARGET_IP, TARGET_PORT))
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 已转发到 {TARGET_IP}:{TARGET_PORT}")
                    except Exception as e:
                        print(f"接收/转发客户端数据异常: {e}")
                elif sock is relay_socket:
                    try:
                        data, server_addr = relay_socket.recvfrom(4096)

                        # 只处理来自目标服务器的数据
                        if server_addr[0] == TARGET_IP:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 收到来自目标的响应 ({len(data)}字节)")

                            # 将响应返回给原始客户端
                            if last_client_addr:
                                recv_socket.sendto(data, last_client_addr)
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 已返回给客户端 {last_client_addr}")
                            else:
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 警告: 无有效客户端地址记录")
                    except Exception as e:
                        print(f"接收/转发目标服务器数据异常: {e}")
        except Exception as e:
            print(f"主循环异常: {e}")

if __name__ == "__main__":
    main()