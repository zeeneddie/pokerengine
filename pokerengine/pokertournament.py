#
# Copyright (C) 2004 Mekensleep
#
# Mekensleep
# 24 rue vieille du temple
# 75004 Paris
#       licensing@mekensleep.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#  Loic Dachary <loic@gnu.org>
#
from math import ceil
from types import StringType
import time

from pokerengine.pokergame import PokerGameServer

TOURNAMENT_STATE_ANNOUNCED = "announced"
TOURNAMENT_STATE_REGISTERING = "registering"
TOURNAMENT_STATE_RUNNING = "running"
TOURNAMENT_STATE_COMPLETE = "complete"
            
def equalizeGames(games, verbose = 0, log_message = None):
    #
    # Games less than 70% full are willing to steal players from other
    # games. Games that are more than 70% full and that are not
    # running are willing to provide players to others.
    #
    want_players = []
    provide_players = []
    for game in games:
        threshold = int(game.max_players * .7)
        count = game.allCount()
        if count < threshold:
            want_players.append([ game.id, game.max_players - count ])
        elif not game.isRunning():
            serials = game.serialsAllSorted()
            provide_players.append((game.id, serials[:count - threshold]))

    results = []

    if len(want_players) <= 0:
        return results

    consumer_index = 0
    for (id, serials) in provide_players:
        want_players.sort(lambda a,b: int(a[1] - b[1]))
        if want_players[0][1] == 0:
            #
            # All satisfied, stop looping
            #
            break

        while len(serials) > 0:
            distributed = False
            for i in xrange(len(want_players)):
                consumer = want_players[consumer_index]
                consumer_index = ( consumer_index + 1 ) % len(want_players)
                if consumer[1] > 0:
                    consumer[1] -= 1
                    serial = serials.pop(0)
                    results.append(( id, consumer[0], serial ))
                    distributed = True
                    if len(serials) <= 0:
                        break
            if not distributed:
                break

#    if len(results) > 0:
#        print "equalizeGames: "
#        pprint(results)

    return results

def breakGames(games, verbose = 0, log_message = None):
    if len(games) < 2:
        return []

    games = games[:]
    #
    # Games not running first, then games running.
    # Each is sorted with games that have least players first.
    #
    games.sort(lambda a,b: a.isRunning() - b.isRunning() or int(a.allCount() - b.allCount()) )

    to_break = [ {
        "id": game.id,
        "seats_left": game.max_players - game.allCount(),
        "serials": game.serialsAll(),
        "to_add": [],
        "running": game.isRunning() } for game in games ]

    if verbose > 2: log_message("breakGames: %s" % to_break)
    results = []
    while True:
        result = breakGame(to_break[0], to_break[1:], verbose, log_message)
        to_break = filter(lambda game: game["seats_left"] > 0, to_break[1:])
        if result == False:
            break
        results.extend(result)
        if len(to_break) < 2:
            break

    return results

def breakGame(to_break, to_fill, verbose = 0, log_message = None):
    #
    # Can't break a game in which players were moved or
    # that are running.
    #
    if len(to_break["to_add"]) > 0 or to_break["running"]:
        return False
    
    seats_left = sum([ game["seats_left"] for game in to_fill ])
    serials = to_break["serials"]
    id = to_break["id"]
    #
    # Don't break a game if there is not enough seats at the
    # other games
    #
    if seats_left < len(serials):
        return False

    #
    # Fill the largest games first, in the hope that the smallest
    # games can be broken later.
    #
    to_fill.reverse()
    result = []
    for game in to_fill:
        if game["seats_left"] > 0:
            count = min(game["seats_left"], len(serials))
            game["to_add"].extend(serials[:count])
            game["seats_left"] -= count
            result.append((id, game["id"], serials[:count]))
            serials = serials[count:]
            if len(serials) <= 0:
                break;

    return result

class PokerTournament:

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name', 'no name')
        self.description_short = kwargs.get('description_short', 'nodescription_short')
        self.description_long = kwargs.get('description_long', 'nodescription_long')
        self.name = kwargs.get('name', 'no name')
        self.serial = kwargs.get('serial', 1)
        self.verbose = kwargs.get('verbose', 0)
        self.players_quota = kwargs.get('players_quota', 10)
        self.variant = kwargs.get('variant', 'holdem')
        self.betting_structure = kwargs.get('betting_structure', 'level-15-30-no-limit')
        self.dirs = kwargs.get('dirs', [])
        self.seats_per_game = kwargs.get('seats_per_game', 10)
        self.sit_n_go = kwargs.get('sit_n_go', 'y')
        self.register_time = kwargs.get('register_time', 0)
        self.start_time = kwargs.get('start_time', 0)
        self.breaks_interval = kwargs.get('breaks_interval', 60)
        self.rebuy_delay = kwargs.get('rebuy_delay', 0)
        self.add_on = kwargs.get('add_on', 0)
        self.add_on_delay = kwargs.get('add_on_delay', 60)
        self.prizes_specs = kwargs.get('prizes_specs', "algorithm")
        self.finish_time = -1
        if type(self.start_time) is StringType:
            self.start_time = int(strftime("%s", strptime(self.start_time, "%Y/%m/%d %H:%M")))
        self.prefix = ""
        
        self.players = []
        self.registered = 0
        self.winners = []
        self.state = TOURNAMENT_STATE_ANNOUNCED
        self.can_register = False
        self.games = []
        self.callback_new_state = lambda tournament: True
        self.callback_create_game = lambda tournament: PokerGameServer("poker.%s.xml", tournament.dirs)
        self.callback_game_filled = lambda tournament, game: True
        self.callback_destroy_game = lambda tournament, game: True
        self.callback_move_player = lambda tournament, from_game_id, to_game_id, serial: self.movePlayer(from_game_id, to_game_id, serial)
        self.callback_remove_player = lambda tournament, game_id, serial: self.removePlayer(game_id, serial)
        self.updateRegistering()

    def message(self, message):
        print self.prefix + "[PokerTournament %s] " % self.name + message
        
    def canRun(self):
        return self.start_time < time.time() and self.sit_n_go == 'y' and self.players_quota <= self.registered

    def getRank(self, serial):
        try:
            winners_count = len(self.winners)
            rank_first = self.registered - winners_count
            return self.winners.index(serial) + rank_first + 1
        except:
            return -1
        
    def updateRegistering(self):
        if self.state == TOURNAMENT_STATE_ANNOUNCED:
            now = time.time()
            if now - self.register_time > 0:
                self.changeState(TOURNAMENT_STATE_REGISTERING)
                return -1
            else:
                return self.register_time - now
        else:
            if self.verbose: self.message("updateRegistering: should not be called while tournament is not in announced state")
            return -1
            
    def changeState(self, state):
        if self.state == TOURNAMENT_STATE_ANNOUNCED and state == TOURNAMENT_STATE_REGISTERING:
            self.can_register = True
        elif self.state == TOURNAMENT_STATE_REGISTERING and state == TOURNAMENT_STATE_RUNNING:
            self.start_time = time.time()
            self.createGames()
            if self.sit_n_go == 'y' or self.registered >= self.players_quota:
                self.can_register = False
        elif self.state == TOURNAMENT_STATE_RUNNING and state == TOURNAMENT_STATE_COMPLETE:
            self.finish_time = time.time()
        else:
            print "PokerTournament:changeState: cannot change from state %s to state %s" % ( self.state, state )
            return
        if self.verbose > 2: self.message("state change %s => %s" % ( self.state, state ))
        self.state = state
        self.callback_new_state(self)

    def isRegistered(self, serial):
        return serial in self.players
        
    def canRegister(self, serial):
        if self.can_register:
            return not self.isRegistered(serial)
        else:
            return False

    def canUnregister(self, serial):
        return self.isRegistered(serial) and self.state == TOURNAMENT_STATE_REGISTERING
        
    def register(self, serial):
        if self.can_register:
            self.players.append(serial)
            self.registered += 1
            if self.state == TOURNAMENT_STATE_REGISTERING:
                if self.canRun(): self.changeState(TOURNAMENT_STATE_RUNNING)
            elif self.state == TOURNAMENT_STATE_RUNNING:
                self.sitPlayer(serial)
            return True
        else:
            return False

    def unregister(self, serial):
        if self.state == TOURNAMENT_STATE_REGISTERING:
            self.players.remove(serial)
            self.registered -= 1
            return True
        else:
            return False

    def sitPlayer(self, serial):
        pass

    def removePlayer(self, game_id, serial):
        game = self.id2game[game_id]
        game.removePlayer(serial)

    def movePlayer(self, from_game_id, to_game_id, serial):
        from_game = self.id2game[from_game_id]
        to_game = self.id2game[to_game_id]
        from_game.open()
        to_game.open()
        from_player = from_game.getPlayer(serial)
        to_game.addPlayer(serial)
        to_player = to_game.getPlayer(serial)
        to_game.payBuyIn(serial, from_player.money)
        to_game.sit(serial)
        to_game.autoBlindAnte(serial)
        to_player.name = from_player.name
        if(from_player.isSitOut()): to_game.sitOut(serial)
        if(from_player.isBot()): to_game.botPlayer(serial)
        from_game.removePlayer(serial)
        from_game.close()
        to_game.close()
    
    def createGames(self):
        games_count = int(ceil(self.registered / float(self.seats_per_game)))
        self.players_quota = games_count * self.seats_per_game
        players = self.players[:]
        for id in xrange(1, games_count + 1):
            game = self.callback_create_game(self)
            game.verbose = self.verbose
            game.setTime(0)
            game.setVariant(self.variant)
            game.setBettingStructure(self.betting_structure)
            game.setMaxPlayers(self.seats_per_game)
            if game.id == 0: game.id = id

            buy_in = game.buyIn()
            for seat in xrange(self.seats_per_game):
                player = players.pop()
                game.addPlayer(player)
                game.payBuyIn(player, buy_in)
                game.sit(player)
                game.autoBlindAnte(player)
            self.games.append(game)
            self.callback_game_filled(self, game)
            game.close()
        self.id2game = dict(zip([ game.id for game in self.games ], self.games))

    def endTurn(self, game_id):
        game = self.id2game[game_id]
        loosers = game.serialsBroke()
        loosers_count = len(loosers)

        if loosers_count == 1:
            self.winners.insert(0, loosers[0])
            self.callback_remove_player(self, game_id, loosers[0])
            if self.verbose > 2: self.message("winners %s" % self.winners)
        elif loosers_count > 1:
            for serial in loosers:
                self.winners.insert(0, serial)
                self.callback_remove_player(self, game_id, serial)
            if self.verbose > 2: self.message("winners %s" % self.winners)

        if len(self.winners) + 1 == self.registered:
            game = self.games[0]
            player = game.playersAll()[0]
            self.winners.insert(0, player.serial)
            self.callback_remove_player(self, game.id, player.serial)
            money = player.money.toint()
            player.money.set(0)
            expected = game.buyIn() * self.registered
            if money != expected:
                self.message("ERROR winner has %d chips and should have %d chips" % ( money, expected ))
            if self.verbose: self.message("winners %s" % self.winners)
            self.callback_destroy_game(self, game)
            self.games = []
            self.id2game = {}
            self.changeState(TOURNAMENT_STATE_COMPLETE)
            return False
        else:
            if loosers_count > 0: self.balanceGames()
            return True
        
    def balanceGames(self):
        to_break = breakGames(self.games, self.verbose, self.message)
        games_broken = {}
        for (from_id, to_id, serials) in to_break:
            for serial in serials:
                if self.verbose > 2: self.message("balanceGames: player %d moved from %d to %d" % ( serial, from_id, to_id ))
                self.callback_move_player(self, from_id, to_id, serial)
            games_broken[from_id] = True

        if len(to_break) > 0:
            for game_id in games_broken.keys():
                game = self.id2game[game_id]
                self.callback_destroy_game(self, game)
                self.games.remove(game)
                del self.id2game[game.id]
            if self.verbose: self.message("balanceGames: broke tables %s" % to_break)
            return True
        
        to_equalize = equalizeGames(self.games, self.verbose, self.message)
        for (from_id, to_id, serial) in to_equalize:
            if self.verbose > 2: self.message("balanceGames: player %d moved from %d to %d" % ( serial, from_id, to_id ))
            self.callback_move_player(self, from_id, to_id, serial)

        return len(to_equalize) > 0

    def prizes(self, buy_in):
        if self.can_register:
            return None
        if self.prizes_specs == "algorithm":
            return self.prizesAlgorithm(buy_in)
        else:
            return None

    def prizesAlgorithm(self, buy_in):
        candidates_count = self.registered
        if candidates_count < 5:
            winners = 1
        elif candidates_count < 10:
            winners = 2
        elif candidates_count < 20:
            winners = 3
        elif candidates_count < 30:
            winners = 4
        elif candidates_count < 40:
            winners = 6
        elif candidates_count < 50:
            winners = int(candidates_count * 0.2)
        elif candidates_count < 200:
            winners = int(candidates_count * 0.15)
        else:
            winners = int(candidates_count * 0.1)

        prizes = []
        money_left = buy_in * candidates_count
        while winners > 0:
            if money_left / winners < int(buy_in * 2.5):
                prizes.extend([ money_left / winners ] * winners)
                winners = 0
            else:
                money_left /= 2
                winners -= 1
                prizes.append(money_left)
        rest = buy_in * candidates_count - sum(prizes)
        prizes[0] += rest
        return prizes
                