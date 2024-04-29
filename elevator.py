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
floors = [i in range(1, max_floor+1)] # ¥����� 1-20
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
        Thread.__init__
        self.req_in = [] # �����ڲ�����
        self.req_out = {ElevatorState.UP: [], ElevatorState.DOWN: []} # �����ⲿ����
        QtCore.QObject.__init__(self)
        
    def run(self):
        while True:
            if self.status_door: # ������
                self.label.setText("Door is opening")
                time.sleep(self.door_speed)
                self.label.setText("Door is closing")
                time.sleep(self.door_speed)
                self.status_door = False
                self.elev_btn[self.cur_floor].setEnabled(True) # �����ڲ���ť�ָ�
                
                # �ָ��ⲿ¥�㰴ť
                if self.status_request != ElevatorState.STOP:
                    requests[self.status_request][self.cur_floor] = False
                    floor_btn[self.cur_floor][self.status_request].setEnabled(True)
                
                # �Ÿı�����״̬, �����Źرպ����״̬��ΪSTOP
                if len(self.req_out[ElevatorState.UP]) == 0 and len(self.req_out[ElevatorState.DOWN]) == 0: 
                    # �����ⲿ����Ϊ��
                    self.status_request = ElevatorState.STOP
                    if len(self.req_in) == 0:
                        self.status_move = ElevatorState.STOP
                        self.label.setText("Elevator is stopped")
            else: # ���ݲ���Ҫ����
                if self.cur_floor in self.req_in: # ���ݵ����ڲ�����¥��
                    self.req_in.remove(self.cur_floor) # ɾ���ڲ�����
                    self.status_door = True # ����
                elif self.status_move == ElevatorState.UP: # ������������1��
                    self.label.setText("Elevator is moving up")
                    time.sleep(self.move_speed)
                    self.cur_floor += 1
                elif self.status_move == ElevatorState.DOWN: # ������������1��
                    self.label.setText("Elevator is moving down")
                    time.sleep(self.move_speed)
                    self.cur_floor -= 1
                    
                # ���ݵ���¥���, �����ⲿ����
                if self.status_move != ElevatorState.STOP and self.cur_floor in self.req_out[self.status_move]:
                    self.req_out[self.status_move].remove(self.cur_floor) # ɾ���ⲿ����
                    self.status_door = True # ����
                elif self.status_move == ElevatorState.DOWN and self.status_request == ElevatorState.UP and \
                    self.floor == self.req_out[ElevatorState.UP][0]: # ��ǰ���з������£������������󣬲��ҵ�����͵�һ��
                    
                    self.req_out[self.status_request].remove(self.cur_floor) # ɾ���ⲿ���󣬸ı䷽��
                    self.status_door = True # ����
                    self.status_move = self.status_request
                elif self.status_move == ElevatorState.UP and self.status_request == ElevatorState.DOWN and \
                    self.floor == self.req_out[ElevatorState.DOWN][-1]: # ��ǰ���з������ϣ������������󣬲��ҵ�����ߵ�һ��
                    
                    self.req_out[self.status_request].remove(self.cur_floor) # ɾ���ⲿ���󣬸ı䷽��
                    self.status_door = True
                    self.status_move = self.status_request
                    
                self.lcd.display(self.cur_floor) # ������ʾ��
                
                if len(self.req_out[ElevatorState.UP]) == 0 and len(self.req_out[ElevatorState.DOWN]) == 0: 
                    # �����ⲿ����Ϊ��
                    if len(self.in_goal) == 0:
                        # �����ڲ�����Ϊ��
                        time.sleep(2) # ����ͣ��2s
            
            self.check_request() # ���������к��״̬
            
    def open_door(self): # ����
        if self.status_move == ElevatorState.STOP
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
