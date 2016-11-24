import itertools
import operator
import random

from elevator import *

UP = True
DOWN = False


class Elevator:
    def __init__(self):
        self.floor = 0
        self.direction = UP
        self.exits = set()
        self.enter_up = set()
        self.enter_down = set()
        self.action = WAIT
        self.wait_floor = 0

    def score(self, floor, direction, n_floors):
        # take the most optimistic estimation (but still admissible)
        if (floor == self.floor and direction == self.direction and
            self.action in (ON_BOARD_UP, ON_BOARD_DOWN)
        ):
            # This check prevents elevator to stop again if there is not enough
            # people in it.
            return 100000
        # TODO: take into account number of stops
        # TODO: elevator does not have to go to the last floor
        if direction:
            if self.floor < floor:
                return floor - self.floor
            else:
                return 2 * n_floors - self.floor - floor - 1
        else:
            if self.floor < floor:
                return self.floor + floor - 1
            else:
                return self.floor - floor

    def add_target(self, floor):
        self.exits.add(floor)

    def is_serving(self, floor, direction):
        if direction:
            return floor in self.enter_up
        else:
            return floor in self.enter_down

    def is_unused(self):
        return not (self.exits or self.enter_up or self.enter_down)

    def dispatch(self, floor, direction):
        if direction:
            self.enter_up.add(floor)
        else:
            self.enter_down.add(floor)

    def move(self):
        self.action = GO_UP if self.direction else GO_DOWN

    def onboard(self):
        self.action = ON_BOARD_UP if self.direction else ON_BOARD_DOWN

    def wait(self):
        self.action = WAIT

    def step(self):
        if self.is_unused():
            # We should move to the waiting floor.
            if self.floor < self.wait_floor:
                self.direction = UP
                self.move()
            elif self.floor > self.wait_floor:
                self.direction = DOWN
                self.move()
            else:
                self.wait()
            return

        # Should I continue in the same direction?
        # We want to change the direction the least amount of time.
        # If there is a call in the same direction we have to move there.
        # Note that we can change direction for the exit on the current floor.
        cmp_func = operator.lt if self.direction else operator.gt
        if not any(
            cmp_func(self.floor, x)
            for x in itertools.chain(self.exits, self.enter_up, self.enter_down)
        ):
            # Change the direction
            # If there is not a call for the current floor and direction,
            if self.direction:
                if self.floor not in self.enter_up:
                    self.direction = not self.direction
            else:
                if self.floor not in self.enter_down:
                    self.direction = not self.direction

        # should I exchange persons on this floor?
        enters = self.enter_up if self.direction else self.enter_down
        if self.floor in self.exits or self.floor in enters:
            self.exits.discard(self.floor)
            enters.discard(self.floor)
            self.onboard()
            return

        self.move()


class Program(ElevatorProgram):
    def __init__(self, floors, elevators):
        super().__init__(floors, elevators)
        self._elevators = [Elevator() for _ in range(elevators)]
        self._actions = []
        # TODO: elevator default positions are set to 0. Finding optimal
        # default positions is the different optimalization.
        # That should not influence score over load much.

    def _select_elevator(self, floor, direction):
        return min(
            self._elevators,
            key=lambda elevator: elevator.score(floor, direction, self.floors)
        )

    def _dispatch_elevator(self, floor, direction):
        # should program dispatch all actions immediately or is better
        # to queue actions?
        # it is better to wait because some floor can be served by other
        # elevators
        # should elevators have own queues?
        # how to reschedule what elevators were already asked to do?
        # TODO: assign actions temporarily (next round the action can be
        # assigned to somebody else)
        if any(
            elevator.is_serving(floor, direction)
            for elevator in self._elevators
        ):
                # Do nothing.
                return
        # TODO: consider global level state optimalizations 
        elevator = self._select_elevator(floor, direction)
        elevator.dispatch(floor, direction)

    def call_elevator_up(self, floor):
        self._actions.append((floor, UP))

    def call_elevator_down(self, floor):
        self._actions.append((floor, DOWN))

    def press_button(self, elevator_id, destination):
        self._elevators[elevator_id].add_target(destination)

    def step(self, floors):
        for floor, direction in self._actions:
            self._dispatch_elevator(floor, direction)
        self._actions = []
        actions = []
        for elevator_id, floor in enumerate(floors):
            elevator = self._elevators[elevator_id]
            elevator.floor = floor
            elevator.step()
            actions.append(elevator.action)
        return actions
