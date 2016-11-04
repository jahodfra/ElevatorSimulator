#!/usr/bin/python

from __future__ import print_function
import ConfigParser
import argparse
import re
import unittest


# TODO: generate persons
# TODO: add first elevator program
# TODO: extract drawing from the simulation
# TODO: allow some actions to take longer time (e.g. exchaning passangers)



class Simulation:
    def __init__(self, floors_count):
        self.floors = [Floor(x) for x in range(floors_count)]
        self.elevators = []
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

    def _update_elevator(self, elevator):
        if elevator.state == Elevator.WAITING:
            # remove persons
            outgoing = [p
                for p in elevator.persons
                if p.destination == elevator.floor_number
            ]
            for person in outgoing:
                elevator.persons.remove(person)
                self.transported_persons += 1
            # onboard persons
            floor_number = elevator.floor_number
            floor = self.floors[floor_number]
            if elevator.sign == Elevator.GOING_UP:
                persons = [p
                    for p in floor.persons
                    if p.destination > floor_number
                ]
            elif elevator.sign == Elevator.GOING_DOWN:
                persons = [p
                    for p in floor.persons
                    if p.destination < floor_number
                ]
            while elevator.free_capacity > 0 and persons:
                person = persons.pop()
                floor.persons.remove(person)
                elevator.add_person(person)
        elif (elevator.state == Elevator.GOING_UP
              and elevator.floor_number + 1 < len(self.floors)):
            elevator.floor_number += 1
        elif (elevator.state == Elevator.GOING_UP
              and elevator.floor_number > 0):
            elevator.floor_number -= 1

    def step(self):
        '''
        Run simulation step.
        
        Move the elevators.
        Allow elevators to decide on the next action.
        Generate new pasangers.
        '''
        for elevator in self.elevators:
            self._update_elevator(elevator)

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
                    part = '{0:<{1}s}'.format(elevator.draw(), elevator.display_width)
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
    GOING_UP = '^'
    GOING_DOWN = 'v'
    WAITING = 'w'

    def __init__(self, floor_number, capacity=4):
        self.floor_number = floor_number
        self.persons = []
        self.state = self.WAITING
        self.capacity = capacity
        self.sign = self.GOING_UP
   
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
        return self.state + self.sign + content


class Person:
    def __init__(self, destination, simulation_step=0):
        self.destination = destination
        self.born_at = simulation_step

    display_width = 2

    def draw(self):
        return str(self.destination)


class TestSimulation(unittest.TestCase):
    def test_draw(self):
        sim = Simulation(3)
        e1 = Elevator(0, 3)
        e1.sign = Elevator.GOING_UP
        e1.add_person(Person(3))
        e1.add_person(Person(2))
        e2 = Elevator(2, 5)
        e2.sign = Elevator.GOING_DOWN
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


def run_level(level):
    parser = ConfigParser.SafeConfigParser()
    parser.read('levels.ini')
    section = 'level_{:02d}'.format(level)
    steps = parser.getint(section, 'steps')
    seed = parser.getint(section, 'seed')
    max_waiting = parser.getint(section, 'max_waiting')
    floors = parser.getint(section, 'floors')
    elevators = parser.get(section, 'elevators')
    elevators = map(int, elevators.split(','))
    person_per_step = parser.getfloat(section, 'person_per_step')
    destinations = {}
    for option in parser.options(section):
        match = re.match('^floor_([0-9]{2})_dest$', option)
        if match:
            destinations[int(match.group(1))] = parser.getfloat(section, option)

    sim = Simulation(floors)
    for capacity in elevators:
        sim.add_elevator(Elevator(0, capacity))
    for step in xrange(steps):
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


def main():
    parser = argparse.ArgumentParser('run elevator simulator')
    parser.add_argument(
        '--level', default=0, type=int, help='level to run')
    #parser.add_argument(
    #    '--log', default=sys.stdout, type=argparse.FileType('w'),
    #    help='the file where the sum should be written')
    args = parser.parse_args()
    if args.level > 0:
        run_level(args.level)
    else:
        unittest.main()
        return


if __name__ == '__main__':
    main()
