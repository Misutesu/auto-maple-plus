"""A collection of functions and classes used across multiple modules."""

import math
import queue
import cv2
import threading
import numpy as np
from src.common import config, settings
from random import random


def run_if_enabled(function):
    """
    Decorator for functions that should only run if the bot is enabled.
    :param function:    The function to decorate.
    :return:            The decorated function.
    """

    def helper(*args, **kwargs):
        if config.enabled:
            return function(*args, **kwargs)

    return helper


def run_if_disabled(message=''):
    """
    Decorator for functions that should only run while the bot is disabled. If MESSAGE
    is not empty, it will also print that message if its function attempts to run when
    it is not supposed to.
    """

    def decorator(function):
        def helper(*args, **kwargs):
            if not config.enabled:
                return function(*args, **kwargs)
            elif message:
                print(message)

        return helper

    return decorator


def distance(a, b):
    """
    Applies the distance formula to two points.
    :param a:   The first point.
    :param b:   The second point.
    :return:    The distance between the two points.
    """

    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def separate_args(arguments):
    """
    Separates a given array ARGUMENTS into an array of normal arguments and a
    dictionary of keyword arguments.
    :param arguments:    The array of arguments to separate.
    :return:             An array of normal arguments and a dictionary of keyword arguments.
    """

    args = []
    kwargs = {}
    for a in arguments:
        a = a.strip()
        index = a.find('=')
        if index > -1:
            key = a[:index].strip()
            value = a[index + 1:].strip()
            kwargs[key] = value
        else:
            args.append(a)
    return args, kwargs


def single_match(frame, template):
    """
    Finds the best match within FRAME.
    :param frame:       The image in which to search for TEMPLATE.
    :param template:    The template to match with.
    :return:            The top-left and bottom-right positions of the best match.
    """

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF)
    _, _, _, top_left = cv2.minMaxLoc(result)
    w, h = template.shape[::-1]
    bottom_right = (top_left[0] + w, top_left[1] + h)
    return top_left, bottom_right

def single_match_new(frame, template, threshold=0.8):
    """
    从游戏画面图片中匹配某些元素，支持透明度处理

    :param frame: 游戏画面图片 (BGR格式)
    :param template: 模板图片，支持透明度 (BGRA格式)
    :param threshold: 匹配阈值，范围0-1，默认0.8
    :return: (top_left, bottom_right) 匹配元素的左上角和右下角坐标，如果未找到则返回None
    """

    # 快速参数检查
    if frame is None or template is None:
        return None

    # 快速获取模板图片的通道数 - 避免多次shape访问
    template_shape = template.shape
    if len(template_shape) == 2:
        # 灰度图，转换为BGR
        template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
        return _match_without_alpha_optimized(frame, template, threshold)
    elif len(template_shape) == 3:
        template_channels = template_shape[2]
        if template_channels == 3:
            # BGR格式
            return _match_without_alpha_optimized(frame, template, threshold)
        elif template_channels == 4:
            # BGRA格式
            return _match_with_alpha_optimized(frame, template, threshold)
        else:
            raise ValueError(f"不支持的模板图片格式，通道数: {template_channels}")
    else:
        raise ValueError(f"不支持的模板图片格式，维度数: {len(template_shape)}")

def _match_with_alpha_optimized(frame, template, threshold):
    """
    优化版本：处理带有透明度的模板匹配
    """
    # 分离BGRA通道 - 避免不必要的浮点运算
    bgr = template[:, :, :3].astype(np.uint8)
    alpha = template[:, :, 3].astype(np.uint8)
    
    # 创建掩码 - 使用整数比较避免浮点运算，转换为uint8类型
    mask = (alpha > 25).astype(np.uint8)  # 相当于 0.1 * 255

    # 确保frame也是uint8类型
    if frame.dtype != np.uint8:
        frame = frame.astype(np.uint8)

    # 如果frame是4通道（BGRA），转换为3通道（BGR）
    if len(frame.shape) == 3 and frame.shape[2] == 4:
        frame = frame[:, :, :3]

    # 使用更快的匹配算法 TM_CCOEFF_NORMED 替代 TM_CCORR_NORMED
    result = cv2.matchTemplate(frame, bgr, cv2.TM_CCOEFF_NORMED, mask=mask)

    # 找到最佳匹配位置
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    # 检查匹配度是否达到阈值
    if max_val >= threshold:
        top_left = max_loc
        h, w = template.shape[:2]
        bottom_right = (top_left[0] + w, top_left[1] + h)
        return top_left, bottom_right
    else:
        return None


