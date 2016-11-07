from elevator import Elevator


def elevator_step(state, **kwrags):
    floors = len(state.floors_up)
    while True:
        while state.floor < floors - 1:
            if state.floors_up[state.floor]:
                yield (Elevator.WAITING, Elevator.GOING_UP)
            state = yield (Elevator.GOING_UP, Elevator.GOING_UP)
        while state.floor > 0:
            if state.floors_down[state.floor]:
                yield (Elevator.WAITING, Elevator.GOING_DOWN)
            state = yield (Elevator.GOING_DOWN, Elevator.GOING_DOWN)
