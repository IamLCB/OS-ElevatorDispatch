# coding=gbk

import sys
import time
from functools import partial
from threading import Thread
import threading
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
import bisect
from enum import Enum

class ElevatorState(Enum):
    UP = 1
    STOP = 0
    DOWN = -1
    
max_floor = 20
elevator_num = 5
floors = [i in range(1, max_floor+1)] # 楼层序号 1-20
requests = {ElevatorState.UP : {floor: False for floor in floors}, 
            ElevatorState.DOWN: {floor: False for floor in floors}} # 请求状态, True表示有请求, False表示无请求
floor_btn = {} # 每层楼的外部按钮

class Elevator(Thread, QtCore.QObject): # 电梯类
    status_move = ElevatorState.STOP
    status_request = ElevatorState.STOP
    status_door = False # 电梯门状态, True表示开(以及开关门), False表示关
    runLock = threading.Lock() # 电梯运行锁, 保证电梯运行时不会被其他线程打断
    cur_floor = 1 # 当前楼层
    door_speed = 2 # 开关门时间
    move_speed = 1 # 电梯运行时间
    elev_btn = {} # 电梯内部按钮
    lcd = None # 电梯显示屏
    label = None # 电梯标签
    
    def __init__(self):
        Thread.__init__
        self.req_in = [] # 电梯内部请求
        self.req_out = {ElevatorState.UP: [], ElevatorState.DOWN: []} # 电梯外部请求
        QtCore.QObject.__init__(self)
        
    def run(self):
        while True:
            if self.status_door: # 开门了
                self.label.setText("Door is opening")
                time.sleep(self.door_speed)
                self.label.setText("Door is closing")
                time.sleep(self.door_speed)
                self.status_door = False
                self.elev_btn[self.cur_floor].setEnabled(True) # 电梯内部按钮恢复
                
                # 恢复外部楼层按钮
                if self.status_request != ElevatorState.STOP:
                    requests[self.status_request][self.cur_floor] = False
                    floor_btn[self.cur_floor][self.status_request].setEnabled(True)
                
                # 门改变后更改状态, 电梯门关闭后电梯状态改为STOP
                if len(self.req_out[ElevatorState.UP]) == 0 and len(self.req_out[ElevatorState.DOWN]) == 0: 
                    # 电梯外部请求为空
                    self.status_request = ElevatorState.STOP
                    if len(self.req_in) == 0:
                        self.status_move = ElevatorState.STOP
                        self.label.setText("Elevator is stopped")
            else: # 电梯不需要开门
                if self.cur_floor in self.req_in: # 电梯到达内部请求楼层
                    self.req_in.remove(self.cur_floor) # 删除内部请求
                    self.status_door = True # 开门
                elif self.status_move == ElevatorState.UP: # 电梯向上运行1层
                    self.label.setText("Elevator is moving up")
                    time.sleep(self.move_speed)
                    self.cur_floor += 1
                elif self.status_move == ElevatorState.DOWN: # 电梯向下运行1层
                    self.label.setText("Elevator is moving down")
                    time.sleep(self.move_speed)
                    self.cur_floor -= 1
                    
                # 电梯到达楼层后, 处理外部请求
                if self.status_move != ElevatorState.STOP and self.cur_floor in self.req_out[self.status_move]:
                    self.req_out[self.status_move].remove(self.cur_floor) # 删除外部请求
                    self.status_door = True # 开门
                elif self.status_move == ElevatorState.DOWN and self.status_request == ElevatorState.UP and \
                    self.floor == self.req_out[ElevatorState.UP][0]: # 当前运行方向向下，但向上有请求，并且到达最低的一层
                    
                    self.req_out[self.status_request].remove(self.cur_floor) # 删除外部请求，改变方向
                    self.status_door = True # 开门
                    self.status_move = self.status_request
                elif self.status_move == ElevatorState.UP and self.status_request == ElevatorState.DOWN and \
                    self.floor == self.req_out[ElevatorState.DOWN][-1]: # 当前运行方向向上，但向下有请求，并且到达最高的一层
                    
                    self.req_out[self.status_request].remove(self.cur_floor) # 删除外部请求，改变方向
                    self.status_door = True
                    self.status_move = self.status_request
                    
                self.lcd.display(self.cur_floor) # 更新显示屏
                
                if len(self.req_out[ElevatorState.UP]) == 0 and len(self.req_out[ElevatorState.DOWN]) == 0: 
                    # 电梯外部请求为空
                    if len(self.in_goal) == 0:
                        # 电梯内部请求为空
                        time.sleep(2) # 电梯停留2s
            
            self.check_request() # 检查电梯运行后的状态
            
    def open_door(self): # 开门
        if self.status_move == ElevatorState.STOP
            self.status_door = True
            
    def check_request(self): # 检查电梯运行后的状态, 电梯到达最高或最低楼层时，电梯状态改为STOP
        if (self.cur_floor < min(floors) and self.status_move == ElevatorState.DOWN  or 
            self.cur_floor > max(floors) and self.status_move == ElevatorState.UP): 
            # 电梯到达最高或最低楼层
            self.status_move = ElevatorState.STOP
            for floor in floors:
                self.elev_btn[floor].setEnabled(True) # 电梯内部按钮恢复
            self.req_in.clear()
            self.cur_floor -= self.status_move.value # 电梯回退1层
