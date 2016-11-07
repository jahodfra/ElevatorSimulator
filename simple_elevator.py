import elevator


def elevator_step(state, **kwrags):
    floors = len(state.floors_up)
    while True:
        while state.floor < floors - 1:
            if state.floors_up[state.floor]:
                yield (elevator.WAIT, elevator.GO_UP)
            state = yield (elevator.GO_UP, elevator.GO_UP)
        while state.floor > 0:
            if state.floors_down[state.floor]:
                yield (elevator.WAIT, elevator.GO_DOWN)
            state = yield (elevator.GO_DOWN, elevator.GO_DOWN)
