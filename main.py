import mysql.connector
from collections import defaultdict
import re
from datetime import datetime

def connect_to_database(database_name=None):
    """连接到数据库，如果database_name为None，则不指定数据库"""
    try:
        connection = mysql.connector.connect(
            host="10.134.84.197",
            user="root",
            password="zhang3660628",
            database=database_name
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def create_new_database():
    """创建新的数据库和表"""
    connection = connect_to_database()
    if not connection:
        return False

    cursor = connection.cursor()
    try:
        # 删除已存在的数据库
        cursor.execute("DROP DATABASE IF EXISTS plane_data_new")
        
        # 创建新数据库
        cursor.execute("CREATE DATABASE plane_data_new")
        cursor.execute("USE plane_data_new")

        # 创建flights表
        cursor.execute("""
            CREATE TABLE flights (
                flight_id INT AUTO_INCREMENT PRIMARY KEY,
                callsign VARCHAR(20) NOT NULL,
                first_seen DATETIME,
                last_seen DATETIME,
                total_points INT DEFAULT 0,
                max_altitude FLOAT,
                min_altitude FLOAT,
                UNIQUE KEY unique_callsign (callsign)
            )
        """)

        # 创建track_points表
        cursor.execute("""
            CREATE TABLE track_points (
                point_id INT AUTO_INCREMENT PRIMARY KEY,
                flight_id INT,
                msg_time DATETIME,
                track_id VARCHAR(20),
                longitude VARCHAR(20),
                latitude VARCHAR(20),
                altitude FLOAT,
                speed_x VARCHAR(20),
                speed_y VARCHAR(20),
                speed_z VARCHAR(20),
                raw_data TEXT,
                FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
            )
        """)

        connection.commit()
        print("数据库和表创建成功！")
        return True
    except mysql.connector.Error as err:
        print(f"Error creating database and tables: {err}")
        return False
    finally:
        cursor.close()
        connection.close()

def parse_track_data(data_bytes):
    """解析数据字节，提取所有字段"""
    try:
        data_str = data_bytes.decode('utf-8')
        match = re.match(r'\((.*?)\)', data_str)
        if not match:
            return None
            
        content = match.group(1)
        pairs = content.split(' -')
        data_dict = {}
        
        for pair in pairs:
            if ' ' in pair:
                key, value = pair.strip().split(' ', 1)
                data_dict[key] = value
                
        return data_dict
    except Exception as e:
        print(f"Error parsing data: {e}")
        return None

def check_altitude(track_data, max_altitude=2400):
    """检查高度是否在指定值以下"""
    try:
        altitude = float(track_data.get('FL', '0'))
        return altitude <= max_altitude
    except (ValueError, TypeError):
        return False

def check_callsign(track_data, prefix='B'):
    """检查航班号是否以指定前缀开头"""
    callsign = track_data.get('CALLSIGN', '')
    return callsign.startswith(prefix)

def get_all_tables(connection):
    """获取数据库中所有表名"""
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    cursor.close()
    return sorted(tables)

def parse_datetime(msg_time_str):
    """解析消息时间字符串为datetime对象"""
    try:
        return datetime.strptime(msg_time_str, "%Y%m%d%H%M%S%f")
    except ValueError:
        return None

def is_valid_callsign(callsign):
    """检查航班号是否有效"""
    if not callsign or len(callsign.strip()) == 0:
        return False
    # 航班号应该只包含字母和数字
    return bool(re.match(r'^[A-Z0-9]+$', callsign))

def is_valid_coordinate(longitude, latitude):
    """检查经纬度是否有效"""
    try:
        # 提取数值部分
        lon = float(re.sub(r'[EW]', '', longitude))
        lat = float(re.sub(r'[NS]', '', latitude))
        
        # 检查经纬度范围
        if not (0 <= lon <= 180 and 0 <= lat <= 90):
            return False
            
        # 检查格式（E/W 和 N/S）
        if not (longitude.startswith('E') or longitude.startswith('W')):
            return False
        if not (latitude.startswith('N') or latitude.startswith('S')):
            return False
            
        return True
    except (ValueError, TypeError):
        return False

def is_valid_speed(speed):
    """检查速度是否有效"""
    try:
        # 提取数值部分（去掉N/S/E/W等前缀）
        speed_val = float(re.sub(r'[NSEW]', '', speed))
        return -1000 <= speed_val <= 1000  # 设置一个合理的速度范围
    except (ValueError, TypeError):
        return False

def is_valid_altitude(altitude):
    """检查高度是否有效"""
    try:
        alt = float(altitude)
        return 0 <= alt <= 50000  # 设置一个合理的高度范围（单位：英尺）
    except (ValueError, TypeError):
        return False

def is_valid_track_data(track_data):
    """检查航迹数据是否有效"""
    if not track_data:
        return False
        
    # 检查必要字段是否存在
    required_fields = ['CALLSIGN', 'MSGTIME', 'LONGTD', 'LATTD', 'FL']
    if not all(field in track_data for field in required_fields):
        return False
    
    # 检查航班号
    if not is_valid_callsign(track_data['CALLSIGN']):
        return False
    
    # 检查经纬度
    if not is_valid_coordinate(track_data['LONGTD'], track_data['LATTD']):
        return False
    
    # 检查高度
    if not is_valid_altitude(track_data['FL']):
        return False
    
    # 检查速度（如果存在）
    for speed_field in ['SPDX', 'SPDY']:
        if speed_field in track_data and not is_valid_speed(track_data[speed_field]):
            return False
    
    # 检查垂直速度（处理两种可能的参数名）
    vertical_speed = track_data.get('SPDZGPS', track_data.get('SPDZ', None))
    if vertical_speed is not None and not is_valid_speed(vertical_speed):
        return False
    
    # 检查时间戳格式
    try:
        datetime.strptime(track_data['MSGTIME'], "%Y%m%d%H%M%S%f")
    except ValueError:
        return False
    
    return True

def process_and_store_table_data(source_connection, new_connection, table_name):
    """处理单个表的数据并存储"""
    print(f"\n正在处理表: {table_name}")
    source_cursor = source_connection.cursor(dictionary=True)
    new_cursor = new_connection.cursor()
    
    try:
        # 分批次查询数据
        batch_size = 10000  # 每次处理10000条数据
        offset = 0
        total_processed = 0
        total_valid = 0
        total_invalid = 0
        
        while True:
            # 查询一批数据
            query = f"SELECT * FROM `{table_name}` LIMIT {batch_size} OFFSET {offset}"
            source_cursor.execute(query)
            rows = source_cursor.fetchall()
            
            if not rows:
                break
                
            # 处理这批数据
            flight_data = defaultdict(list)
            filtered_count = 0
            invalid_count = 0
            
            for row in rows:
                total_processed += 1
                track_data = parse_track_data(row['data'])
                
                # 检查数据有效性
                if not is_valid_track_data(track_data):
                    invalid_count += 1
                    total_invalid += 1
                    continue
                
                # 检查筛选条件（高度和航班号前缀）
                if (check_altitude(track_data) and 
                    check_callsign(track_data)):
                    flight_data[track_data['CALLSIGN']].append(track_data)
                    filtered_count += 1
                    total_valid += 1
            
            # 存储这批数据
            for callsign, track_points in flight_data.items():
                if not track_points:
                    continue

                # 获取时间范围和高度范围
                msg_times = [parse_datetime(point.get('MSGTIME', '')) for point in track_points if point.get('MSGTIME')]
                msg_times = [t for t in msg_times if t is not None]
                
                altitudes = [float(point.get('FL', '0')) for point in track_points if point.get('FL')]
                
                if not msg_times or not altitudes:
                    continue

                first_seen = min(msg_times)
                last_seen = max(msg_times)
                total_points = len(track_points)
                max_altitude = max(altitudes)
                min_altitude = min(altitudes)

                # 插入或更新航班记录
                new_cursor.execute("""
                    INSERT INTO flights (
                        callsign, first_seen, last_seen, total_points,
                        max_altitude, min_altitude
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        first_seen = LEAST(first_seen, %s),
                        last_seen = GREATEST(last_seen, %s),
                        total_points = total_points + %s,
                        max_altitude = GREATEST(max_altitude, %s),
                        min_altitude = LEAST(min_altitude, %s)
                """, (
                    callsign, first_seen, last_seen, total_points,
                    max_altitude, min_altitude,
                    first_seen, last_seen, total_points,
                    max_altitude, min_altitude
                ))
                
                # 获取flight_id
                if new_cursor.lastrowid:
                    flight_id = new_cursor.lastrowid
                else:
                    new_cursor.execute("SELECT flight_id FROM flights WHERE callsign = %s", (callsign,))
                    flight_id = new_cursor.fetchone()[0]

                # 插入航迹点数据
                for point in track_points:
                    msg_time = parse_datetime(point.get('MSGTIME', ''))
                    if not msg_time:
                        continue

                    try:
                        altitude = float(point.get('FL', '0'))
                    except (ValueError, TypeError):
                        altitude = 0

                    # 获取垂直速度（优先使用SPDZGPS，如果没有则使用SPDZ）
                    vertical_speed = point.get('SPDZGPS', point.get('SPDZ', ''))

                    new_cursor.execute("""
                        INSERT INTO track_points (
                            flight_id, msg_time, track_id, longitude, latitude,
                            altitude, speed_x, speed_y, speed_z, raw_data
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        flight_id,
                        msg_time,
                        point.get('TRACKID', ''),
                        point.get('LONGTD', ''),
                        point.get('LATTD', ''),
                        altitude,
                        point.get('SPDX', ''),
                        point.get('SPDY', ''),
                        vertical_speed,
                        str(point)
                    ))

            new_connection.commit()
            print(f"已处理 {offset + len(rows)} 条记录:")
            print(f"  - 符合条件的记录: {filtered_count} 条")
            print(f"  - 无效数据: {invalid_count} 条")
            offset += batch_size
            
        # 打印该表的总结信息
        print(f"\n表 {table_name} 处理完成:")
        print(f"  - 总处理记录: {total_processed}")
        print(f"  - 有效记录: {total_valid}")
        print(f"  - 无效记录: {total_invalid}")
        print(f"  - 有效率: {(total_valid/total_processed*100):.2f}%")
            
    except mysql.connector.Error as err:
        print(f"处理表 {table_name} 时发生错误: {err}")
        new_connection.rollback()
    finally:
        source_cursor.close()
        new_cursor.close()

def main():
    # 创建新数据库和表
    if not create_new_database():
        print("创建新数据库失败")
        return

    # 连接到原数据库和新数据库
    source_connection = connect_to_database("planedata")
    new_connection = connect_to_database("plane_data_new")
    
    if not source_connection or not new_connection:
        print("数据库连接失败")
        return

    try:
        # 获取所有表名
        tables = get_all_tables(source_connection)
        total_tables = len(tables)
        
        print(f"共找到 {total_tables} 个表")
        print("筛选条件: 高度 <= 2400 且 航班号以'B'开头")
        
        # 逐个处理每个表
        for i, table in enumerate(tables, 1):
            print(f"\n处理进度: {i}/{total_tables}")
            process_and_store_table_data(source_connection, new_connection, table)
            
        print("\n所有数据迁移完成！")
        
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        source_connection.close()
        new_connection.close()

if __name__ == "__main__":
    main()
