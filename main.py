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
        # 直接从MSGTIME字符串解析完整的时间
        # 格式: YYYYMMDDHHmmssSSS
        year = int(msg_time_str[:4])
        month = int(msg_time_str[4:6])
        day = int(msg_time_str[6:8])
        hour = int(msg_time_str[8:10])
        minute = int(msg_time_str[10:12])
        second = int(msg_time_str[12:14])
        # 毫秒部分如果存在的话
        microsecond = int(msg_time_str[14:]) if len(msg_time_str) > 14 else 0
        
        return datetime(year, month, day, hour, minute, second, microsecond)
    except (ValueError, TypeError, IndexError) as e:
        print(f"Error parsing datetime from {msg_time_str}: {e}")
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
        # 检查是否为空或者只包含空格
        if not longitude or not latitude or longitude.isspace() or latitude.isspace():
            return False
            
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
    except (ValueError, TypeError, AttributeError):
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
        invalid_stats = {
            'empty_coordinates': 0,
            'invalid_coordinates': 0,
            'invalid_altitude': 0,
            'invalid_callsign': 0,
            'missing_fields': 0,
            'invalid_time': 0
        }
        
        # 用于批量插入的缓存
        flight_updates = {}  # 存储航班更新信息
        track_points_batch = []  # 存储航迹点批量插入数据
        
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
                
                # 详细的数据验证
                if not track_data:
                    invalid_stats['missing_fields'] += 1
                    invalid_count += 1
                    continue
                
                # 检查必要字段是否存在
                required_fields = ['CALLSIGN', 'MSGTIME', 'LONGTD', 'LATTD', 'FL']
                if not all(field in track_data for field in required_fields):
                    invalid_stats['missing_fields'] += 1
                    invalid_count += 1
                    continue
                
                # 检查航班号
                if not is_valid_callsign(track_data['CALLSIGN']):
                    invalid_stats['invalid_callsign'] += 1
                    invalid_count += 1
                    continue
                
                # 检查经纬度是否为空
                if not track_data['LONGTD'] or not track_data['LATTD'] or \
                   track_data['LONGTD'].isspace() or track_data['LATTD'].isspace():
                    invalid_stats['empty_coordinates'] += 1
                    invalid_count += 1
                    continue
                
                # 检查经纬度格式和范围
                if not is_valid_coordinate(track_data['LONGTD'], track_data['LATTD']):
                    invalid_stats['invalid_coordinates'] += 1
                    invalid_count += 1
                    continue
                
                # 检查高度
                if not is_valid_altitude(track_data['FL']):
                    invalid_stats['invalid_altitude'] += 1
                    invalid_count += 1
                    continue
                
                # 检查时间格式
                msg_time = parse_datetime(track_data['MSGTIME'])
                if not msg_time:
                    invalid_stats['invalid_time'] += 1
                    invalid_count += 1
                    continue
                
                # 检查筛选条件（高度和航班号前缀）
                if (check_altitude(track_data) and 
                    check_callsign(track_data)):
                    flight_data[track_data['CALLSIGN']].append((track_data, msg_time))
                    filtered_count += 1
                    total_valid += 1
            
            # 处理航班数据
            for callsign, track_points in flight_data.items():
                if not track_points:
                    continue

                # 获取时间范围和高度范围
                msg_times = [point[1] for point in track_points]
                altitudes = [float(point[0].get('FL', '0')) for point in track_points]
                
                if not msg_times or not altitudes:
                    continue

                first_seen = min(msg_times)
                last_seen = max(msg_times)
                total_points = len(track_points)
                max_altitude = max(altitudes)
                min_altitude = min(altitudes)

                # 更新航班信息缓存
                if callsign not in flight_updates:
                    flight_updates[callsign] = {
                        'first_seen': first_seen,
                        'last_seen': last_seen,
                        'total_points': total_points,
                        'max_altitude': max_altitude,
                        'min_altitude': min_altitude,
                        'points': []
                    }
                else:
                    existing = flight_updates[callsign]
                    existing['first_seen'] = min(existing['first_seen'], first_seen)
                    existing['last_seen'] = max(existing['last_seen'], last_seen)
                    existing['total_points'] += total_points
                    existing['max_altitude'] = max(existing['max_altitude'], max_altitude)
                    existing['min_altitude'] = min(existing['min_altitude'], min_altitude)
                
                # 添加航迹点到缓存
                flight_updates[callsign]['points'].extend(track_points)

            # 每处理50000条记录或最后一批数据时，执行批量插入
            if total_processed % 50000 == 0 or not rows:
                # 批量更新航班信息
                if flight_updates:
                    # 首先插入或更新航班信息
                    flight_values = []
                    for callsign, data in flight_updates.items():
                        flight_values.append((
                            callsign, 
                            data['first_seen'],
                            data['last_seen'],
                            data['total_points'],
                            data['max_altitude'],
                            data['min_altitude']
                        ))

                    # 批量插入或更新航班信息
                    new_cursor.executemany("""
                        INSERT INTO flights (
                            callsign, first_seen, last_seen, total_points,
                            max_altitude, min_altitude
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                            first_seen = LEAST(first_seen, VALUES(first_seen)),
                            last_seen = GREATEST(last_seen, VALUES(last_seen)),
                            total_points = total_points + VALUES(total_points),
                            max_altitude = GREATEST(max_altitude, VALUES(max_altitude)),
                            min_altitude = LEAST(min_altitude, VALUES(min_altitude))
                    """, flight_values)

                    # 获取所有航班的ID
                    callsign_list = list(flight_updates.keys())
                    format_strings = ','.join(['%s'] * len(callsign_list))
                    new_cursor.execute(
                        f"SELECT flight_id, callsign FROM flights WHERE callsign IN ({format_strings})",
                        callsign_list
                    )
                    flight_ids = {row['callsign']: row['flight_id'] for row in new_cursor.fetchall()}

                    # 准备航迹点数据进行批量插入
                    track_points_values = []
                    for callsign, data in flight_updates.items():
                        flight_id = flight_ids[callsign]
                        for point, msg_time in data['points']:
                            try:
                                altitude = float(point.get('FL', '0'))
                            except (ValueError, TypeError):
                                altitude = 0

                            vertical_speed = point.get('SPDZGPS', point.get('SPDZ', ''))
                            
                            track_points_values.append((
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

                    # 批量插入航迹点数据
                    if track_points_values:
                        new_cursor.executemany("""
                            INSERT INTO track_points (
                                flight_id, msg_time, track_id, longitude, latitude,
                                altitude, speed_x, speed_y, speed_z, raw_data
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, track_points_values)

                    # 提交事务
                    new_connection.commit()

                    # 清空缓存
                    flight_updates.clear()
                    track_points_values.clear()

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
        print("\n无效数据统计:")
        print(f"  - 空经纬度: {invalid_stats['empty_coordinates']}")
        print(f"  - 无效经纬度: {invalid_stats['invalid_coordinates']}")
        print(f"  - 无效高度: {invalid_stats['invalid_altitude']}")
        print(f"  - 无效航班号: {invalid_stats['invalid_callsign']}")
        print(f"  - 缺失字段: {invalid_stats['missing_fields']}")
        print(f"  - 无效时间: {invalid_stats['invalid_time']}")
            
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
