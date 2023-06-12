from pymodbus.client.sync import ModbusSerialClient as RtuMaster
import requests
import json
import base64
import pyaudio
import time
import hashlib
from aip import AipSpeech

# 设置百度API相关参数
APP_ID = '34384930'
API_KEY = 'Qbhf8CPGmSnGzUlqRaePqlYa'
SECRET_KEY = 'XfhzbesAcA62llyBhGRwLK7IbAkE08Ad'

# 实例化 AipSpeech 客户端
client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)

# 录音设置
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5

def recognize_speech():
    # 创建 pyaudio 模块的音频对象
    audio = pyaudio.PyAudio()

    # 打开音频流，准备进行音频数据录制
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)

    print("请开始说话......")

    # 存储所有录音片段的列表
    frames = []

    # 循环录音，将所有录音片段存储到 frames 中
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    # 停止音频流，关闭音频流
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # 将录音片段拼接起来，形成完整的音频数据
    speech_data = bytes().join(frames)

    # 构造 API 请求参数
    options = {
        'dev_pid': 1536 # 识别模型，这里使用中文普通话模型
    }

    # 发送语音识别请求
    result = client.asr(speech_data, 'pcm', RATE, options)

    if 'result' in result:
        text = result['result'][0]
        print("语音识别结果：", text)
        return text
    else:
        print("语音识别失败")
        return None

recognize_speech()


def connect_relay(port):
    master = None
    try:
        master = RtuMaster(method='rtu', port=port, baudrate=9600, timeout=5, bytesize=8, parity='E', stopbits=1)
        if not master.connect():
            raise ValueError("Failed to connect to modbus slave at {}".format(port))
        response_code = 1
        return response_code, master
    except Exception as exc:
        print(str(exc))
        response_code = -1
        if master:
            master.close()
            master = None
        return response_code, master

def switch_fan(master, action):
    if not master.is_socket_open():
        print("Error: Invalid master object")
        return -2

    if action.upper() not in ['ON', 'OFF']:
        raise ValueError("Invalid action: {}".format(action))

    try:
        if action.upper() == 'ON':
            # 控制继电器闭合，开启风扇
            rr = master.write_coil(0, True, unit=2)
        else:
            # 控制继电器断开，关闭风扇
            rr = master.write_coil(0, False, unit=2)
        response_code = 1
    except Exception as exc:
        print(str(exc))
        response_code = -1
    return response_code

def on_command_recognized():
    # 风扇状态，初始化为关闭
    fan_state = 0
    # 检查风扇当前状态
    coil_status = master.read_coils(0, 1, unit=2)
    fan_is_on = coil_status.bits[0]

    # 根据风扇状态设置 fan_state 的值
    if fan_is_on:
        fan_state = 1

    command = recognize_speech()
    print("识别结果：", command)

    if command is None:
        print("指令不明，请重新操作")
    elif '打开风扇' in command:
        if fan_state != 1:
            fan_state = 1
            switch_fan(master, 'ON')
            time.sleep(1)  # 等待继电器切换
            # 更新风扇状态
            fan_state = 1
            print('已打开风扇')
        else:
            print('风扇已经打开')
    elif '关闭风扇' in command:
        if fan_state != 0:
            # 关闭风扇
            switch_fan(master, 'OFF')
            time.sleep(1)
            # 更新风扇状态
            fan_state = 0
            print('已关闭风扇')
        else:
            print('风扇已经关闭')
    elif '停止运行' in command:
        global running
        running = False
        print('程序已停止')
    else:
        print('指令不明，请重新操作')

running = True
fan_state = 0
port = 'COM5'
res, master = connect_relay(port)

if res > 0:
    print("连接成功")
else:
    print("连接超时或失败")

while running:
    on_command_recognized()