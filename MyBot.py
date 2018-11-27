#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
from hlt.entity import Ship
from hlt.positionals import Direction, Position
import random
import logging

BOT_VERSION = "amezhenin-v11"
DIRECTIONS = [Direction.North, Direction.South, Direction.East, Direction.West]
SHIP_BUILD_MAX_TURN = 200
MAX_OWN_SHIPS = 20
MIN_DROPOFF_DIST = 10


class Bot:
    def __init__(self):
        self.game = hlt.Game()
        self.me = None
        self.game_map = None
        self.command_queue = []
        self.my_ships = []


    def start(self):
        """ <<<Game Begin>>> """
        # At this point "game" variable is populated with initial map data.
        # This is a good place to do computationally expensive start-up pre-processing.
        # As soon as you call "ready" function below, the 2 second per turn timer will start.
        self.game.ready(BOT_VERSION)

        logging.info("Successfully created bot! My Player ID is {}.".format(self.game.my_id))
        logging.info("Max turns %s" % constants.MAX_TURNS)

        """ <<<Game Loop>>> """
        while True:
            self.update_frame()

            # self.attack_enemy_shipyard()
            self.construct_dropoff()

            for ship in self.my_ships:
                if ship.halite_amount >= constants.MAX_HALITE * 0.9:
                    # navigate to home
                    move = self.drop_halite(ship)
                    self.command_queue.append(ship.move(move))
                elif self.is_end_game(ship):
                    move = self.drop_halite(ship, force=True)
                    self.command_queue.append(ship.move(move))
                else:
                    move = self.collect(ship)
                    self.command_queue.append(ship.move(move))

            self.build_ship()
            # Send your moves back to the game environment, ending this turn.
            self.game.end_turn(self.command_queue)


    def update_frame(self):
        self.game.update_frame()
        # You extract player metadata and the updated map metadata here for convenience.
        self.me = self.game.me
        self.game_map = self.game.game_map
        self.command_queue = []
        self.my_ships = self.me.get_ships()


    def build_ship(self):
        # If the game is in the first X turns and you have enough halite, spawn a ship.
        # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
        if self.game.turn_number <= SHIP_BUILD_MAX_TURN and len(self.my_ships) <= MAX_OWN_SHIPS \
                and self.me.halite_amount >= constants.SHIP_COST \
                and not self.game_map[self.me.shipyard].is_occupied:
            self.command_queue.append(self.me.shipyard.spawn())


    def attack_enemy_shipyard(self):
        """
        DISABLED: attack shipyard only if it is a duel
        """

        enemies = self.game.players.values()
        enemies = list(filter(lambda x: x.id != self.me.id, enemies))
        # we don't attack if we have 4 players or no ships
        if len(enemies) != 1 or len(self.my_ships) == 0:
            return
        enemy = enemies[0]

        # find a closest ship and use to attack the enemy
        closest_ship = self.my_ships[0]
        min_distance = 9999
        for ship in self.my_ships:
            dist = self.game_map.calculate_distance(ship.position, enemy.shipyard.position)
            # logging.info("Ship %s distance %s" % (ship, dist))
            if dist < min_distance:
                # logging.info("Selecting ship %s" % ship)
                closest_ship = ship
                min_distance = dist

        # if turn is in (300;340] AND there is NO ships in the enemy shipyard, then don't attack
        # it means that enemy is killing this ships
        if 300 < self.game.turn_number <= 340 or min_distance == 0:
            move = self.game_map.naive_navigate(closest_ship, enemy.shipyard.position)
            self.command_queue.append(closest_ship.move(move))
            self.my_ships = list(filter(lambda x: x.id != closest_ship.id, self.my_ships))
            # logging.info("Final list %s" % self.my_ships)


    def construct_dropoff(self):

        if self.game.turn_number < 50 \
                or len(self.me.get_dropoffs()) > 0 \
                or self.me.halite_amount < constants.DROPOFF_COST:
            return self.my_ships

        # scan all position and find a closest to shipyard closest with max halite
        closest_cand = None
        closest_dist = 9999
        max_halite = 0
        for w in range(0, self.game_map.width):
            for h in range(0, self.game_map.height):
                p = Position(w, h)
                dist = self.game_map.calculate_distance(p, self.me.shipyard.position)
                if dist < MIN_DROPOFF_DIST:
                    continue
                halite = self.game_map[p].halite_amount
                if halite > max_halite or (halite == max_halite and dist < closest_dist):
                    logging.info("New candidate dist %s with pos %s with halite %s" % (dist, p, halite))
                    closest_cand = p
                    closest_dist = dist
                    max_halite = halite

        if not closest_cand:
            return

        # pick closest ship to that position
        closest_ship = self.my_ships[0]
        closest_dist = 9999
        for ship in self.my_ships:
            dist = self.game_map.calculate_distance(ship.position, closest_cand)
            if dist < closest_dist:
                logging.info("New ship dist %s with pos %s" % (dist, ship.position))
                closest_ship = ship
                closest_dist = dist

        # move there
        if closest_dist != 0:
            move = self.game_map.naive_navigate(closest_ship, closest_cand)
            self.command_queue.append(closest_ship.move(move))
            self.my_ships = list(filter(lambda x: x.id != closest_ship.id, self.my_ships))
            return

        # if we are there, try to build a dropoff
        logging.info("Ship %s is making dropoff" % closest_ship)
        self.command_queue.append(closest_ship.make_dropoff())
        self.my_ships = list(filter(lambda x: x.id != closest_ship.id, self.my_ships))


    def collect(self, ship):
        max_halite = self.game_map[ship.position].halite_amount * 2
        pos_choices = [{
            'position': ship.position,
            'direction': Direction.Still,
            'halite': max_halite
        }]
        for direction, position in zip(DIRECTIONS, ship.position.get_surrounding_cardinals()):
            # logging.info("Ship %s pos %s state %s" % (ship, position, game_map[position].is_occupied))
            if self.game_map[position].is_occupied:
                continue
            pos_choices.append({
                'position': position,
                'direction': direction,
                'halite': self.game_map[position].halite_amount
            })
            if max_halite < self.game_map[position].halite_amount:
                max_halite = self.game_map[position].halite_amount
                # logging.info("New max halite: %s" % max_halite)

        # pos_choices = [ship.position] + pos_choices
        # halite_choices = list(map(lambda x: game_map[x].halite_amount, pos_choices))
        # halite_choices[0] *= 2  # we prefer to stand still
        # logging.info(pos_choices)

        best_moves = list(filter(lambda x: x['halite'] == max_halite, pos_choices))
        if len(best_moves) > 1:
            logging.info("Multiple best moves: %s" % best_moves)
            best_move = random.choice(best_moves)
            logging.info("Random best move: %s" % best_move)
        else:
            best_move = best_moves[0]

        # mark next move of this ship as occupied
        self.game_map[best_move['position']].ship = Ship(self.me, random.randint(1000, 10000), ship.position, 0)
        # game_map[best_move['position']].ship = ship

        # if max_halite['direction'] != Direction.Still:
        #     # mark this position as empty, because we will move away from it next move
        #     game_map[ship.position].ship = None
        # return best move
        # logging.info("Ship %s move %s" % (ship, best_move['position']))

        return best_move['direction']


    def drop_halite(self, ship, force=False):

        dropoffs = self.me.get_dropoffs()
        if len(dropoffs):
            drop_pos = dropoffs[0].position
        else:
            drop_pos = self.me.shipyard.position

        if force is False:
            if self.game_map[drop_pos].ship and self.game_map[drop_pos].ship.owner != self.me:
                # attack enemy in my dropoff
                self.game_map[drop_pos].ship = None
            move = self.game_map.naive_navigate(ship, drop_pos)
        else:
            # set dropoff/shipyard as empty
            self.game_map[drop_pos].ship = None
            move = self.game_map.naive_navigate(ship, drop_pos)

        # make it unsafe to
        # logging.info("Current %s move %s next pos %s" % (ship.position, move, ship.position + Position(*move)))
        # FIXME: rewrite navigation and remove this dummy creation
        self.game_map[ship.position + Position(*move)].ship = Ship(self.me, random.randint(1000, 10000),
                                                              ship.position + Position(*move), 0)
        # game_map[ship.position].ship = None
        return move


    def is_end_game(self, ship):
        home_dist = self.game_map.calculate_distance(ship.position, self.me.shipyard.position)
        res = home_dist + 10 > (constants.MAX_TURNS - self.game.turn_number)
        return res


if __name__ == "__main__":
    bot = Bot()
    bot.start()
