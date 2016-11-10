from elevator import *


class Program(ElevatorProgram):
    def __init__(self, floors, elevators):
        super().__init__(floors, elevators)
        self.floors_up = [False] * floors
        self.floors_down = [False] * floors

    def call_elevator_up(self, floor):
        self.floors_up[floor] = True

    def call_elevator_down(self, floor):
        self.floors_down[floor] = True

    def generate_actions(self, elevator_id, floor):
        while True:
            while floor < self.floors - 1:
                if self.floors_up[floor]:
                    yield ON_BOARD_UP
                    self.floors_up[floor] = False
                floor = yield GO_UP
            while floor > 0:
                if self.floors_down[floor]:
                    yield ON_BOARD_DOWN
                    self.floors_down[floor] = False
                floor = yield GO_DOWN