def _match_without_alpha_optimized(frame, template, threshold):
    """
    优化版本：处理不带透明度的模板匹配
    """
    # 确保数据类型正确
    if frame.dtype != np.uint8:
        frame = frame.astype(np.uint8)
    if template.dtype != np.uint8:
        template = template.astype(np.uint8)
    
    # 如果frame是4通道（BGRA），转换为3通道（BGR）
    if len(frame.shape) == 3 and frame.shape[2] == 4:
        frame = frame[:, :, :3]
    
    # 如果template是4通道（BGRA），转换为3通道（BGR）
    if len(template.shape) == 3 and template.shape[2] == 4:
        template = template[:, :, :3]
    
    # 使用更快的匹配算法 TM_CCOEFF_NORMED
    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)

    # 找到最佳匹配位置
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    # 检查匹配度是否达到阈值
    if max_val >= threshold:
        top_left = max_loc
        h, w = template.shape[:2]
        bottom_right = (top_left[0] + w, top_left[1] + h)
        return top_left, bottom_right
    else:
        return None


# def single_match_new(frame, template, threshold=0.8):
#     """
#     从游戏画面图片中匹配某些元素，支持透明度处理

#     :param frame: 游戏画面图片 (BGR格式)
#     :param template: 模板图片，支持透明度 (BGRA格式)
#     :param threshold: 匹配阈值，范围0-1，默认0.8
#     :return: (top_left, bottom_right) 匹配元素的左上角和右下角坐标，如果未找到则返回None
#     """

#     # 检查输入参数
#     if frame is None or template is None:
#         return None

#     # 获取模板图片的通道数
#     template_channels = template.shape[2] if len(template.shape) > 2 else 1

#     # 如果模板是灰度图，转换为BGR
#     if template_channels == 1:
#         template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
#         template_channels = 3

#     # 如果模板有透明度通道 (BGRA)
#     if template_channels == 4:
#         return _match_with_alpha(frame, template, threshold)
#     # 如果模板是BGR格式
#     elif template_channels == 3:
#         return _match_without_alpha(frame, template, threshold)
#     else:
#         raise ValueError(f"不支持的模板图片格式，通道数: {template_channels}")


def _match_with_alpha(frame, template, threshold):
    """
    处理带有透明度的模板匹配
    """
    # 分离BGRA通道
    bgr = template[:, :, :3]
    alpha = template[:, :, 3] / 255.0  # 归一化到0-1

    # 创建掩码，只匹配非透明区域
    mask = alpha > 0.1  # 透明度阈值，可以调整

    # 使用掩码进行模板匹配
    result = cv2.matchTemplate(frame, bgr, cv2.TM_CCORR_NORMED, mask=mask.astype(np.uint8))

    # 找到最佳匹配位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 检查匹配度是否达到阈值
    if max_val >= threshold:
        top_left = max_loc
        h, w = template.shape[:2]
        bottom_right = (top_left[0] + w, top_left[1] + h)
        return top_left, bottom_right
    else:
        return None


def _match_without_alpha(frame, template, threshold):
    """
    处理不带透明度的模板匹配
    """
    # 使用归一化相关系数进行匹配
    result = cv2.matchTemplate(frame, template, cv2.TM_CCORR_NORMED)

    # 找到最佳匹配位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 检查匹配度是否达到阈值
    if max_val >= threshold:
        top_left = max_loc
        h, w = template.shape[:2]
        bottom_right = (top_left[0] + w, top_left[1] + h)
        return top_left, bottom_right
    else:
        return None


