#!/usr/bin/python3

import bisect
import configparser
import argparse
import importlib
import itertools
import statistics
import sys
import time
import random
import re
import unittest


# TODO: design couple of levels
# TODO: measure different algorithms
# TODO: write README.md
# TODO: write blogpost


GO_UP = 'up'
GO_DOWN = 'down'
WAIT = 'wait'
ON_BOARD_UP = 'on board passangers up'
ON_BOARD_DOWN = 'on board passangers down'
ON_BOARD_ALL = 'on board all passangers'

ACTION_TIME = {
    GO_UP: 1,
    GO_DOWN: 1,
    WAIT: 1,
    ON_BOARD_UP: 2,
    ON_BOARD_DOWN: 2,
    ON_BOARD_ALL: 2,
}


__all__ = ('GO_UP GO_DOWN WAIT ON_BOARD_UP ON_BOARD_DOWN ON_BOARD_ALL'
' ElevatorProgram').split(' ')

class Simulation:
    def __init__(self, floors_count, program, person_generator, max_waiting):
        self.floors = [Floor(x) for x in range(floors_count)]
        self.elevators = []
        self.program = program
        self.transport_times = []
        self.step_counter = 0
        self.max_waiting = max_waiting
        self.person_generator = person_generator

    def add_elevator(self, elevator):
        self.elevators.append(elevator)

    def add_person(self, person, floor_number):
        self.floors[floor_number].add_person(person)

    def all_persons(self):
        for floor in self.floors:
            for person in floor.persons:
                yield person
        for elevator in self.elevators:
            for person in elevator.persons:
                yield person

    @property
    def oldest_birth_date(self):
        try:
            return min(p.born_at for p in self.all_persons())
        except ValueError:
            return -1

    def _remove_persons_from_elevator(self, elevator):
        outgoing = [
            p
            for p in elevator.persons
            if p.destination == elevator.floor_number
        ]
        for person in outgoing:
            elevator.persons.remove(person)
            self.transport_times.append(self.step_counter - person.born_at)

    def _on_board_persons(self, elevator_id, condition, callbacks):
        elevator = self.elevators[elevator_id]
        floor_number = elevator.floor_number
        floor = self.floors[floor_number]
        persons = [p for p in floor.persons if condition(p)]
        while elevator.free_capacity > 0 and persons:
            person = persons.pop()
            floor.persons.remove(person)
            elevator.add_person(person)
            self.program.press_button(elevator_id, person.destination)
        if persons:
            # If there are remaining persons on the floor, let
            # the elevator know that
            for callback in callbacks:
                callback(floor_number)

    def _update_elevator(self, elevator_id):
        elevator = self.elevators[elevator_id]
        elevator.wait_time -= 1
        if elevator.wait_time > 0:
            return
        state = elevator.state
        if state == WAIT:
            pass
        elif state == ON_BOARD_UP:
            self._remove_persons_from_elevator(elevator)
            floor = elevator.floor_number
            self._on_board_persons(
                elevator_id,
                lambda p: p.destination > floor,
                [self.program.call_elevator_up]
            )
        elif state == ON_BOARD_DOWN:
            self._remove_persons_from_elevator(elevator)
            floor = elevator.floor_number
            self._on_board_persons(
                elevator_id,
                lambda p: p.destination < floor,
                [self.program.call_elevator_down]
            )
        elif state == ON_BOARD_ALL:
            self._remove_persons_from_elevator(elevator)
            floor = elevator.floor_number
            self._on_board_persons(
                elevator_id,
                lambda p: p.destination != floor,
                [self.program.call_elevator_up, self.program.call_elevator_down]
            )
        elif (elevator.state == GO_UP and
              elevator.floor_number + 1 < len(self.floors)):
            elevator.floor_number += 1
            elevator.move_counter += 1
        elif (elevator.state == GO_DOWN and
              elevator.floor_number > 0):
            elevator.floor_number -= 1
            elevator.move_counter += 1

    def _generate_person(self):
        src_floor, dest_floor = self.person_generator()
        if src_floor is not None:
            self.add_person(Person(dest_floor, self.step_counter), src_floor)
            if dest_floor > src_floor:
                self.program.call_elevator_up(src_floor)
            else:
                self.program.call_elevator_down(src_floor)

    def step(self):
        """Run simulation step.

        Move the elevators.
        Allow elevators to decide on the next action.
        Generate new pasangers.
        """
        self._generate_person()
        for elevator_id, _ in enumerate(self.elevators):
            self._update_elevator(elevator_id)
        actions = self.program.step(
            [elevator.floor_number for elevator in self.elevators]
        )
        for elevator, action in zip(self.elevators, actions):
            if elevator.wait_time <= 0:
                elevator.state = action
                elevator.wait_time = ACTION_TIME[action]
        self.step_counter += 1

    def failed(self):
        birth_date = self.oldest_birth_date
        return (
            birth_date > -1 and
            self.step_counter - birth_date > self.max_waiting
        )

    @property
    def move_counter(self):
        if self.elevators:
            return sum(elevator.move_counter for elevator in self.elevators)
        return 0


