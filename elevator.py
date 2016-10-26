#!/usr/bin/python

import unittest

# TODO: add information sign to the elevator
# TODO: generate persons


class Simulation:
    def __init__(self, floors_count):
        self.floors = [Floor(x) for x in range(floors_count)]
        self.elevators = []

    def add_elevator(self, elevator):
        self.elevators.append(elevator)

    def add_person(self, person, floor_number):
        self.floors[floor_number].add_person(person)

    def _update_elevator(self, elevator):
        if elevator.state == Elevator.WAITING:
            # remove persons
            outgoing = [
                p for p elevator.persons
                if p.destination == elevator.floor_number]
            for person in outgoing:
                elevator.persons.remove(person)
            # onboard persons
            floor = self.floors[elevator.floor_number]
            while elevator.free_capacity > 0 and floor.persons:
                elevator.add_person(floor.persons.pop())
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
        elevator.step()
                 

    def draw(self):
        '''
        Draws actual state of simulation

        Returns string with the content
        
        e.g. for each floor
        06 8^   
        05 8^ 6v w1,4,10,55              v2,4,5
        04 1v                    ^8

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
   
    def add_person(self, person):
        if len(self.persons) == self.capacity:
            raise Exception('Cannot add person elevator is full')
        self.persons.append(person)

    @property
    def display_width(self):
        return 1 + (Person.display_width+1) * self.capacity

    @property
    def free_capacity(self):
        return self.capacity - len(self.persons)

    def draw(self):
        content = ','.join(
            p.draw() for p in sorted(self.persons, key=lambda p: p.destination)
        )
        return self.state + content


class Person:
    def __init__(self, destination):
        self.destination = destination

    display_width = 2

    def draw(self):
        return str(self.destination)


class TestSimulation(unittest.TestCase):
    def test_draw(self):
        sim = Simulation(3)
        e1 = Elevator(0, 3)
        e1.add_person(Person(3))
        e1.add_person(Person(2))
        e2 = Elevator(2, 5)
        e2.add_person(Person(1))
        sim.add_elevator(e1)
        sim.add_elevator(e2)
        sim.add_person(Person(0), 1)
        sim.add_person(Person(2), 1)
        sim.add_person(Person(1), 2)
        generated = sim.draw()
        for gline, eline in zip(generated.split('\n'), [
                ' 2 1v                  w1',
                ' 1 1^ 1v',
                ' 0          w2,3',
        ]):
            self.assertEqual(gline.rstrip('\n'), eline)


if __name__ == '__main__':
    unittest.main()
