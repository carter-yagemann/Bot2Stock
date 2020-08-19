from agent.TradingAgent import TradingAgent
from message.Message import Message
from util.util import log_print

from math import sqrt
import numpy as np
import pandas as pd
import sys

np.set_printoptions(threshold=np.inf)


class BotmasterAgent(TradingAgent):

    def __init__(self, id, name, type, attack_time, lambda_a=0.005, symbol='IBM', starting_cash=100000,
                 log_orders=False, random_state=None):

        # Base class init.
        super().__init__(id, name, type, random_state, starting_cash, log_orders)

        # Store additional parameters
        self.symbol = symbol            # symbol to spoof
        self.attack_time = attack_time  # time spoofing begins at
        self.lambda_a = lambda_a        # mean arrival rate

        self.state = 'AWAITING_WAKEUP'

    def getWakeFrequency(self):
        return pd.Timedelta(self.random_state.randint(low=0, high=100), unit='ns')

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

        # If it's not attack time yet, wait for it
        if currentTime < self.attack_time:
            self.state = 'INACTIVE'
            # Enter the market with a Poisson distribution
            delta_time = self.random_state.exponential(scale=1.0 / self.lambda_a)
            self.setWakeup(self.attack_time + pd.Timedelta('{}ns'.format(int(round(delta_time)))))
            return

        # It's time to begin the attack

        # First, we need to go fully long (no margin) on the target stock, which requires
        # knowing the last trade price.
        if not self.symbol in self.last_trade:
            self.getLastTrade(self.symbol)
            self.state = 'AWAITING_LAST_TRADE'
            self.setWakeup(currentTime + self.getWakeFrequency())
            return

        # Use all our cash to buy shares in the target stock
        if not self.symbol in self.holdings:
            quantity = int(round(self.holdings['CASH'] / self.last_trade[self.symbol]))
            assert quantity >= 1
            self.placeLimitOrder(self.symbol, quantity, True, self.last_trade[self.symbol] * 100)
            self.state = 'ATTACKING'
            # Now that we have shares, we don't need to wake up again until it's time to dump
            self.setWakeup(self.mkt_close - pd.Timedelta('20ms'))
            return

        # Time to dump
        self.placeLimitOrder(self.symbol, self.holdings[self.symbol], False, 1)
        self.state = 'INACTIVE'

    def receiveMessage(self, currentTime, msg):
        # Allow parent class to handle state + message combinations it understands.
        super().receiveMessage(currentTime, msg)

        if msg.body['msg'] == "QUERY_ATTACK_TIME":
            self.sendMessage(msg.body['sender'], Message({"msg": "QUERY_ATTACK_TIME", "sender": self.id,
                                                          "attack": self.state == 'ATTACKING'}))