class PersonGenerator:
    def __init__(self, seed, prob_src, prob_dest, person_per_step):
        self.random_sequence = random.Random()
        self.random_sequence.seed(seed)
        self.prob_src = prob_src
        self.prob_dest = prob_dest
        self.person_per_step = person_per_step

    def generate(self):
        if self.random_sequence.random() >= self.person_per_step:
            return None, None
        src_floor = random_choice(
            self.prob_src.items(), self.random_sequence.random()
        )
        dest_floor = random_choice(
            ((k, v) for k, v in self.prob_dest.items() if k != src_floor),
            self.random_sequence.random()
        )
        return src_floor, dest_floor


class SimulationFormatter:

    ELEVATOR_STATE_MAP = {
        GO_UP: '^',
        GO_DOWN: 'v',
        ON_BOARD_UP: 'A',
        ON_BOARD_DOWN: 'V',
        ON_BOARD_ALL: 'X',
        WAIT: '.',
    }

    def __init__(self, floors=100, persons_on_floor=True):
        digits = 1
        while floors > 10:
            digits += 1
            floors /= 10
        self.digits = digits
        self.persons_on_floor = persons_on_floor

    def _draw_floor(self, floor):
        people_up = sum(p.destination > floor.number for p in floor.persons)
        people_down = sum(p.destination < floor.number for p in floor.persons)
        output = '{0:{1}d}'.format(floor.number, self.digits)
        if self.persons_on_floor:
            if people_up > 0:
                output += ' {0}^'.format(people_up)
            if people_down > 0:
                output += ' {0}v'.format(people_down)
        else:
            if people_up and people_down:
                output += 'x'
            elif people_up:
                output += '^'
            elif people_down:
                output += 'v'
            else:
                output += ' '
        return output

    def _floor_width(self):
        if self.persons_on_floor:
            return self.digits + 1 + 3 + 1 + 3 + 1
        else:
            return self.digits + 3

    def _draw_person(self, person):
        return str(person.destination % 10**self.digits)

    def _elevator_width(self, elevator):
        digits = 1 if self.digits == 1 else self.digits + 1
        return 1 + digits * elevator.capacity

    def _draw_elevator(self, elevator):
        separator = '' if self.digits == 1 else ','
        content = separator.join(
            self._draw_person(p)
            for p in sorted(elevator.persons, key=lambda p: p.destination)
        )
        state = self.ELEVATOR_STATE_MAP[elevator.state]
        return state + content

    def draw(self, sim):
        """Draws actual state of simulation

        Returns string with the content

        e.g. for each floor
        06 8^
        05 8^ 6v w1,4,10,55              v2,4,5
        04 1v                    ^8
        ...

        Means that on 5th floor there are 8th people wanting to go up
        and 6 people wanting to go down.
        Elevator 1 waits in the floor and has 5 people going to
        floors 1, 4, 5, 10, 55.
        Elevator 2 is in a different floor.
        Elevator 3 goes down with people wanting to 2, 4, 5 floors.
        """
        lines = []
        for floor in reversed(sim.floors):
            part = '{0:<{1}s}'.format(
                self._draw_floor(floor), self._floor_width())
            parts = [part]
            for elevator in sim.elevators:
                width = self._elevator_width(elevator)
                if elevator.floor_number == floor.number:
                    part = '{0:<{1}s}'.format(
                        self._draw_elevator(elevator), width)
                    parts.append(part)
                else:
                    parts.append(' ' * width)
            lines.append(' '.join(parts))
        return '\n'.join(line.rstrip() for line in lines)


class Floor:
    def __init__(self, number):
        self.number = number
        self.persons = []

    def add_person(self, person):
        self.persons.append(person)


class Elevator:
    def __init__(self, floor_number, capacity=4):
        self.floor_number = floor_number
        self.persons = []
        self.state = WAIT
        self.capacity = capacity
        self.wait_time = 0
        self.move_counter = 0

    def add_person(self, person):
        if len(self.persons) == self.capacity:
            raise Exception('Cannot add person elevator is full')
        self.persons.append(person)

    @property
    def free_capacity(self):
        return self.capacity - len(self.persons)


class Person:
    def __init__(self, destination, simulation_step=0):
        self.destination = destination
        self.born_at = simulation_step


def normalize_probability(prob, floors):
    set_prob = sum(prob.values())
    if set_prob > 1.0:
        prob = {k: p / set_prob for k, p in prob.items()}
        set_prob = 1.0
    remaining_prob = 1.0 - set_prob
    remaining_values = floors - len(prob)
    if remaining_values > 0:
        p_per_value = remaining_prob / remaining_values
        for floor in range(floors):
            if floor not in prob:
                prob[floor] = p_per_value


