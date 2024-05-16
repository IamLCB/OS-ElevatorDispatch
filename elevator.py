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
floors = [i for i in range(1, max_floor+1)] # ¥����� 1-20
requests = {ElevatorState.UP : {floor: False for floor in floors}, 
            ElevatorState.DOWN: {floor: False for floor in floors}} # ����״̬, True��ʾ������, False��ʾ������
floor_btn = {} # ÿ��¥���ⲿ��ť

class Elevator(Thread, QtCore.QObject): # ������
    status_move = ElevatorState.STOP
    status_request = ElevatorState.STOP
    status_door = False # ������״̬, True��ʾ��(�Լ�������), False��ʾ��
    runLock = threading.Lock() # ����������, ��֤��������ʱ���ᱻ�����̴߳��
    cur_floor = 1 # ��ǰ¥��
    door_speed = 2 # ������ʱ��
    move_speed = 1 # ��������ʱ��
    elev_btn = {} # �����ڲ���ť
    lcd = None # ������ʾ��
    label = None # ���ݱ�ǩ
    
    def __init__(self):
        Thread.__init__(self)
        self.req_in = [] # �����ڲ�����
        self.req_out = {ElevatorState.UP: [], ElevatorState.DOWN: []} # �����ⲿ����
        QtCore.QObject.__init__(self)
        
    def run(self):
        while True:
            if self.status_door: # ������
                self.label.setText("Opening door")
                time.sleep(self.door_speed)
                self.label.setText("Closing door")
                time.sleep(self.door_speed)
                self.status_door = False
                self.elev_btn[self.cur_floor].setEnabled(True) # �����ڲ���ť�ָ�
                
                # �ָ��ⲿ¥�㰴ť
                if self.status_request != ElevatorState.STOP:
                    requests[self.status_request][self.cur_floor] = False
                    floor_btn[self.status_request][self.cur_floor].setEnabled(True)
                
                # �Ÿı�����״̬, �����Źرպ����״̬��ΪSTOP
                if len(self.req_out[ElevatorState.UP]) == 0 and len(self.req_out[ElevatorState.DOWN]) == 0: 
                    # �����ⲿ����Ϊ��
                    self.status_request = ElevatorState.STOP
                    if len(self.req_in) == 0:
                        self.status_move = ElevatorState.STOP
                        self.label.setText("STOP")
            else: # ���ݲ���Ҫ����
                if self.cur_floor in self.req_in: # ���ݵ����ڲ�����¥��
                    self.req_in.remove(self.cur_floor) # ɾ���ڲ�����
                    self.status_door = True # ����
                elif self.status_move == ElevatorState.UP: # ������������1��
                    self.label.setText("Moving up")
                    time.sleep(self.move_speed)
                    self.cur_floor += 1
                elif self.status_move == ElevatorState.DOWN: # ������������1��
                    self.label.setText("Moving down")
                    time.sleep(self.move_speed)
                    self.cur_floor -= 1
                    
                # ���ݵ���¥���, �����ⲿ����
                if self.status_move != ElevatorState.STOP and self.cur_floor in self.req_out[self.status_move]:
                    self.req_out[self.status_move].remove(self.cur_floor) # ɾ���ⲿ����
                    self.status_door = True # ����
                elif self.status_move == ElevatorState.DOWN and self.status_request == ElevatorState.UP and \
                    self.cur_floor == self.req_out[ElevatorState.UP][0]: # ��ǰ���з������£������������󣬲��ҵ�����͵�һ��
                    
                    self.req_out[self.status_request].remove(self.cur_floor) # ɾ���ⲿ���󣬸ı䷽��
                    self.status_door = True # ����
                    self.status_move = self.status_request
                elif self.status_move == ElevatorState.UP and self.status_request == ElevatorState.DOWN and \
                    self.cur_floor == self.req_out[ElevatorState.DOWN][-1]: # ��ǰ���з������ϣ������������󣬲��ҵ�����ߵ�һ��
                    
                    self.req_out[self.status_request].remove(self.cur_floor) # ɾ���ⲿ���󣬸ı䷽��
                    self.status_door = True
                    self.status_move = self.status_request
                    
                self.lcd.display(self.cur_floor) # ������ʾ��
                
                if len(self.req_out[ElevatorState.UP]) == 0 and len(self.req_out[ElevatorState.DOWN]) == 0: 
                    # �����ⲿ����Ϊ��
                    if len(self.req_in) == 0:
                        # �����ڲ�����Ϊ��
                        time.sleep(2) # ����ͣ��2s
            
            self.check_request() # ���������к��״̬
            
    def open_door(self): # ����
        if self.status_move == ElevatorState.STOP:
            self.status_door = True
            
    def check_request(self): # ���������к��״̬, ���ݵ�����߻����¥��ʱ������״̬��ΪSTOP
        if (self.cur_floor < min(floors) and self.status_move == ElevatorState.DOWN  or 
            self.cur_floor > max(floors) and self.status_move == ElevatorState.UP): 
            # ���ݵ�����߻����¥��
            self.status_move = ElevatorState.STOP
            for floor in floors:
                self.elev_btn[floor].setEnabled(True) # �����ڲ���ť�ָ�
            self.req_in.clear()
            self.cur_floor -= self.status_move.value # ���ݻ���1��

    def status_toMove(self, goal):
        if self.status_move == ElevatorState.STOP:
            if goal > self.cur_floor:
                self.status_move = ElevatorState.UP
            elif goal < self.cur_floor:
                self.status_move = ElevatorState.DOWN
                
    def set_in(self, goal): # �ڲ�����
        if (self.status_move == ElevatorState.STOP or
            self.status_move == ElevatorState.UP and goal >= self.cur_floor and goal not in self.req_in or
            self.status_move == ElevatorState.DOWN and goal <= self.cur_floor and goal not in self.req_in):
        # ����ֹͣ���ߵ�������������Ŀ��¥���ڵ��ݵ�ǰ¥��֮����Ŀ��¥�㲻�ڵ����ڲ�������  
            self.elev_btn[goal].setEnabled(False) # �����ڲ���ťʧЧ

            if goal != self.cur_floor:
                bisect.insort(self.req_in, goal) # ��������ڲ�����
                self.status_toMove(goal)
            else: # ������Ŀ��¥��
                self.status_door = True
            return True
        else:
            return False
        
    def set_out(self, goal, req_dir): # �ⲿ����
        if (self.status_move == ElevatorState.STOP or
            self.status_move == ElevatorState.UP and goal >= self.cur_floor and goal not in self.req_out[req_dir] or
            self.status_move == ElevatorState.DOWN and goal <= self.cur_floor and goal not in self.req_out[req_dir]):
            # ����ֹͣ���ߵ�������������Ŀ��¥���ڵ��ݵ�ǰ¥��֮����Ŀ��¥�㲻�ڵ����ⲿ������
            
            if goal != self.cur_floor: # ���ݲ���Ŀ��¥��
                if self.status_request == ElevatorState.STOP or self.status_request == req_dir:
                    bisect.insort(self.req_out[req_dir], goal)
                    self.status_request = req_dir
                    print(self.req_out)
                    print(self.status_request)
                else:
                    return False
                
                self.status_toMove(goal)
            else: # ������Ŀ��¥��
                self.status_door = True
            return True
        else:
            return False
        
