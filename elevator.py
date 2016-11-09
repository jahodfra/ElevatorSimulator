#!/usr/bin/python3

import configparser
import argparse
import importlib
import random
import re
import unittest


# TODO: merge sign and state and add NOOP action
# TODO: extract drawing from the simulation
# TODO: allow some actions to take longer time (e.g. exchaning passangers)
# TODO: design couple of levels
# TODO: measure different algorithms
# TODO: write blogpost

GO_UP = 'up'
GO_DOWN = 'down'
WAIT = 'wait'


class Simulation:
    def __init__(self, floors_count, program):
        self.floors = [Floor(x) for x in range(floors_count)]
        self.elevators = []
        self.program = program
        self.transported_persons = 0

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

    def _update_elevator(self, elevator_id):
        elevator = self.elevators[elevator_id]
        if elevator.state == WAIT:
            # remove persons
            outgoing = [
                p
                for p in elevator.persons
                if p.destination == elevator.floor_number
            ]
            for person in outgoing:
                elevator.persons.remove(person)
                self.transported_persons += 1
            # onboard persons
            floor_number = elevator.floor_number
            floor = self.floors[floor_number]
            if elevator.sign == GO_UP:
                persons = [
                    p
                    for p in floor.persons
                    if p.destination > floor_number
                ]
            elif elevator.sign == GO_DOWN:
                persons = [
                    p
                    for p in floor.persons
                    if p.destination < floor_number
                ]
            while elevator.free_capacity > 0 and persons:
                person = persons.pop()
                floor.persons.remove(person)
                elevator.add_person(person)
                self.program.press_button(elevator_id, person.destination)
            if persons:
                # If there are remaining persons on the floor, let
                # the elevator know that
                if elevator.sign == GO_UP:
                    self.program.call_elevator_up(floor_number)
                else:
                    self.program.call_elevator_down(floor_number)
        elif (elevator.state == GO_UP and
              elevator.floor_number + 1 < len(self.floors)):
            elevator.floor_number += 1
        elif (elevator.state == GO_DOWN and
              elevator.floor_number > 0):
            elevator.floor_number -= 1

    def step(self):
        '''
        Run simulation step.

        Move the elevators.
        Allow elevators to decide on the next action.
        Generate new pasangers.
        '''
        for elevator_id, _ in enumerate(self.elevators):
            self._update_elevator(elevator_id)
        for elevator_id, elevator in enumerate(self.elevators):
            new_state, new_sign = self.program.step(
                elevator_id, elevator.floor_number)
            elevator.state = new_state
            elevator.sign = new_sign

    def draw(self):
        '''
        Draws actual state of simulation

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
        '''
        lines = []
        for floor in reversed(self.floors):
            part = '{0:<{1}s}'.format(floor.draw(), floor.display_width)
            parts = [part]
            for elevator in self.elevators:
                if elevator.floor_number == floor.number:
                    part = '{0:<{1}s}'.format(
                        elevator.draw(), elevator.display_width)
                    parts.append(part)
                else:
                    parts.append(' ' * elevator.display_width)
            lines.append(' '.join(parts))
        return '\n'.join(line.rstrip() for line in lines)


class Floor:
    def __init__(self, number):
        self.number = number
        self.persons = []

    display_width = 2 + 1 + 3 + 1 + 3 + 1

    def draw(self):
        people_up = sum(p.destination > self.number for p in self.persons)
        people_down = sum(p.destination < self.number for p in self.persons)
        output = '{0:2d}'.format(self.number)
        if people_up > 0:
            output += ' {0}^'.format(people_up)
        if people_down > 0:
            output += ' {0}v'.format(people_down)
        return output

    def add_person(self, person):
        self.persons.append(person)