def multi_match(frame, template, threshold=0.95):
    """
    Finds all matches in FRAME that are similar to TEMPLATE by at least THRESHOLD.
    :param frame:       The image in which to search.
    :param template:    The template to match with.
    :param threshold:   The minimum percentage of TEMPLATE that each result must match.
    :return:            An array of matches that exceed THRESHOLD.
    """

    if template.shape[0] > frame.shape[0] or template.shape[1] > frame.shape[1]:
        return []
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)
    locations = list(zip(*locations[::-1]))
    results = []
    for p in locations:
        x = int(round(p[0] + template.shape[1] / 2))
        y = int(round(p[1] + template.shape[0] / 2))
        results.append((x, y))
    return results

def multi_match_new(frame, template, threshold=0.8, max_results=10):
    """
    从游戏画面图片中匹配多个相同元素

    :param frame: 游戏画面图片 (BGR格式)
    :param template: 模板图片，支持透明度 (BGRA格式)
    :param threshold: 匹配阈值，范围0-1，默认0.8
    :param max_results: 最大返回结果数量，默认10
    :return: [(top_left, bottom_right), ...] 匹配元素的坐标列表，如果未找到则返回空列表
    """
    # 快速参数检查
    if frame is None or template is None:
        return []

    # 快速获取模板图片的通道数
    template_shape = template.shape
    if len(template_shape) == 2:
        # 灰度图，转换为BGR
        template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
        return _multi_match_without_alpha(frame, template, threshold, max_results)
    elif len(template_shape) == 3:
        template_channels = template_shape[2]
        if template_channels == 3:
            # BGR格式
            return _multi_match_without_alpha(frame, template, threshold, max_results)
        elif template_channels == 4:
            # BGRA格式
            return _multi_match_with_alpha(frame, template, threshold, max_results)
        else:
            raise ValueError(f"不支持的模板图片格式，通道数: {template_channels}")
    else:
        raise ValueError(f"不支持的模板图片格式，维度数: {len(template_shape)}")

def _multi_match_with_alpha(frame, template, threshold, max_results):
    """
    处理带有透明度的多模板匹配
    """
    # 分离BGRA通道
    bgr = template[:, :, :3].astype(np.uint8)
    alpha = template[:, :, 3].astype(np.uint8)
    
    # 创建掩码
    mask = (alpha > 25).astype(np.uint8)

    # 确保frame也是uint8类型
    if frame.dtype != np.uint8:
        frame = frame.astype(np.uint8)

    # 如果frame是4通道（BGRA），转换为3通道（BGR）
    if len(frame.shape) == 3 and frame.shape[2] == 4:
        frame = frame[:, :, :3]

    # 使用TM_CCOEFF_NORMED进行匹配
    result = cv2.matchTemplate(frame, bgr, cv2.TM_CCOEFF_NORMED, mask=mask)
    
    return _find_multiple_matches(result, threshold, max_results, template.shape)

def _multi_match_without_alpha(frame, template, threshold, max_results):
    """
    处理不带透明度的多模板匹配
    """
    # 确保数据类型正确
    if frame.dtype != np.uint8:
        frame = frame.astype(np.uint8)
    if template.dtype != np.uint8:
        template = template.astype(np.uint8)
    
    # 如果frame是4通道（BGRA），转换为3通道（BGR）
    if len(frame.shape) == 3 and frame.shape[2] == 4:
        frame = frame[:, :, :3]
    
    # 如果template是4通道（BGRA），转换为3通道（BGR）
    if len(template.shape) == 3 and template.shape[2] == 4:
        template = template[:, :, :3]
    
    # 使用TM_CCOEFF_NORMED进行匹配
    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    
    return _find_multiple_matches(result, threshold, max_results, template.shape)

def _find_multiple_matches(result, threshold, max_results, template_shape):
    """
    从匹配结果中找到多个匹配位置
    """
    matches = []
    h, w = template_shape[:2]
    
    # 找到所有超过阈值的匹配位置
    locations = np.where(result >= threshold)
    
    for pt in zip(*locations[::-1]):  # 转换坐标格式
        if len(matches) >= max_results:
            break
            
        # 检查是否与已有匹配重叠
        is_duplicate = False
        for existing_match in matches:
            existing_pt = existing_match[0]
            # 如果两个匹配位置距离太近，认为是重复的
            if abs(pt[0] - existing_pt[0]) < w//2 and abs(pt[1] - existing_pt[1]) < h//2:
                is_duplicate = True
                break
        
        if not is_duplicate:
            top_left = pt
            bottom_right = (pt[0] + w, pt[1] + h)
            matches.append((top_left, bottom_right))
    
    return matches