elevs = [Elevator() for i in range(elevator_num)] # 5������ 0-4

def out_request(floor, req_dir): # �ⲿ��������ť
    if not requests[floor][req_dir]:
        requests[floor][req_dir] = True
        floor_btn[floor][req_dir].setEnabled(False)
    print()
    for elev in elevs:
        if elev.set_out(req_dir, floor):
            return
    requests[floor][req_dir] = False # ���ݶ������У�����ʧ��
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
        # ��õĻ���դ�񲼾��ˡ����ֲ����ǰѴ��ڷ�Ϊ�к��С�������ʹ��դ�񲼾֣���Ҫʹ��QGridLayoutģ�顣"""
        screens = QGridLayout()  # ¥����ʾ
        inButtons = QGridLayout()  # �ڲ���ť
        openButtons = QGridLayout()  # ���Ű�ť
        outButtons = QGridLayout()  # �ⲿ��ť
        grid = QGridLayout()  # ��ʾ�Ͱ�ť��һ����񲼾���

        # �������
        screens.setHorizontalSpacing(20)  # ����¥����ʾ֮��ļ��
        inButtons.setHorizontalSpacing(30)  # ���õ����ڰ�ť��֮��ļ��
        outButtons.setHorizontalSpacing(20)  # ���õ����ⰴť��֮��ļ��
        grid.setHorizontalSpacing(100)  # �������ⰴť��֮��ļ��

        # ������һ��դ�񲼾֣��ֱ�����ȥ
        grid.addLayout(inButtons, 1, 0)  # �ڲ���ť�������岼��
        grid.addLayout(openButtons, 2, 0)  # ���Ű�ť�������岼��
        grid.addLayout(outButtons, 1, 1)  # �ⲿ��ť�������岼��
        grid.addLayout(screens, 0, 0)  # ��ʾ¥��������岼��
        self.setLayout(grid)

        up_button = {}
        down_button = {}
        
        for floor in floors:
            # �ⲿ��ť��20��¥-20�У�����-2��---------------------------
            text = QLabel(str(floor))  # ��ť��¥��
            text.setFont(QFont("Calibri"))  # ����
            text.setAlignment(QtCore.Qt.AlignRight)
            outButtons.addWidget(text, max_floor - floor + 1, 0)

            button = QPushButton('��')
            button.setFont(QFont("Calibri"))  # ����
            outButtons.addWidget(button, max_floor - floor + 1, 1)
            button.clicked.connect(partial(out_request, ElevatorState.UP, floor))
            up_button[floor] = button

            button = QPushButton('��')
            button.setFont(QFont("Calibri"))  # ����
            outButtons.addWidget(button, max_floor - floor + 1, 2)
            button.clicked.connect(partial(out_request, ElevatorState.DOWN, floor))
            down_button[floor] = button
        floor_btn[ElevatorState.UP] = up_button  # out_button{'up'}{floor}
        floor_btn[ElevatorState.DOWN] = down_button  # out_button{'down'}{floor}
        
        # �ڲ���ť��5������-5�У�20��¥-20��---------------------------
        for elev in range(elevator_num):
            in_button = {}
            for floor in floors:
                button = QPushButton(str(floor))
                button.setFont(QFont("Calibri")) # ����
                inButtons.addWidget(button, max_floor - floor + 1, elev)  # �ӵ�դ�񲼾���
                button.clicked.connect(partial(elevs[elev].set_in, floor))  # ���µ�¥����ӵ�Ŀ���б���
                in_button[floor] = button
            elevs[elev].elev_btn = in_button

            open_but = QPushButton('OPEN')
            open_but.setFont(QFont("Calibri"))
            open_but.clicked.connect(elevs[elev].open_door)
            openButtons.addWidget(open_but, 0, elev)
            elevs[elev].open_but = open_but
        
        # ��ǰ¥����ʾ-------------------------------------------
        for i in range(elevator_num):
            Show = QVBoxLayout()  # ʹ�� QVBoxLayout ���� QGridLayout
            HBox = QHBoxLayout()  # ʹ�� QHBoxLayout ����ˮƽ����
            
            # ������ʾ
            lcd = QLCDNumber()
            lcd.display(elevs[i].cur_floor)
            lcd.setDigitCount(2)
            size = 50  # ���������εı߳�
            lcd.setFixedSize(size, size)  # ���ù̶��Ŀ�Ⱥ͸߶�
            lcd.setStyleSheet("border: 2px solid black; background: silver; ")  # �����ʽ
            elevs[i].lcd = lcd
            
            # ����һ���̶���ȵĿհ�С����
            spacer = QWidget()
            spacer.setFixedWidth(10)
            # ���LCD�Ϳհ�С������HBox����
            HBox.addWidget(lcd)
            HBox.addWidget(spacer)
            Show.addLayout(HBox)
            
            # �����к���ͣ��ʾ
            stateShow = QLabel("STOP")
            stateShow.setAlignment(QtCore.Qt.AlignCenter)  # ���ж���
            elevs[i].label = stateShow
            Show.addWidget(stateShow)
            # ��Ϊ������뵽screens
            screens.addLayout(Show, 0, i)


        self.setWindowTitle('Elevator Dispatch System')
        self.show()

if __name__ == "__main__":  # ���Թ���������
    app = QApplication(sys.argv)

    w = GUI()
    start()
    sys.exit(app.exec_())
