#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2006 - 2010 Loic Dachary <loic@dachary.org>
# Copyright (C) 2008 Bradley M. Kuhn <bkuhn@ebb.org>
# Copyright (C) 2004, 2005, 2006 Mekensleep
#
# Mekensleep
# 26 rue des rosiers
# 75004 Paris
#       licensing@mekensleep.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors:
#  Loic Dachary <loic@dachary.org>
#  Bradley M. Kuhn <bkuhn@ebb.org>
#

import unittest, sys
from os import path

TESTS_PATH = path.dirname(path.realpath(__file__))
sys.path.insert(0, path.join(TESTS_PATH, ".."))

from pokerengine.pokergame import PokerGameServer
from string import split

import reflogging
log = reflogging.root_logger.get_child('test_blinds')

try:
    from nose.plugins.attrib import attr
except ImportError, e:
    def attr(fn): return fn

class PokerPredefinedDecks:

    def __init__(self, decks):
        self.decks = decks
        self.index = 0

    def shuffle(self, deck):
        deck[:] = self.decks[self.index][:]
        self.index += 1
        if self.index >= len(self.decks):
            self.index = 0


class TestBlinds(unittest.TestCase):

    def setUp(self):
        self.game = PokerGameServer("poker.%s.xml", [path.join(TESTS_PATH, '../conf')])
        self.game.setVariant("holdem")
        self.game.setBettingStructure("1-2_20-200_limit")
        self.amounts = {}
        self.amounts['big'] = 2
        self.amounts['small'] = 1
        predefined_decks = [
            "8d 2h 2c 8c 4c Kc Ad 9d Ts Jd 5h Tc 4d 9h 8h 7h 9c 2s 3c Kd 5s Td 5d Th 3s Kh Js Qh 7d 2d 3d 9s Qd Ac Jh Jc Qc 6c 7s Ks 5c 4h 7c 4s Qs 6s 6h Ah 6d As 3h 8s", # distributed from the end
            ]
        self.game.shuffler = PokerPredefinedDecks(map(lambda deck: self.game.eval.string2card(split(deck)), predefined_decks))

    def tearDown(self):
        del self.game

    def make_new_bot(self, serial, seat):
        game = self.game
        self.failUnless(game.addPlayer(serial, seat))
        self.failUnless(game.payBuyIn(serial, game.bestBuyIn()))
        self.failUnless(game.sit(serial))
        game.botPlayer(serial)
        game.noAutoBlindAnte(serial)

    def make_new_player(self, serial, seat):
        game = self.game
        self.failUnless(game.addPlayer(serial, seat))
        self.failUnless(game.payBuyIn(serial, game.bestBuyIn()))
        self.failUnless(game.sit(serial))

    def pay_blinds(self, skipSerials = {}):
        game = self.game
        for serial in game.serialsAll():
            if serial in skipSerials: continue 
            game.autoBlindAnte(serial)
        for serial in game.serialsAll():
            if serial in skipSerials: continue 
            game.noAutoBlindAnte(serial)

    def check_button(self, serial):
        self.assertEquals(self.game.player_list[self.game.dealer], serial)

    def check_blinds(self, descriptions):
        players = self.game.playersAll()
        players.sort(key=lambda i: i.seat)
        failStr = None
        ii = 0
        for player in players:
            ii += 1
            (blind, missed, wait, missedCount) = descriptions.pop(0)
            if(blind != player.blind or missed != player.missed_blind or wait != player.wait_for or player.missed_big_blind_count != missedCount):
                failStr = "%d check_blinds FAILED actual %s != from expected %s" % ( ii, (player.blind, player.missed_blind, player.wait_for, player.missed_big_blind_count), (blind, missed, wait, missedCount) )
                log.debug(failStr)
            else:
                goodStr = "%d check_blinds %s == %s" % (ii, (player.blind, player.missed_blind, player.wait_for, player.missed_big_blind_count), (blind, missed, wait, missedCount) )
                log.debug(goodStr)
        if failStr:
            self.fail(failStr)
            
    def confirm_blind(self, hist, acceptedEntries):
        for ee in acceptedEntries:
            (val1, val2, val3) = ee
            ee = ('blind', val1, val2, val3)
            self.assertEquals(ee in hist, True)
            hist.remove(ee)
        for hh in hist:
            self.assertNotEquals(hh[0], 'blind')
            self.assertNotEquals(hh[0], 'ante')

    def confirm_hist(self, hist, acceptedEntries):
        for ee in acceptedEntries:
            self.assertEquals(ee in hist, True)
            hist.remove(ee)

    def test1(self):
        big = self.amounts['big']
        small = self.amounts['small']

        seat2serial = {}
        for (serial, seat) in ((1, 0), (2, 1), (3, 2), (4, 3)):
            self.make_new_bot(serial, seat)
            seat2serial[seat] = serial
        self.game.beginTurn(1)
        # (blind, missed, wait, missedCount)

        self.check_button(1)
        self.check_blinds([
            (False, None, False, 0), # 1
            ('small', None, False, 0), # 2
            ('big', None, False, 0), # 3
            (False, None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(3, big, 0), (2, small, 0)])

        self.game.beginTurn(2)
        self.check_button(2)
        # (blind, missed, wait, missedCount)
        self.check_blinds([
            (False, None, False, 0), # 1
            (False, None, False, 0), # 2
            ('small', None, False, 0), # 3
            ('big', None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(4, big, 0), (3, small, 0)])

        self.game.beginTurn(3)
        self.check_button(3)
        # (blind, missed, wait, missedCount)
        self.check_blinds([
            ('big', None, False, 0), # 1
            (False, None, False, 0), # 2
            (False, None, False, 0), # 3
            ('small', None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(1, big, 0), (4, small, 0)])

        self.game.beginTurn(4)
        # (blind, missed, wait)
        self.check_button(4)
        self.check_blinds([
            ('small', None, False, 0), # 1
            ('big', None, False, 0), # 2
            (False, None, False, 0), # 3
            (False, None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(2, big, 0), (1, small, 0)])
    # --------------------------------------------------------------------------
    def test2(self):
        """
        Two new players enter the game and both pay the big blind
        """
        big = self.amounts['big']
        small = self.amounts['small']

        for (serial, seat) in ((1, 0), (2, 1), (3, 2), (4, 8)):
            self.make_new_bot(serial, seat)
        self.game.beginTurn(1)
        self.check_button(1)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            ('small', None, False, 0), # 2
            ('big', None, False, 0), # 3
            (False, None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(3, big, 0), (2, small, 0)])

        for (serial, seat) in ((10, 4), (11, 5)):
            self.make_new_bot(serial, seat)

        self.game.beginTurn(2)
        self.check_button(2)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            (False, None, False, 0), # 2
            ('small', None, False, 0), # 3
            ('big', 'n/a', False, 0), # 10
            ('late', 'n/a', False, 0), # 11
            (False, None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(11, big, 0), (10, big, 0), (3, small, 0)])
    # --------------------------------------------------------------------------
    def test3(self):
        """
        Two new players enter the game between the small
        and big blind. They are allowed to play during the
        second turn because they cannot be awarded the button
        as they arrive.
        """
        big = self.amounts['big']
        small = self.amounts['small']

        for (serial, seat) in ((1, 0), (2, 1), (3, 7), (4, 8)):
            self.make_new_bot(serial, seat)
        self.game.beginTurn(1)
        self.check_button(1)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            ('small', None, False, 0), # 2
            ('big', None, False, 0), # 3
            (False, None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(2, small, 0), (3, big, 0)])

        for (serial, seat) in ((10, 4), (11, 5)):
            self.make_new_bot(serial, seat)

        self.game.beginTurn(2)
        # (blind, missed, wait)
        self.check_button(2)
        self.check_blinds([
            (False, None, False, 0), # 1
            (False, None, False, 0), # 2
            (False, 'n/a', 'late', 0), # 10
            (False, 'n/a', 'late', 0), # 11
            ('small', None, False, 0), # 3
            ('big', None, False, 0), # 4
        ])
        self.pay_blinds()
        history = self.game.turn_history
        self.confirm_blind(history, [(4, big, 0), (3, small, 0)])
        # players who did not pay the big blind are removed from
        # the history by historyReduce
        game_index = 0
        player_list_index = 7
        serial2chips_index = 9
        self.assertEqual(history[game_index][player_list_index], [1, 2, 10, 11, 3, 4])
        self.assertEqual(history[game_index][serial2chips_index].keys(), [1, 2, 3, 4, 10, 11])
        self.game.historyReduce()
        self.game.historyReduce()
        self.assertEqual(self.game.turn_history[game_index][player_list_index], [1, 2, 3, 4])
        self.assertEqual(self.game.turn_history[game_index][serial2chips_index].keys(), [1, 2, 3, 4])

        self.game.beginTurn(3)
        self.check_button(3)
        # (blind, missed, wait)
        self.check_blinds([
            ('big', None, False, 0), # 1
            (False, None, False, 0), # 2
            ('late', 'n/a', False, 0), # 10
            ('late', 'n/a', False, 0), # 11
            (False, None, False, 0), # 3
            ('small', None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(1, big, 0), (10, big, 0),(11, big, 0), (4, small, 0)])
        self.game.beginTurn(4)
        # (blind, missed, wait)
        self.check_button(4)
        self.check_blinds([
            ('small', None, False, 0), # 1
            ('big', None, False, 0), # 2
            (False, None, False, 0), # 10
            (False, None, False, 0), # 11
            (False, None, False, 0), # 3
            (False, None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(1, small, 0), (2, big, 0)])
    # --------------------------------------------------------------------------
    def test4_fourPlayers_player4missedBothBlinds_onlyBigRequired(self):
        """
        Less than 6 players, player 4 missed the big and small blinds and
        must pay the big blind when back in the game.  The missed blind
        count only ever goes to one, because the player is not passed again.
        """
        big = self.amounts['big']
        small = self.amounts['small']

        for (serial, seat) in ((1, 0), (2, 1), (3, 2), (4, 3)):
            self.make_new_bot(serial, seat)
        self.game.beginTurn(1)
        self.check_button(1)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            ('small', None, False, 0), # 2
            ('big', None, False, 0), # 3
            (False, None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(2, small, 0), (3, big, 0)])

        self.game.sitOut(4)

        self.game.beginTurn(2)
        self.check_button(2)
        # (blind, missed, wait)
        self.check_blinds([
            ('big', None, False, 0), # 1
            (False, None, False, 0), # 2
            ('small', None, False, 0), # 3
            (False, 'big', False, 1), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(3, small, 0), (1, big, 0)])
        
        self.game.beginTurn(3)
        self.check_button(3)
        # (blind, missed, wait)
        self.check_blinds([
            ('small', None, False, 0), # 1
            ('big', None, False, 0), # 2
            (False, None, False, 0), # 3
            (False, 'big', False, 1), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(1, small, 0), (2, big, 0)])
        self.assertEquals(self.game.serial2player[4].getMissedRoundCount(), 1)
        self.assertEquals(self.game.serial2player[1].getMissedRoundCount(), 0)
        self.game.sit(4)
        
        self.game.beginTurn(4)
        self.check_button(1)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            ('small', None, False, 0), # 2
            ('big', None, False, 0), # 3
            ('late', 'big', False, 1), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(2, small, 0), (3, big, 0),(4, big, 0)])

        self.game.beginTurn(5)
        self.check_button(2)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            (False, None, False, 0), # 2
            ('small', None, False, 0), # 3
            ('big', None, False, 0), # 4
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(3, small, 0), (4, big, 0)])

    # --------------------------------------------------------------------------
    def test5_sixPlayers_missedBothBlinds_bothRequired(self):
        """
        At six players, player 4 missed the big and small blinds and
        must pay BOTH when back in the game.  The missed blind
        count only ever goes to one, because the player is not passed again.
        """
        big = self.amounts['big']
        small = self.amounts['small']

        for (serial, seat) in ((1, 0), (2, 1), (3, 2), (4, 3), (5, 4), (6, 5)):
            self.make_new_bot(serial, seat)
        self.game.beginTurn(1)
        self.check_button(1)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            ('small', None, False, 0), # 2
            ('big', None, False, 0), # 3
            (False, None, False, 0), # 4
            (False, None, False, 0), # 5
            (False, None, False, 0), # 6
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(2, small, 0), (3, big, 0)])

        self.game.sitOut(4)

        self.game.beginTurn(2)
        self.check_button(2)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            (False, None, False, 0), # 2
            ('small', None, False, 0), # 3
            (False, 'big', False, 1), # 4
            ('big', None, False, 0), # 5
            (False, None, False, 0), # 6
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(3, small, 0), (5, big, 0)])
        
        self.game.beginTurn(3)
        self.check_button(3)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            (False, None, False, 0), # 2
            (False, None, False, 0), # 3
            (False, 'big', False, 1), # 4
            ('small', None, False, 0), # 5
            ('big', None, False, 0), # 6
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(5, small, 0), (6, big, 0)])
        self.assertEquals(self.game.serial2player[4].getMissedRoundCount(), 1)

        self.game.sit(4)
        
        self.game.beginTurn(4)
        self.check_button(5)
        # (blind, missed, wait)
        self.check_blinds([
            ('big', None, False, 0), # 1
            (False, None, False, 0), # 2
            (False, None, False, 0), # 3
            ('big_and_dead', 'big', False, 1), # 4
            (False, None, False, 0), # 5
            ('small', None, False, 0), # 6
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(6, small, 0), (1, big, 0), (4, big, small)])
        self.game.beginTurn(5)
        # (blind, missed, wait)
        self.check_blinds([
            ('small', None, False, 0), # 1
            ('big', None, False, 0), # 2
            (False, None, False, 0), # 3
            (False, None, False, 0), # 4
            (False, None, False, 0), # 5
            (False, None, False, 0), # 6
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(1, small, 0), (2, big, 0)])
    # --------------------------------------------------------------------------
    def test6_fivePlayers_multiDecline_noHandStarts(self):
        """Five players, goes 2 handed before first hand dealt.  Others sit in after.
        At five players, 1, 2 and 4 sit out before first hand begins.  3
        accepts the small blind, as 1, 2, and 4 sit back in.  5 rejects
        the big blind, and the turn ends.  We restart with the five
        sitting out and blinds in the right place.
        """
        big = self.amounts['big']
        small = self.amounts['small']

        for (serial, seat) in ((1, 0), (2, 1), (3, 2), (4, 3), (5, 4)):
            self.make_new_bot(serial, seat)
        self.game.sitOut(1)
        self.game.sitOut(2)
        self.game.sitOut(4)
        self.game.beginTurn(1)
        self.check_button(5)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            (False, 'small', False, 0), # 2
            ('small', None, False, 0), # 3
            (False, 'big', False, 1), # 4
            ('big', None, False, 0), # 5
        ])
        self.assertEquals(self.game.serial2player[4].getMissedRoundCount(), 1)
        self.game.sit(1)
        self.game.sit(2)
        self.game.autoBlindAnte(3)
        self.game.noAutoBlindAnte(3)
        self.game.sit(4)
        self.confirm_hist(self.game.turn_history, [('blind_request', 5, big, 0, 'big'), ('blind', 3, small, 0)])
        self.check_button(5)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, 'first_round', 0), # 1
            (False, 'small', 'first_round', 0), # 2
            (True, None, False, 0), # 3
            (False, 'big', 'first_round', 1), # 4
            ('big', None, False, 0), # 5
        ])

        self.game.sitOut(5)
        self.confirm_hist(self.game.turn_history, [('canceled', 3, small)])

        self.failUnless(self.game.state, "end")
        self.failUnless(self.game.serial2player[3].money, self.game.bestBuyIn())

        self.game.sitOut(5)
        self.game.beginTurn(2)
        self.check_button(1)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            ('small', None, False, 0), # 2
            ('big', None, False, 0), # 3
            (False, None, False, 0), # 4
            (False, None, False, 0), # 5
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(2, small, 0), (3, big, 0)])
    # --------------------------------------------------------------------------
    def test7_specialTwoWaitForPost(self):
        """Special case where two players came in waiting to post.
        """
        game = self.game