def convert_to_relative(point, frame):
    """
    Converts POINT into relative coordinates in the range [0, 1] based on FRAME.
    Normalizes the units of the vertical axis to equal those of the horizontal
    axis by using config.mm_ratio.
    :param point:   The point in absolute coordinates.
    :param frame:   The image to use as a reference.
    :return:        The given point in relative coordinates.
    """

    x = point[0] / frame.shape[1]
    y = point[1] / config.capture.minimap_ratio / frame.shape[0]
    return x, y


def convert_to_absolute(point, frame):
    """
    Converts POINT into absolute coordinates (in pixels) based on FRAME.
    Normalizes the units of the vertical axis to equal those of the horizontal
    axis by using config.mm_ratio.
    :param point:   The point in relative coordinates.
    :param frame:   The image to use as a reference.
    :return:        The given point in absolute coordinates.
    """

    x = int(round(point[0] * frame.shape[1]))
    y = int(round(point[1] * config.capture.minimap_ratio * frame.shape[0]))
    return x, y


def filter_color(img, ranges):
    """
    Returns a filtered copy of IMG that only contains pixels within the given RANGES.
    on the HSV scale.
    :param img:     The image to filter.
    :param ranges:  A list of tuples, each of which is a pair upper and lower HSV bounds.
    :return:        A filtered copy of IMG.
    """

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, ranges[0][0], ranges[0][1])
    for i in range(1, len(ranges)):
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, ranges[i][0], ranges[i][1]))

    # Mask the image
    color_mask = mask > 0
    result = np.zeros_like(img, np.uint8)
    result[color_mask] = img[color_mask]
    return result


def draw_location(minimap, pos, color):
    """
    Draws a visual representation of POINT onto MINIMAP. The radius of the circle represents
    the allowed error when moving towards POINT.
    :param minimap:     The image on which to draw.
    :param pos:         The location (as a tuple) to depict.
    :param color:       The color of the circle.
    :return:            None
    """

    center = convert_to_absolute(pos, minimap)
    cv2.circle(minimap,
               center,
               round(minimap.shape[1] * settings.move_tolerance),
               color,
               1)


def print_separator():
    """Prints a 3 blank lines for visual clarity."""

    print('\n\n')


def print_state():
    """Prints whether Auto Maple is currently enabled or disabled."""

    print_separator()
    print('#' * 18)
    print(f"#    {'ENABLED ' if config.enabled else 'DISABLED'}    #")
    print('#' * 18)


def closest_point(points, target):
    """
    Returns the point in POINTS that is closest to TARGET.
    :param points:      A list of points to check.
    :param target:      The point to check against.
    :return:            The point closest to TARGET, otherwise None if POINTS is empty.
    """

    if points:
        points.sort(key=lambda p: distance(p, target))
        return points[0]


def bernoulli(p):
    """
    Returns the value of a Bernoulli random variable with probability P.
    :param p:   The random variable's probability of being True.
    :return:    True or False.
    """

    return random() < p


def rand_float(start, end):
    """Returns a random float value in the interval [START, END)."""

    assert start < end, 'START must be less than END'
    return (end - start) * random() + start


##########################
#       Threading        #
##########################
class Async(threading.Thread):
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.queue = queue.Queue()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.function(*self.args, **self.kwargs)
        self.queue.put('x')

    def process_queue(self, root):
        def f():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                root.after(100, self.process_queue(root))

        return f


def async_callback(context, function, *args, **kwargs):
    """Returns a callback function that can be run asynchronously by the GUI."""

    def f():
        task = Async(function, *args, **kwargs)
        task.start()
        context.after(100, task.process_queue(context))

    return f
