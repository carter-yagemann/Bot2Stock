from agent.TradingAgent import TradingAgent
from message.Message import Message
from util.util import log_print

from math import sqrt
import numpy as np
import pandas as pd
import sys

np.set_printoptions(threshold=np.inf)


class SpoofingAgent(TradingAgent):

    def __init__(self, id, name, type, spoof_time=None, botmaster=None, spoof_shares=10000, lambda_a=0.005, symbol='IBM', starting_cash=100000,
                 log_orders=False, random_state=None):

        # Base class init.
        super().__init__(id, name, type, random_state, starting_cash, log_orders)

        # Store additional parameters
        self.symbol = symbol              # symbol to spoof
        self.spoof_time = spoof_time      # time spoofing begins at
        self.spoof_shares = spoof_shares  # number of shares to spoof
        self.lambda_a = lambda_a          # mean arrival rate
        self.botmaster = botmaster        # if spoof_time is None, poll this agent instead

        assert not (self.botmaster is None and self.spoof_time is None)

        self.state = 'AWAITING_WAKEUP'
        self.master_cmd = 'NONE'

    def getWakeFrequency(self):
        return pd.Timedelta(self.random_state.randint(low=0, high=100), unit='ns')

    def haveSpread(self):
        return self.symbol in self.known_bids or self.symbol in self.known_asks

    def wakeup(self, currentTime):
        # Parent class handles discovery of exchange times and market_open wakeup call.
        super().wakeup(currentTime)

        if not self.mkt_open or not self.mkt_close:
            # TradingAgent handles discovery of exchange times.
            return

        # If the market is closed for the day, we're done
        if self.mkt_closed:
            self.state = 'INACTIVE'
            return

        # If it's not spoofing time yet, wait for it
        if not self.spoof_time is None and currentTime < self.spoof_time:
            self.state = 'INACTIVE'
            # Spoofing agents enter the market with a Poisson distribution
            delta_time = self.random_state.exponential(scale=1.0 / self.lambda_a)
            self.setWakeup(self.spoof_time + pd.Timedelta('{}ns'.format(int(round(delta_time)))))
            return
        elif self.spoof_time is None and self.master_cmd != 'ATTACK':
            if self.state != "AWAITING_CMD":
                self.sendMessage(self.botmaster, Message({'msg': "QUERY_ATTACK_TIME", "sender": self.id}))
                self.state = "AWAITING_CMD"
            self.cancelOrders()  # double checking that we aren't spoofing right now
            self.setWakeup(currentTime + self.getWakeFrequency())
            return

        # It's spoofing time!

        # If we don't already have the spread, we need it
        # Note, getting the spread also gives us the last trade for free
        if not self.haveSpread():
            if self.state != 'AWAITING_SPREAD':
                self.getCurrentSpread(self.symbol)
                self.state = 'AWAITING_SPREAD'
            self.setWakeup(currentTime + self.getWakeFrequency())
            return
        else:
            self.state = 'ACTIVE'

        # We have the spread now, we can place a spoof order.
        self.placeOrder()

        # Clear our spread data, which will send us back into the awaiting
        # spread state.
        if self.symbol in self.known_bids:
            del self.known_bids[self.symbol]
        if self.symbol in self.known_asks:
            del self.known_asks[self.symbol]
        self.setWakeup(currentTime + self.getWakeFrequency())

    def placeOrder(self):
        # Called when it is time for the agent to spoof.
        bids = self.known_bids[self.symbol]

        # Our strategy is based on Wellman's "Spoofing the Limit Order Book" paper.
        # Namely, we want to maintain a large bid that's one tick behind the best
        # bid, canceling existing bids as necessary to do so.

        # First, if there are no bids currently in the spread, we cannot spoof.
        if not bids:
            log_print("No bids, cannot spoof")
            return

        best_bid = bids[0][0]

        # If the best bid is somehow a penny or less, we have no room to spoof.
        if best_bid <= 1:
            log_print("Current best bid is under a penny, no room to spoof")
            return

        # Next, check if we already have a bid in the book.
        num_outstanding_orders = len(self.orders)
        if num_outstanding_orders > 0:
            # We have bids in the book, cancel any that aren't one tick behind
            # the best bid.
            num_canceled = 0
            for id, order in self.orders.items():
                if order.limit_price != best_bid - 1:
                    self.cancelOrder(order)
                    num_canceled += 1

            assert num_canceled <= num_outstanding_orders

        # If we had outstanding orders, but we didn't cancel all of them, then
        # the remaining ones are already one tick behind the best bid, so no
        # further orders need to be placed.
        if num_outstanding_orders > 0 and num_canceled < num_outstanding_orders:
            return

        # We either had no outstanding orders, or they've all been canceled.
        # Place a new bid one tick behind the current best.
        log_print("BID {} {}@{}", self.symbol, self.spoof_shares, best_bid - 1)
        self.placeLimitOrder(self.symbol, self.spoof_shares, True, best_bid - 1)

    def cancelOrders(self):
        if not self.orders: return False

        for id, order in self.orders.items():
            self.cancelOrder(order)

        return True

    def receiveMessage(self, currentTime, msg):
        # Allow parent class to handle state + message combinations it understands.
        super().receiveMessage(currentTime, msg)

        if msg.body['msg'] == "ORDER_EXECUTED":
            # Some of our orders executed, cancel everything NOW!
            log_print("An order executed by accident, canceling everything")
            self.cancelOrders()

        if msg.body['msg'] == "QUERY_ATTACK_TIME":
            if msg.body['attack']:
                self.master_cmd = 'ATTACK'
            else:
                self.master_cmd = 'WAIT'
            self.state = 'INACTIVE'
