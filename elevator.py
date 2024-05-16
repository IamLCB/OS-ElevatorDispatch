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
floors = [i for i in range(1, max_floor+1)] # 楼层序号 1-20
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
        Thread.__init__(self)
        self.req_in = [] # 电梯内部请求
        self.req_out = {ElevatorState.UP: [], ElevatorState.DOWN: []} # 电梯外部请求
        QtCore.QObject.__init__(self)
        
    def run(self):
        while True:
            if self.status_door: # 开门了
                self.label.setText("Opening door")
                time.sleep(self.door_speed)
                self.label.setText("Closing door")
                time.sleep(self.door_speed)
                self.status_door = False
                self.elev_btn[self.cur_floor].setEnabled(True) # 电梯内部按钮恢复
                
                # 恢复外部楼层按钮
                if self.status_request != ElevatorState.STOP:
                    requests[self.status_request][self.cur_floor] = False
                    floor_btn[self.status_request][self.cur_floor].setEnabled(True)
                
                # 门改变后更改状态, 电梯门关闭后电梯状态改为STOP
                if len(self.req_out[ElevatorState.UP]) == 0 and len(self.req_out[ElevatorState.DOWN]) == 0: 
                    # 电梯外部请求为空
                    self.status_request = ElevatorState.STOP
                    if len(self.req_in) == 0:
                        self.status_move = ElevatorState.STOP
                        self.label.setText("STOP")
            else: # 电梯不需要开门
                if self.cur_floor in self.req_in: # 电梯到达内部请求楼层
                    self.req_in.remove(self.cur_floor) # 删除内部请求
                    self.status_door = True # 开门
                elif self.status_move == ElevatorState.UP: # 电梯向上运行1层
                    self.label.setText("Moving up")
                    time.sleep(self.move_speed)
                    self.cur_floor += 1
                elif self.status_move == ElevatorState.DOWN: # 电梯向下运行1层
                    self.label.setText("Moving down")
                    time.sleep(self.move_speed)
                    self.cur_floor -= 1
                    
                # 电梯到达楼层后, 处理外部请求
                if self.status_move != ElevatorState.STOP and self.cur_floor in self.req_out[self.status_move]:
                    self.req_out[self.status_move].remove(self.cur_floor) # 删除外部请求
                    self.status_door = True # 开门
                elif self.status_move == ElevatorState.DOWN and self.status_request == ElevatorState.UP and \
                    self.cur_floor == self.req_out[ElevatorState.UP][0]: # 当前运行方向向下，但向上有请求，并且到达最低的一层
                    
                    self.req_out[self.status_request].remove(self.cur_floor) # 删除外部请求，改变方向
                    self.status_door = True # 开门
                    self.status_move = self.status_request
                elif self.status_move == ElevatorState.UP and self.status_request == ElevatorState.DOWN and \
                    self.cur_floor == self.req_out[ElevatorState.DOWN][-1]: # 当前运行方向向上，但向下有请求，并且到达最高的一层
                    
                    self.req_out[self.status_request].remove(self.cur_floor) # 删除外部请求，改变方向
                    self.status_door = True
                    self.status_move = self.status_request
                    
                self.lcd.display(self.cur_floor) # 更新显示屏
                
                if len(self.req_out[ElevatorState.UP]) == 0 and len(self.req_out[ElevatorState.DOWN]) == 0: 
                    # 电梯外部请求为空
                    if len(self.req_in) == 0:
                        # 电梯内部请求为空
                        time.sleep(2) # 电梯停留2s
            
            self.check_request() # 检查电梯运行后的状态
            
    def open_door(self): # 开门
        if self.status_move == ElevatorState.STOP:
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

    def status_toMove(self, goal):
        if self.status_move == ElevatorState.STOP:
            if goal > self.cur_floor:
                self.status_move = ElevatorState.UP
            elif goal < self.cur_floor:
                self.status_move = ElevatorState.DOWN
                
    def set_in(self, goal): # 内部请求
        if (self.status_move == ElevatorState.STOP or
            self.status_move == ElevatorState.UP and goal >= self.cur_floor and goal not in self.req_in or
            self.status_move == ElevatorState.DOWN and goal <= self.cur_floor and goal not in self.req_in):
        # 电梯停止或者电梯向上运行且目标楼层在电梯当前楼层之上且目标楼层不在电梯内部请求中  
            self.elev_btn[goal].setEnabled(False) # 电梯内部按钮失效

            if goal != self.cur_floor:
                bisect.insort(self.req_in, goal) # 插入电梯内部请求
                self.status_toMove(goal)
            else: # 电梯在目标楼层
                self.status_door = True
            return True
        else:
            return False
        
    def set_out(self, goal, req_dir): # 外部请求
        if (self.status_move == ElevatorState.STOP or
            self.status_move == ElevatorState.UP and goal >= self.cur_floor and goal not in self.req_out[req_dir] or
            self.status_move == ElevatorState.DOWN and goal <= self.cur_floor and goal not in self.req_out[req_dir]):
            # 电梯停止或者电梯向上运行且目标楼层在电梯当前楼层之上且目标楼层不在电梯外部请求中
            
            if goal != self.cur_floor: # 电梯不在目标楼层
                if self.status_request == ElevatorState.STOP or self.status_request == req_dir:
                    bisect.insort(self.req_out[req_dir], goal)
                    self.status_request = req_dir
                    print(self.req_out)
                    print(self.status_request)
                else:
                    return False
                
                self.status_toMove(goal)
            else: # 电梯在目标楼层
                self.status_door = True
            return True
        else:
            return False
        
elevs = [Elevator() for i in range(elevator_num)] # 5部电梯 0-4

def out_request(floor, req_dir): # 外部按下请求按钮
    if not requests[floor][req_dir]:
        requests[floor][req_dir] = True
        floor_btn[floor][req_dir].setEnabled(False)
    print()
    for elev in elevs:
        if elev.set_out(req_dir, floor):
            return
    requests[floor][req_dir] = False # 电梯都在运行，请求失败
    floor_btn[floor][req_dir].setEnabled(True)
    
def start():
    for i in range(elevator_num):
        elevs[i].start()
        
def join():
    for i in range(elevator_num):
        elevs[i].join()
        
class GUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        # 最常用的还是栅格布局了。这种布局是把窗口分为行和列。创建和使用栅格布局，需要使用QGridLayout模块。"""
        screens = QGridLayout()  # 楼层显示
        inButtons = QGridLayout()  # 内部按钮
        openButtons = QGridLayout()  # 开门按钮
        outButtons = QGridLayout()  # 外部按钮
        grid = QGridLayout()  # 显示和按钮在一个表格布局中

        # 间距设置
        screens.setHorizontalSpacing(20)  # 设置楼层显示之间的间距
        inButtons.setHorizontalSpacing(30)  # 设置电梯内按钮列之间的间距
        outButtons.setHorizontalSpacing(20)  # 设置电梯外按钮列之间的间距
        grid.setHorizontalSpacing(100)  # 设置内外按钮列之间的间距

        # 整体是一个栅格布局，分别加入进去
        grid.addLayout(inButtons, 1, 0)  # 内部按钮加入整体布局
        grid.addLayout(openButtons, 2, 0)  # 开门按钮加入整体布局
        grid.addLayout(outButtons, 1, 1)  # 外部按钮加入整体布局
        grid.addLayout(screens, 0, 0)  # 显示楼层加入整体布局
        self.setLayout(grid)

        up_button = {}
        down_button = {}
        
        for floor in floors:
            # 外部按钮：20层楼-20行，上下-2列---------------------------
            text = QLabel(str(floor))  # 按钮的楼层
            text.setFont(QFont("Calibri"))  # 字体
            text.setAlignment(QtCore.Qt.AlignRight)
            outButtons.addWidget(text, max_floor - floor + 1, 0)

            button = QPushButton('▲')
            button.setFont(QFont("Calibri"))  # 字体
            outButtons.addWidget(button, max_floor - floor + 1, 1)
            button.clicked.connect(partial(out_request, ElevatorState.UP, floor))
            up_button[floor] = button

            button = QPushButton('▼')
            button.setFont(QFont("Calibri"))  # 字体
            outButtons.addWidget(button, max_floor - floor + 1, 2)
            button.clicked.connect(partial(out_request, ElevatorState.DOWN, floor))
            down_button[floor] = button
        floor_btn[ElevatorState.UP] = up_button  # out_button{'up'}{floor}
        floor_btn[ElevatorState.DOWN] = down_button  # out_button{'down'}{floor}
        
        # 内部按钮：5部电梯-5行，20层楼-20列---------------------------
        for elev in range(elevator_num):
            in_button = {}
            for floor in floors:
                button = QPushButton(str(floor))
                button.setFont(QFont("Calibri")) # 字体
                inButtons.addWidget(button, max_floor - floor + 1, elev)  # 加到栅格布局里
                button.clicked.connect(partial(elevs[elev].set_in, floor))  # 按下的楼层添加到目标列表里
                in_button[floor] = button
            elevs[elev].elev_btn = in_button

            open_but = QPushButton('OPEN')
            open_but.setFont(QFont("Calibri"))
            open_but.clicked.connect(elevs[elev].open_door)
            openButtons.addWidget(open_but, 0, elev)
            elevs[elev].open_but = open_but
        
        # 当前楼层显示-------------------------------------------
        for i in range(elevator_num):
            Show = QVBoxLayout()  # 使用 QVBoxLayout 代替 QGridLayout
            HBox = QHBoxLayout()  # 使用 QHBoxLayout 创建水平布局
            
            # 数字显示
            lcd = QLCDNumber()
            lcd.display(elevs[i].cur_floor)
            lcd.setDigitCount(2)
            size = 50  # 设置正方形的边长
            lcd.setFixedSize(size, size)  # 设置固定的宽度和高度
            lcd.setStyleSheet("border: 2px solid black; background: silver; ")  # 设计样式
            elevs[i].lcd = lcd
            
            # 创建一个固定宽度的空白小部件
            spacer = QWidget()
            spacer.setFixedWidth(10)
            # 添加LCD和空白小部件到HBox布局
            HBox.addWidget(lcd)
            HBox.addWidget(spacer)
            Show.addLayout(HBox)
            
            # 上下行和暂停显示
            stateShow = QLabel("STOP")
            stateShow.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
            elevs[i].label = stateShow
            Show.addWidget(stateShow)
            # 作为整体加入到screens
            screens.addLayout(Show, 0, i)


        self.setWindowTitle('Elevator Dispatch System')
        self.show()

if __name__ == "__main__":  # 可以管理共享数据
    app = QApplication(sys.argv)

    w = GUI()
    start()
    sys.exit(app.exec_())