#        for (serial, seat) in ((1, 0), (2, 1), (3, 2), (4, 3)):
        for (serial, seat) in ((1, 2), (2, 3)):
            self.make_new_bot(serial, seat)
        game.beginTurn(1)
        self.pay_blinds()

        self.game.beginTurn(2)
        # (blind, missed, wait)
        self.check_blinds([
            ('small', None, False, 0), # 1
            ('big', None, False, 0), # 2
        ])
        game.autoBlindAnte(1)
        game.noAutoBlindAnte(1)
        game.autoBlindAnte(2)
        game.noAutoBlindAnte(2)
        game.sitOutNextTurn(2)
        self.failUnless(self.game.state, "end")

        #
        # Two players came in and are waiting for
        # the late blind because they attempted to enter
        # either on the small blind or the dealer position.
        # Fake this situation instead of playing hands that
        # will lead to the same because it introduces an
        # complexity that is not necessary. This case can happen
        # indeed although very rarely.
        #
        for (serial, seat) in ((3, 0), (4, 7)):
            self.make_new_player(serial, seat)
            game.getPlayer(serial).wait_for = 'late'

        self.game.beginTurn(3)
        # (blind, missed, wait)
        self.check_blinds([
            ('big', None, False, 0), # 1
            (False, None, False, 0), # 2
            (False, 'small', False, 0), # 3
            ('small', None, False, 0) # 4
        ])

    # --------------------------------------------------------------------------
    def test8_updateBlinds(self):
        """updateBlinds() test
        """
        game = self.game
        for (serial, seat) in ((1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6)):
            self.make_new_bot(serial, seat)
        game.player_list = [1, 3, 4, 5, 6]
        game.dealer_seat = 3
        for (serial, blind_info) in (
            (1, ("big", "n/a", False, 0)),
            (2, ("late", "n/a", "first_round", 0)),
            (3, (False, None, False, 0)),
            (4, (False, "n/a", "late", 0)),
            (5, (False, "n/a", "late", 0)),
            (6, (True, None, False, 0)),
        ):
            player = game.getPlayer(serial)
            player.blind, player.missed_blind, player.wait_for, player.missed_big_blind_count = blind_info

        game.updateBlinds()
        self.check_blinds([
            ("big", "n/a", False, 0),
            ("late", "n/a", "first_round", 0),
            (False, None, False, 0),
            (False, "n/a", "late", 0),
            (False, "n/a", "late", 0),
            (True, None, False, 0),
        ])
    # --------------------------------------------------------------------------
    def test9_fivePlayers_missedBothBlinds_onlyBigRequired(self):
        """
        Less than 6 players, player 4 missed the big and small blinds and
        must pay the big blind when back in the game.  The missed blind
        count only ever goes to one, because the player is not passed again.
        """
        big = self.amounts['big']
        small = self.amounts['small']

        for (serial, seat) in ((1, 0), (2, 1), (3, 2), (4, 3), (5, 4)):
            self.make_new_bot(serial, seat)
        self.game.beginTurn(1)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            ('small', None, False, 0), # 2
            ('big', None, False, 0), # 3
            (False, None, False, 0), # 4
            (False, None, False, 0), # 5
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(2, small, 0), (3, big, 0)])

        self.game.sitOut(4)

        self.game.beginTurn(2)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            (False, None, False, 0), # 2
            ('small', None, False, 0), # 3
            (False, 'big', False, 1), # 4
            ('big', None, False, 0), # 5
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(3, small, 0), (5, big, 0)])
        
        self.game.beginTurn(3)
        # (blind, missed, wait)
        self.check_blinds([
            ('big', None, False, 0), # 1
            (False, None, False, 0), # 2
            (False, None, False, 0), # 3
            (False, 'big', False, 1), # 4
            ('small', None, False, 0), # 5
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(5, small, 0), (1, big, 0)])
        self.assertEquals(self.game.serial2player[4].getMissedRoundCount(), 1)
        self.game.sit(4)
        
        self.game.beginTurn(4)
        # (blind, missed, wait)
        self.assertEquals(self.game.serial2player[4].getMissedRoundCount(), 1)
        self.check_blinds([
            ('small', None, False, 0), # 1
            ('big', None, False, 0), # 2
            (False, None, False, 0), # 3
            ('late', 'big', False, 1), # 4
            (False, None, False, 0), # 5
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(1, small, 0), (2, big, 0), (4, big, 0)])

        self.assertEquals(self.game.serial2player[4].getMissedRoundCount(), 0)
        self.game.beginTurn(5)
        # (blind, missed, wait)
        self.check_blinds([
            (False, None, False, 0), # 1
            ('small', None, False, 0), # 2
            ('big', None, False, 0), # 3
            (False, None, False, 0), # 4
            (False, None, False, 0), # 5
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(2, small, 0), (3, big, 0)])
    # --------------------------------------------------------------------------
    def test11_sixPlayers_fiveSitsOutForALongTime(self):
        """test11_sixPlayers_fiveSitsOutForALongTime
        Tests six players where the fifth sits out for a long time and the counter runs.
        """
        big = self.amounts['big']
        small = self.amounts['small']

        for (serial, seat) in ((100, 0), (101, 1), (102, 2), (103, 3), (104, 4), (105, 5)):
            self.make_new_bot(serial, seat)

        turn = 0
        missedCounterVerify = 0
        missedSoFar = None
        self.assertEquals(self.game.sitOut(105), True)
        while missedCounterVerify < 4:
            for serial in [100, 101, 102, 103, 104, 105]:
                amount = self.game.maxBuyIn() - self.game.serial2player[serial].money
                self.game.rebuy(serial, amount)

            turn += 1
            self.game.beginTurn(turn)
            self.check_button(100)
            self.assertEquals(self.game.isSitOut(105), True)
            self.check_blinds([
                (False, None, False, 0), # 100
                ('small', None, False, 0), # 101
                ('big', None, False, 0), # 102
                (False, None, False, 0), # 103
                (False, None, False, 0), # 104
                (False, missedSoFar, False, missedCounterVerify), # 105
            ])
            self.pay_blinds()
            self.confirm_blind(self.game.turn_history, [(101, small, 0), (102, big, 0)])

            turn += 1
            self.assertEquals(self.game.isSitOut(105), True)
            self.game.beginTurn(turn)
            self.check_button(101)
            self.check_blinds([
                (False, None, False, 0), # 100
                (False, None, False, 0), # 101
                ('small', None, False, 0), # 102
                ('big', None, False, 0), # 103
                (False, None, False, 0), # 104
                (False, missedSoFar, False, missedCounterVerify), # 105
            ])

            self.pay_blinds(skipSerials = { 105 : 105 })
            self.confirm_blind(self.game.turn_history, [(102, small, 0), (103, big, 0)])

            turn += 1
            self.assertEquals(self.game.isSitOut(105), True)
            self.game.beginTurn(turn)
            self.check_button(102)
            self.check_blinds([
                (False, None, False, 0), # 100
                (False, None, False, 0), # 101
                (False, None, False, 0), # 102
                ('small', None, False, 0), # 103
                ('big', None, False, 0), # 104
                (False, missedSoFar, False, missedCounterVerify), # 105
            ])
            self.pay_blinds(skipSerials = { 105 : 105 })
            self.confirm_blind(self.game.turn_history, [(103, small, 0), (104, big, 0)])

            turn += 1
            missedCounterVerify += 1
            self.assertEquals(self.game.isSitOut(105), True)
            self.game.beginTurn(turn)
            self.check_button(103)
            missedSoFar = 'big'
            self.check_blinds([
                ('big', None, False, 0), # 100
                (False, None, False, 0), # 101
                (False, None, False, 0), # 102
                (False, None, False, 0), # 103
                ('small', None, False, 0), # 104
                (False, missedSoFar, False, missedCounterVerify), # 105
            ])
            self.pay_blinds(skipSerials = { 105 : 105 })
            self.confirm_blind(self.game.turn_history, [(104, small, 0), (100, big, 0)])

            turn += 1
            self.game.beginTurn(turn)
            self.check_button(104)
            self.assertEquals(self.game.isSitOut(105), True)
            self.check_blinds([
                ('small', None, False, 0), # 100
                ('big', None, False, 0), # 101
                (False, None, False, 0), # 102
                (False, None, False, 0), # 103
                (False, None, False, 0), # 104
                (False, missedSoFar, False, missedCounterVerify), # 105
            ])
            self.pay_blinds(skipSerials = { 105 : 105 })
            self.confirm_blind(self.game.turn_history, [(100, small, 0), (101, big, 0)])

    # --------------------------------------------------------------------------
    def test12_fourPlayers_fourSitsOutForALongTime(self):
        """test12_fourPlayers_fourSitsOutForALongTime
        Tests four players where the fourth sits out for a long time and the counter runs.
        """
        big = self.amounts['big']
        small = self.amounts['small']

        for (serial, seat) in ((100, 0), (101, 1), (102, 2), (103, 3)):
            self.make_new_bot(serial, seat)

        turn = 0
        missedCounterVerify = 0
        missedSoFar = None
        self.assertEquals(self.game.sitOut(103), True)
        while missedCounterVerify < 4:
            for serial in [100, 101, 102, 103]:
                amount = self.game.maxBuyIn() - self.game.serial2player[serial].money
                self.game.rebuy(serial, amount)

            turn += 1
            self.game.beginTurn(turn)
            self.check_button(100)
            self.assertEquals(self.game.isSitOut(103), True)
            self.check_blinds([
                (False, None, False, 0), # 100
                ('small', None, False, 0), # 101
                ('big', None, False, 0), # 102
                (False, missedSoFar, False, missedCounterVerify), # 103
            ])
            self.pay_blinds(skipSerials = { 103 : 103 })
            self.confirm_blind(self.game.turn_history, [(101, small, 0), (102, big, 0)])
            self.assertEquals(self.game.serial2player[103].getMissedRoundCount(),
               missedCounterVerify)

            turn += 1
            missedCounterVerify += 1
            missedSoFar = 'big'
            self.assertEquals(self.game.isSitOut(103), True)
            self.game.beginTurn(turn)
            self.check_button(101)
            self.check_blinds([
                ('big', None, False, 0), # 100
                (False, None, False, 0), # 101
                ('small', None, False, 0), # 102
                (False, missedSoFar, False, missedCounterVerify), # 103
            ])

            self.pay_blinds(skipSerials = { 103 : 103 })
            self.confirm_blind(self.game.turn_history, [(102, small, 0), (100, big, 0)])
            self.assertEquals(self.game.serial2player[103].getMissedRoundCount(),
               missedCounterVerify)

            turn += 1
            self.assertEquals(self.game.isSitOut(103), True)
            self.game.beginTurn(turn)
            self.check_button(102)
            self.check_blinds([
                ('small', None, False, 0), # 100
                ('big', None, False, 0), # 101
                (False, None, False, 0), # 102
                (False, missedSoFar, False, missedCounterVerify), # 103
            ])

            self.pay_blinds(skipSerials = { 103 : 103 })
            self.confirm_blind(self.game.turn_history, [(100, small, 0), (101, big, 0)])
            self.assertEquals(self.game.serial2player[103].getMissedRoundCount(),
               missedCounterVerify)


    def helperForTest13and14(self, big, small):
        """This just sets up a situation that can have two outcomes; after
        sitting out for a very long time, the 102 player can sit in while
        the blinds are being posted, or before they are."""

        for (serial, seat) in ((100, 0), (101, 1), (102, 2), (103, 3), (104, 4), (105, 5), (106, 6)):
            self.make_new_bot(serial, seat)

        turn = 0
        missedCounterVerify = 0
        missedSoFar = None
        turn += 1
        self.game.beginTurn(turn)
        self.check_button(100)
        self.check_blinds([
            (False, None, False, 0), # 100
            ('small', None, False, 0), # 101
            ('big', None, False, 0), # 102
            (False, None, False, 0), # 103
            (False, None, False, 0), # 104
            (False, missedSoFar, False, missedCounterVerify), # 105
            (False, None, False, 0), # 106
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(101, small, 0), (102, big, 0)])

        turn += 1
        self.game.beginTurn(turn)
        self.check_button(101)
        self.check_blinds([
            (False, None, False, 0), # 100
            (False, None, False, 0), # 101
            ('small', None, False, 0), # 102
            ('big', None, False, 0), # 103
            (False, None, False, 0), # 104
            (False, None, False, 0), # 105
            (False, None, False, 0), # 106
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(102, small, 0), (103, big, 0)])


        turn += 1
        self.game.beginTurn(turn)
        self.check_button(102)
        self.check_blinds([
            (False, None, False, 0), # 100
            (False, None, False, 0), # 101
            (False, None, False, 0), # 102
            ('small', None, False, 0), # 103
            ('big', None, False, 0), # 104
            (False, None, False, 0), # 105
            (False, None, False, 0), # 106
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(103, small, 0), (104, big, 0)])

        self.assertEquals(self.game.sitOut(102), True)
        missedCounterVerify = 0
        missedSoFar = None
        
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), 0)
        while missedCounterVerify < 4:
            for serial in [100, 101, 102, 103, 104, 105, 106]:
                amount = self.game.maxBuyIn() - self.game.serial2player[serial].money
                self.game.rebuy(serial, amount)

            turn += 1
            self.game.beginTurn(turn)
            self.check_button(103)
            self.assertEquals(self.game.isSitOut(102), True)
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
            self.check_blinds([
                (False, None, False, 0), # 100
                (False, None, False, 0), # 101
                (False, missedSoFar, False, missedCounterVerify), # 102
                (False, None, False, 0), # 103
                ('small', None, False, 0), # 104
                ('big', None, False, 0), # 105
                (False, None, False, 0), # 106
            ])
            self.pay_blinds(skipSerials = { 102 : 102 })
            self.confirm_blind(self.game.turn_history, [(104, small, 0), (105, big, 0)])
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)

            turn += 1
            self.assertEquals(self.game.isSitOut(102), True)
            self.game.beginTurn(turn)
            self.check_button(104)
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
            self.check_blinds([
                (False, None, False, 0), # 100
                (False, None, False, 0), # 101
                (False, missedSoFar, False, missedCounterVerify), # 102
                (False, None, False, 0), # 103
                (False, None, False, 0), # 104
                ('small', None, False, 0), # 105
                ('big', None, False, 0), # 106
            ])

            self.pay_blinds(skipSerials = { 102 : 102 })
            self.confirm_blind(self.game.turn_history, [(105, small, 0), (106, big, 0)])
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)

            turn += 1
            self.assertEquals(self.game.isSitOut(102), True)
            self.game.beginTurn(turn)
            self.check_button(105)
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
            self.check_blinds([
                ('big', None, False, 0), # 100
                (False, None, False, 0), # 101
                (False, missedSoFar, False, missedCounterVerify), # 102
                (False, None, False, 0), # 103
                (False, None, False, 0), # 104
                (False, None, False, 0), # 105
                ('small', None, False, 0), # 106
            ])
            self.pay_blinds(skipSerials = { 102 : 102 })
            self.confirm_blind(self.game.turn_history, [(106, small, 0), (100, big, 0)])
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)

            turn += 1
            self.assertEquals(self.game.isSitOut(102), True)
            self.game.beginTurn(turn)
            self.check_button(106)
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
            self.check_blinds([
                ('small', None, False, 0), # 100
                ('big', None, False, 0), # 101
                (False, missedSoFar, False, missedCounterVerify), # 102
                (False, None, False, 0), # 103
                (False, None, False, 0), # 104
                (False, None, False, 0), # 105
                (False, None, False, 0), # 106
            ]) 
            self.pay_blinds(skipSerials = { 102 : 102 })
            self.confirm_blind(self.game.turn_history, [(100, small, 0), (101, big, 0)])
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)

            turn += 1
            missedCounterVerify += 1
            missedSoFar = 'big'
            self.game.beginTurn(turn)
            self.check_button(100)
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
            self.assertEquals(self.game.isSitOut(102), True)
            self.check_blinds([
                (False, None, False, 0), # 100
                ('small', None, False, 0), # 101
                (False, missedSoFar, False, missedCounterVerify), # 102
                ('big', None, False, 0), # 103
                (False, None, False, 0), # 104
                (False, None, False, 0), # 105
                (False, None, False, 0), # 106
            ])
            self.pay_blinds(skipSerials = { 102 : 102 })
            self.confirm_blind(self.game.turn_history, [(101, small, 0), (103, big, 0)])
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)


            turn += 1
            self.game.beginTurn(turn)
            self.check_button(101)
            self.assertEquals(self.game.isSitOut(102), True)
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
            self.check_blinds([
                (False, None, False, 0), # 100
                (False, None, False, 0), # 101
                (False, missedSoFar, False, missedCounterVerify), # 102
                ('small', None, False, 0), # 103
                ('big', None, False, 0), # 104
                (False, None, False, 0), # 105
                (False, None, False, 0), # 106
            ])
            self.pay_blinds(skipSerials = { 102 : 102 })
            self.confirm_blind(self.game.turn_history, [(103, small, 0), (104, big, 0)])
            self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
        return(turn, missedSoFar, missedCounterVerify)
    # --------------------------------------------------------------------------
    def test13_sevenPlayers_fiveSitsOutForALongTimeAfterInitialPayment_duringBlinds(self):
        """test13_sevenPlayers_fiveSitsOutForALongTimeAfterInitialPayment_duringBlinds
        Tests seven players where the fifth sits out for a long time and the counter runs.
        """
        big = self.amounts['big']
        small = self.amounts['small']

        (turn, missedSoFar, missedCounterVerify) = self.helperForTest13and14(big, small)
        # end of while, now let's try to sit back in!  In this test, we
        # sit back in during the blind posting period.
        turn += 1
        self.game.beginTurn(turn)
        self.check_button(103)
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
        self.assertEquals(self.game.sit(102), True)
        self.check_blinds([(False, None, False, 0), # 100
            (False, None, False, 0), # 101
            (False, 'big', 'first_round', missedCounterVerify), # 102
            (False, None, False, 0), # 103
            ('small', None, False, 0), # 104
            ('big', None, False, 0), # 105
            (False, None, False, 0), # 106
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(104, small, 0), (105, big, 0)])
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
        turn += 1
        self.game.beginTurn(turn)
        self.check_button(104)
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
        self.assertEquals(self.game.isSit(102), True)
        self.check_blinds([(False, None, False, 0), # 100
            (False, None, False, 0), # 101
            ('big_and_dead', 'big', False, missedCounterVerify), # 102
            (False, None, False, 0), # 103
            (False, None, False, 0), # 104
            ('small', None, False, 0), # 105
            ('big', None, False, 0), # 106
        ])
        self.pay_blinds()
        # We find 102 has posted big and small, since he can now play again.
        self.confirm_blind(self.game.turn_history, [(105, small, 0), (106, big, 0), (102, big, small)])
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), 0)
        turn += 1
        self.game.beginTurn(turn)
        self.check_button(105)
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), 0)
        self.assertEquals(self.game.isSit(102), True)
        self.check_blinds([
            ('big', None, False, 0), # 100
            (False, None, False, 0), # 101
            (False, None, False, 0), # 102
            (False, None, False, 0), # 103
            (False, None, False, 0), # 104
            (False, None, False, 0), # 105
            ('small', None, False, 0), # 106
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(106, small, 0), (100, big, 0)])
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), 0)
    # --------------------------------------------------------------------------
    def test14_sevenPlayers_fiveSitsOutForALongTimeAfterInitialPayment_beforeBlinds(self):
        """test14_sevenPlayers_fiveSitsOutForALongTimeAfterInitialPayment_beforeBlinds
        Tests seven players where the fifth sits out for a long time and
        the counter runs.  Then, he sits abck but while they are posting
        blinds.
        """
        big = self.amounts['big']
        small = self.amounts['small']

        (turn, missedSoFar, missedCounterVerify) = self.helperForTest13and14(big, small)
        # end of while, now let's try to sit back in!  In this test, we
        # sit back in before the blinds are posted
        self.assertEquals(self.game.sit(102), True)
        turn += 1
        self.game.beginTurn(turn)
        self.check_button(103)
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), missedCounterVerify)
        self.assertEquals(self.game.isSit(102), True)
        self.check_blinds([(False, None, False, 0), # 100
            (False, None, False, 0), # 101
            ('big_and_dead', 'big', False, missedCounterVerify), # 102
            (False, None, False, 0), # 103
            ('small', None, False, 0), # 104
            ('big', None, False, 0), # 105
            (False, None, False, 0), # 106
        ])
        self.pay_blinds()
        # We find 102 has posted big and small, since he can now play again.
        self.confirm_blind(self.game.turn_history, [(104, small, 0), (105, big, 0), (102, big, small)])
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), 0)
        turn += 1
        self.game.beginTurn(turn)
        self.check_button(104)
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), 0)
        self.assertEquals(self.game.isSit(102), True)
        self.check_blinds([
            (False, None, False, 0), # 100
            (False, None, False, 0), # 101
            (False, None, False, 0), # 102
            (False, None, False, 0), # 103
            (False, None, False, 0), # 104
            ('small', None, False, 0), # 105
            ('big', None, False, 0), # 106
        ])
        self.pay_blinds()
        self.confirm_blind(self.game.turn_history, [(105, small, 0), (106, big, 0)])
        self.assertEquals(self.game.serial2player[102].getMissedRoundCount(), 0)

def GetTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBlinds))
    return suite

def run():
    return unittest.TextTestRunner().run(GetTestSuite())
    
if __name__ == '__main__':
    if run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

# Interpreted by emacs
# Local Variables:
# compile-command: "( cd .. ; ./config.status tests/blinds.py ) ; ( cd ../tests ; make TESTS='blinds.py' check )"
# End:
