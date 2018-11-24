#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
import logging

BOT_VERSION = "stand-still"

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
        game.end_turn([])


if __name__ == "__main__":
    main()
