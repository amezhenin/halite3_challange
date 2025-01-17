#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
from collections import defaultdict
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction


# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging


def attack_enemy(game, command_queue, ship_status):
    me = game.me
    game_map = game.game_map

    enemies = game.players.values()
    enemies = list(filter(lambda x: x.id != me.id, enemies))
    if len(enemies) != 1:
        return
    enemy = enemies[0]

    # find attacking ship
    logging.info("Statuses %s" % ship_status.items())

    ship = list(filter(lambda x: x[1] == "attack_shipyard", ship_status.items()))

    logging.info("Ships %s" % ship)
    # if not found , assign one
    if len(ship) == 0:
        ship = list(me.get_ships())
        if len(ship) == 0:
            return
        ship = ship[0]
        logging.info("Turning %s ship into attacking ship" % ship)
        ship_status[ship.id] = "attack_shipyard"
        pass
    # if found move it to the enemy shipyard
    else:
        ship = list(filter(lambda x: x.id == ship[0][0], me.get_ships()))[0]
        logging.info("found ship %s" % repr(ship))

    move = game_map.naive_navigate(ship, enemy.shipyard.position)
    command_queue.append(ship.move(move))

    pass


""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("amezhenin-v3")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

DIRECTIONS = [Direction.Still, Direction.North, Direction.South, Direction.East, Direction.West]


def collect(ship):
    pos_choices = [ship.position] + ship.position.get_surrounding_cardinals()
    halite_choices = list(map(lambda x: game_map[x].halite_amount, pos_choices))
    halite_choices[0] *= 2  # we prefer to stand still
    max_idx = halite_choices.index(max(halite_choices))
    return DIRECTIONS[max_idx]

ship_status = defaultdict(lambda: "collecting")

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

    attack_enemy(game, command_queue, ship_status)

    for ship in me.get_ships():


        if ship_status[ship.id] == "collecting":
            if ship.halite_amount >= constants.MAX_HALITE * 0.4:
                # navigate to home
                ship_status[ship.id] = "returning"
                move = game_map.naive_navigate(ship, me.shipyard.position)
                command_queue.append(ship.move(move))
            else:
                move = collect(ship)
                command_queue.append(ship.move(move))

        elif ship_status[ship.id] == "returning":
            if ship.halite_amount == 0:
                ship_status[ship.id] = "collecting"
            else:
                move = game_map.naive_navigate(ship, me.shipyard.position)
                command_queue.append(ship.move(move))
        else:
            pass

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    turns_to_generate = 3 if len(game.players) == 2 else 1
    if game.turn_number <= turns_to_generate \
            and me.halite_amount >= constants.SHIP_COST \
            and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())



    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