def random_choice(density, random_number):
    choices, weights = zip(*density)
    cumdist = list(itertools.accumulate(weights))
    value = random_number * cumdist[-1]
    return choices[bisect.bisect(cumdist, value)]


class ElevatorProgram:
    def __init__(self, floors, elevators):
        self.floors = floors
        self.elevators = elevators
        self.action_generators = {}

    def call_elevator_up(self, floor):
        pass

    def call_elevator_down(self, floor):
        pass

    def press_button(self, elevator_id, destination):
        pass

    def step(self, floors):
        """Computes the next action for an elevator.

        Dummy elevator program

        Args:
            floors: position of all elevators. If the elevator is waiting the
            action for it is ignored.
        Returns:
            list with actions for all elevators
        """
        return [WAIT] * len(floors)


def print_state(sim, formatter, n_floors):
    if sim.step_counter != 0 and sys.stdout.isatty():
        print('\33[{}F\33[J'.format(n_floors+1), end='')
    birth_date = sim.oldest_birth_date
    print('step:{} oldest:{} transported:{}'.format(
        sim.step_counter,
        sim.step_counter - birth_date if birth_date > -1 else 'None',
        len(sim.transport_times)
    ))
    print(formatter.draw(sim))
    if sys.stdout.isatty():
        time.sleep(0.3)
    else:
        print()


def load_level(level, program_cls):
    parser = configparser.SafeConfigParser()
    parser.read('levels.ini')
    section = 'level_{:02d}'.format(level)
    steps = parser.getint(section, 'steps')
    seed = parser.getint(section, 'seed')
    max_waiting = parser.getint(section, 'max_waiting')
    floors = parser.getint(section, 'floors')
    elevators = parser.get(section, 'elevators')
    elevators = [int(capacity) for capacity in elevators.split(',')]

    person_per_step = parser.getfloat(section, 'person_per_step')
    prob_dest = {}
    prob_src = {}
    for option in parser.options(section):
        match = re.match('^floor_([0-9]{2})_(dest|src)$', option)
        if match:
            floor = int(match.group(1))
            probability = parser.getfloat(section, option)
            if match.group(2) == 'dest':
                prob_dest[floor] = probability
            else:
                prob_src[floor] = probability
    normalize_probability(prob_dest, floors)
    normalize_probability(prob_src, floors)

    program = program_cls(floors, len(elevators))
    generator = (
        PersonGenerator(seed, prob_src, prob_dest, person_per_step).generate
    )
    sim = Simulation(floors, program, generator, max_waiting)
    for capacity in elevators:
        sim.add_elevator(Elevator(0, capacity))
    return sim, steps


def run_level(level, program_cls, debug):
    sim, steps = load_level(level, program_cls)
    formatter = SimulationFormatter(
        floors=len(sim.floors), persons_on_floor=False)
    for _ in range(steps):
        birth_date = sim.oldest_birth_date
        if sim.failed():
            print('Failure: Person waited more than {} steps.'.format(
                sim.max_waiting
            ))
            break
        sim.step()
        if debug:
            print_state(sim, formatter, len(sim.floors))

    print('persons:', len(sim.transport_times))
    if not sim.transport_times:
        sim.transport_times.append(0)
    print('min time:', min(sim.transport_times))
    print('max time:', max(sim.transport_times))
    print('avg time:', statistics.mean(sim.transport_times))
    print('median time:', statistics.median(sim.transport_times))
    print('moves:', sim.move_counter)


class TestSimulation(unittest.TestCase):
    def test_draw(self):
        generator = lambda: None, None
        sim = Simulation(3, ElevatorProgram, generator, 1)
        e1 = Elevator(0, 3)
        e1.sign = GO_UP
        e1.add_person(Person(3))
        e1.add_person(Person(2))
        e2 = Elevator(2, 5)
        e2.sign = GO_DOWN
        e2.add_person(Person(1))
        sim.add_elevator(e1)
        sim.add_elevator(e2)
        sim.add_person(Person(0), 1)
        sim.add_person(Person(2), 1)
        sim.add_person(Person(1), 2)
        generated = SimulationFormatter().draw(sim)
        for gline, eline in zip(generated.split('\n'), [
                ' 2 1v                  .1',
                ' 1 1^ 1v',
                ' 0          .2,3',
        ]):
            self.assertEqual(gline.rstrip('\n'), eline)


def main():
    parser = argparse.ArgumentParser('run elevator simulator')
    parser.add_argument(
        '--level', default=0, type=int, help='level to run')
    parser.add_argument(
        '--program', help='name of the module with a program')
    parser.add_argument(
        '--debug', help='show detailed output', default=False,
        action='store_true')
    args = parser.parse_args()
    if args.program:
        program = importlib.import_module(args.program).Program
    else:
        program = ElevatorProgram
    if args.level > 0:
        run_level(args.level, program, args.debug)
    else:
        unittest.main()
        return


if __name__ == '__main__':
    main()
