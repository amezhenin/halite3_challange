#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
from hlt.entity import Ship
from hlt.positionals import Direction, Position
import random
import logging

BOT_VERSION = "amezhenin-v10"
DIRECTIONS = [Direction.North, Direction.South, Direction.East, Direction.West]
SHIP_BUILD_MAX_TURN = 200
MAX_OWN_SHIPS = 15


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


def construct_dropoff(game, command_queue, all_ships):
    me = game.me
    game_map = game.game_map

    if game.turn_number < 50 \
            or len(me.get_dropoffs()) > 0 \
            or me.halite_amount < constants.DROPOFF_COST:
        return all_ships

    # scan all position and find a closest to shipyard closest with max halite
    closest_cand = None
    closest_dist = 9999
    max_halite = 0
    for w in range(0, game_map.width):
        for h in range(0, game_map.height):
            p = Position(w, h)
            dist = game_map.calculate_distance(p, me.shipyard.position)
            if dist < 10:
                continue
            halite = game_map[p].halite_amount
            if halite > max_halite or (halite == max_halite and dist < closest_dist):
                logging.info("New candidate dist %s with pos %s with halite %s" % (dist, p, halite))
                closest_cand = p
                closest_dist = dist
                max_halite = halite

    if not closest_cand:
        return all_ships

    # pick closest ship to that position
    closest_ship = all_ships[0]
    closest_dist = 9999
    for ship in all_ships:
        dist = game_map.calculate_distance(ship.position, closest_cand)
        if dist < closest_dist:
            logging.info("New ship dist %s with pos %s" % (dist, ship.position))
            closest_ship = ship
            closest_dist = dist

    # move there
    if closest_dist != 0:
        move = game_map.naive_navigate(closest_ship, closest_cand)
        command_queue.append(closest_ship.move(move))
        all_ships = list(filter(lambda x: x.id != closest_ship.id, all_ships))
        return all_ships

    # if we are there, try to build a dropoff
    logging.info("Ship %s is making dropoff" % closest_ship)
    command_queue.append(closest_ship.make_dropoff())
    all_ships = list(filter(lambda x: x.id != closest_ship.id, all_ships))
    return all_ships


def collect(game, ship):
    me = game.me
    game_map = game.game_map

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
    # logging.info(pos_choices)

    best_moves = list(filter(lambda x: x['halite'] == max_halite, pos_choices))
    if len(best_moves) > 1:
        logging.info("Multiple best moves: %s" % best_moves)
        best_move = random.choice(best_moves)
        logging.info("Random best move: %s" % best_move)
    else:
        best_move = best_moves[0]

    # mark next move of this ship as occupied
    game_map[best_move['position']].ship = Ship(me, random.randint(1000, 10000), ship.position, 0)
    # game_map[best_move['position']].ship = ship

    # if max_halite['direction'] != Direction.Still:
    #     # mark this position as empty, because we will move away from it next move
    #     game_map[ship.position].ship = None
    # return best move
    # logging.info("Ship %s move %s" % (ship, best_move['position']))

    return best_move['direction']


def drop_halite(game, ship, force=False):
    me = game.me
    game_map = game.game_map

    dropoffs = me.get_dropoffs()
    if len(dropoffs):
        drop_pos = dropoffs[0].position
    else:
        drop_pos = me.shipyard.position

    if force is False:
        if game_map[drop_pos].ship and game_map[drop_pos].ship.owner != me:
            # attack enemy in my dropoff
            game_map[drop_pos].ship = None
        move = game_map.naive_navigate(ship, drop_pos)
    else:
        # set dropoff/shipyard as empty
        game_map[drop_pos].ship = None
        move = game_map.naive_navigate(ship, drop_pos)

    # make it unsafe to
    # logging.info("Current %s move %s next pos %s" % (ship.position, move, ship.position + Position(*move)))
    # FIXME: rewrite navigation and remove this dummy creation
    game_map[ship.position + Position(*move)].ship = Ship(me, random.randint(1000, 10000),
                                                          ship.position + Position(*move), 0)
    # game_map[ship.position].ship = None
    return move


def is_end_game(game, ship):
    me = game.me
    game_map = game.game_map

    home_dist = game_map.calculate_distance(ship.position, me.shipyard.position)
    res = home_dist + 10 > (constants.MAX_TURNS - game.turn_number)
    return res


def main():
    """ <<<Game Begin>>> """

    # This game object contains the initial game state.
    game = hlt.Game()
    # At this point "game" variable is populated with initial map data.
    # This is a good place to do computationally expensive start-up pre-processing.
    # As soon as you call "ready" function below, the 2 second per turn timer will start.
    game.ready(BOT_VERSION)

    # Now that your bot is initialized, save a message to yourself in the log file with some important information.
    #   Here, you log here your id, which you can always fetch from the game object by using my_id.
    logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))
    logging.info("Max turns %s" % constants.MAX_TURNS)

    """ <<<Game Loop>>> """
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
        all_ships = construct_dropoff(game, command_queue, all_ships)

        for ship in all_ships:
            if ship.halite_amount >= constants.MAX_HALITE * 0.6:
                # navigate to home
                move = drop_halite(game, ship)
                command_queue.append(ship.move(move))
            elif is_end_game(game, ship):
                move = drop_halite(game, ship, force=True)
                command_queue.append(ship.move(move))
            else:
                move = collect(game, ship)
                command_queue.append(ship.move(move))

        # If the game is in the first X turns and you have enough halite, spawn a ship.
        # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
        if game.turn_number <= SHIP_BUILD_MAX_TURN and len(all_ships) <= MAX_OWN_SHIPS \
                and me.halite_amount >= constants.SHIP_COST \
                and not game_map[me.shipyard].is_occupied:
            command_queue.append(me.shipyard.spawn())

        # Send your moves back to the game environment, ending this turn.
        game.end_turn(command_queue)


if __name__ == "__main__":
    main()
