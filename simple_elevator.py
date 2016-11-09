import elevator


def init(floors, elevators):
    global floors_up
    global floors_down
    global n_floors
    floors_up = [False] * floors
    floors_down = [False] * floors
    n_floors = floors


def call_elevator_up(floor):
    floors_up[floor] = True


def call_elevator_down(floor):
    floors_down[floor] = True


def elevator_step(state, **kwargs):
    while True:
        while state.floor < n_floors - 1:
            if floors_up[state.floor]:
                yield (elevator.WAIT, elevator.GO_UP)
                floors_up[state.floor] = False
            state = yield (elevator.GO_UP, elevator.GO_UP)
        while state.floor > 0:
            if floors_down[state.floor]:
                yield (elevator.WAIT, elevator.GO_DOWN)
                floors_down[state.floor] = False
            state = yield (elevator.GO_DOWN, elevator.GO_DOWN)
