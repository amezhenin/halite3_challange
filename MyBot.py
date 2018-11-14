#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction

import random
# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging


def attack_enemy(game, command_queue, all_ships):
    me = game.me
    game_map = game.game_map

    # attack shipyard only if it is a duel
    enemies = game.players.values()
    enemies = list(filter(lambda x: x.id != me.id, enemies))
    # we don't attack if we have 4 players or no ships
    if len(enemies) != 1 or len(all_ships) == 0:
        return all_ships
    enemy = enemies[0]

    # find a closest ship and use to attack the enemy
    closest_ship = all_ships[0]
    min_distance = 9999
    for ship in all_ships:
        dist = game_map.calculate_distance(ship.position, enemy.shipyard.position)
        # logging.info("Ship %s distance %s" % (ship, dist))
        if dist < min_distance:
            # logging.info("Selecting ship %s" % ship)
            closest_ship = ship
            min_distance = dist

    # if turn is > 50 AND there is NO ships in the enemy shipyard, then don't attack
    # it means that enemy is killing this ships
    if game.turn_number > 50 and min_distance != 0:
        return all_ships

    move = game_map.naive_navigate(closest_ship, enemy.shipyard.position)
    command_queue.append(closest_ship.move(move))
    all_ships = list(filter(lambda x: x.id != closest_ship.id, all_ships))
    # logging.info("Final list %s" % all_ships)
    return all_ships


""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("amezhenin-v6")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

DIRECTIONS = [Direction.North, Direction.South, Direction.East, Direction.West]


def collect(ship):
    max_halite = game_map[ship.position].halite_amount * 2
    pos_choices = [{
        'position': ship.position,
        'direction': Direction.Still,
        'halite': max_halite
    }]
    for direction, position in zip(DIRECTIONS, ship.position.get_surrounding_cardinals()):
        # logging.info("Ship %s pos %s state %s" % (ship, position, game_map[position].is_occupied))
        if game_map[position].is_occupied:
            continue
        pos_choices.append({
            'position': position,
            'direction': direction,
            'halite': game_map[position].halite_amount
        })
        if max_halite < game_map[position].halite_amount:
            max_halite = game_map[position].halite_amount
            # logging.info("New max halite: %s" % max_halite)

    # pos_choices = [ship.position] + pos_choices
    # halite_choices = list(map(lambda x: game_map[x].halite_amount, pos_choices))
    # halite_choices[0] *= 2  # we prefer to stand still
    logging.info(pos_choices)

    best_moves = list(filter(lambda x: x['halite'] == max_halite, pos_choices))
    if len(best_moves) > 1:
        logging.info("Multiple best moves: %s" % best_moves)
        best_move = random.choice(best_moves)
        logging.info("Random best move: %s" % best_move)
    else:
        best_move = best_moves[0]

    # mark next move of this ship as occupied
    game_map[best_move['position']].ship = ship

    # if max_halite['direction'] != Direction.Still:
    #     # mark this position as empty, because we will move away from it next move
    #     game_map[ship.position].ship = None
    # return best move
    # logging.info("Ship %s move %s" % (ship, best_move['position']))

    return best_move['direction']

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []

    all_ships = me.get_ships()
    all_ships = attack_enemy(game, command_queue, all_ships)

    for ship in all_ships:

        if ship.halite_amount >= constants.MAX_HALITE * 0.4:
            # navigate to home
            move = game_map.naive_navigate(ship, me.shipyard.position)
            command_queue.append(ship.move(move))
        else:
            move = collect(ship)
            command_queue.append(ship.move(move))

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= 200 and len(all_ships) <= 17 \
            and me.halite_amount >= constants.SHIP_COST \
            and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