class Elevator:
    def __init__(self, floor_number, capacity=4):
        self.floor_number = floor_number
        self.persons = []
        self.state = WAIT
        self.capacity = capacity
        self.sign = GO_UP

    def add_person(self, person):
        if len(self.persons) == self.capacity:
            raise Exception('Cannot add person elevator is full')
        self.persons.append(person)

    @property
    def display_width(self):
        return 2 + (Person.display_width+1) * self.capacity

    @property
    def free_capacity(self):
        return self.capacity - len(self.persons)

    def draw(self):
        content = ','.join(
            p.draw() for p in sorted(self.persons, key=lambda p: p.destination)
        )
        state = {
            GO_UP: '^',
            GO_DOWN: 'v',
            WAIT: 'w',
        }[self.state]
        sign = {
            GO_UP: '^',
            GO_DOWN: 'v',
        }[self.sign]
        return state + sign + content


class Person:
    def __init__(self, destination, simulation_step=0):
        self.destination = destination
        self.born_at = simulation_step

    display_width = 2

    def draw(self):
        return str(self.destination)


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


def random_choice(density):
    density = list(density)
    value = random.random() * sum(v for k, v in density)
    for key, prob in density:
        if value <= prob:
            return key
        value -= prob


def generate_person(sim, prob_src, prob_dest, step):
    src_floor = random_choice(prob_src.items())
    dest_floor = random_choice(
        (k, v) for k, v in prob_dest.items() if k != src_floor
    )
    sim.add_person(Person(dest_floor, step), src_floor)
    if dest_floor > src_floor:
        sim.program.call_elevator_up(src_floor)
    else:
        sim.program.call_elevator_down(src_floor)


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

    def generate_actions(self, elevator_id, floor):
        """Computes the next action for an elevator.

        Dummy elevator program

        Args:
            elevator_id: int Unique number of the current elevator
            floor: starting elevator floor
        Yields: next action, next sign status
            New status
        Yield from: the current elevator floor
        """
        while True:
            _new_state = yield(WAIT, GO_UP)

    def step(self, elevator_id, floor):
        """Computes the next action for an elevator.

        Dummy elevator program

        Args:
            elevator_id: int Unique number of the current elevator
            floor: starting elevator floor
        Yields: next action, next sign status
            New status
        Yield from: the current elevator floor
        """
        generator = self.action_generators.get(elevator_id)
        if not generator:
            generator = self.generate_actions(elevator_id, floor)
            self.action_generators[elevator_id] = generator
            next(generator)
        try:
            return generator.send(floor)
        except StopIteration:
            return WAIT, GO_UP


def run_level(level, program_cls):
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

    random.seed(seed)
    program = program_cls(floors, len(elevators))
    sim = Simulation(floors, program)
    for capacity in elevators:
        sim.add_elevator(Elevator(0, capacity))
    for step in range(steps):
        if random.random() < person_per_step:
            generate_person(sim, prob_src, prob_dest, step)
        birth_date = sim.oldest_birth_date
        if birth_date > -1 and step - birth_date > max_waiting:
            print('Failure: Person waited more than {} steps.'.format(
                max_waiting
            ))
            return
        sim.step()
        print('step:{} oldest:{} transported:{}'.format(
            step,
            step - birth_date if birth_date > -1 else 'None',
            sim.transported_persons
        ))
        print(sim.draw())
        print()
    print(sim.transported_persons)


class TestSimulation(unittest.TestCase):
    def test_draw(self):
        sim = Simulation(3)
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
        generated = sim.draw()
        for gline, eline in zip(generated.split('\n'), [
                ' 2 1v                   wv1',
                ' 1 1^ 1v',
                ' 0          w^2,3',
        ]):
            self.assertEqual(gline.rstrip('\n'), eline)


def main():
    parser = argparse.ArgumentParser('run elevator simulator')
    parser.add_argument(
        '--level', default=0, type=int, help='level to run')
    parser.add_argument(
        '--program', help='name of the module with a program')
    args = parser.parse_args()
    if args.program:
        program = importlib.import_module(args.program).Program
    else:
        program = ElevatorProgram
    if args.level > 0:
        run_level(args.level, program)
    else:
        unittest.main()
        return


if __name__ == '__main__':
    main()
