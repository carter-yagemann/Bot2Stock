#!/usr/bin/env python

import pandas as pd
import sys
import os

BETWEEN_START = pd.to_datetime('09:30').time()
BETWEEN_END   = pd.to_datetime('16:30').time()

def read_historical_trades(file, symbol='IBM'):
    df = pd.read_pickle(file, compression='bz2')
    df = df.loc[symbol]
    df = df.between_time('9:30', '16:00')
    return df

def read_simulated_trades(file, symbol='IBM'):
    # TODO - Exchange agents do not support multiple symbols yet.
    df = pd.read_pickle(file, compression='bz2')
    df = df[df['EventType'] == 'LAST_TRADE']

    if len(df) <= 0:
        print("There appear to be no simulated trades", file=sys.stderr)
        sys.exit(2)

    df['PRICE'] = [y for x,y in df['Event'].str.split(',')]
    df['SIZE'] = [x for x,y in df['Event'].str.split(',')]

    df['PRICE'] = df['PRICE'].str.replace('$','').astype('float64') / 100.0
    df['SIZE'] = df['SIZE'].astype('float64')

    return df

def resample_weighted_mean(df, value, weight, freq):
    return (df[value] * df[weight]).resample(freq).sum() / df[weight].resample(freq).sum()

def resample_weighted_std(df, value, weight, freq):
    return (df[value] * df[weight]).resample(freq).std() / df[weight].resample(freq).sum()

def main():
    if len(sys.argv) != 4:
        print('Usage:', sys.argv[0], '<frequency> <Exchange Agent DataFrame> <Trades Dataframe>')
        print('    Example: python b2s_stats.py 1T logs/ExchangeAgent0.bz2 data/trades/trades_2014/ct_20140128.bgz')
        sys.exit(1)

    FREQUENCY = sys.argv[1]

    # read in dataframes
    try:
        print("[+] Loading", sys.argv[2], file=sys.stderr)
        exchange_df = read_simulated_trades(sys.argv[2])
    except:
        print('Failed to read:', sys.argv[2], file=sys.stderr)
        sys.exit(2)
    try:
        print("[+] Loading", sys.argv[3], file=sys.stderr)
        trades_df = read_historical_trades(sys.argv[3])
    except:
        print('Failed to read:', sys.argv[3], file=sys.stderr)
        sys.exit(2)

    # reduce dataframes to same time span
    exchange_df = exchange_df.between_time(BETWEEN_START, BETWEEN_END)
    trades_df = trades_df.between_time(BETWEEN_START, BETWEEN_END)

    if 'PRICE' in trades_df.columns:
        # historical data is sequence of completed orders (price, size)
        merged_df = pd.DataFrame({'SimPriceMean': resample_weighted_mean(exchange_df, 'PRICE', 'SIZE', FREQUENCY),
                                  'SimPriceStd': resample_weighted_std(exchange_df, 'PRICE', 'SIZE', FREQUENCY),
                                  'HistPriceMean': resample_weighted_mean(trades_df, 'PRICE', 'SIZE', FREQUENCY),
                                  'HistPriceStd': resample_weighted_std(trades_df, 'PRICE', 'SIZE', FREQUENCY)
                })
    else:
        # historical data is aggregated (open, high, low, close, volumn)
        first = lambda a: a[0] if len(a) > 0 else None
        last = lambda a: a[-1] if len(a) > 0 else None
        freq = trades_df.index.freq
        merged_df = pd.DataFrame({'SimOpen': exchange_df['PRICE'].resample(freq).apply(first),
                                  'SimHigh': exchange_df['PRICE'].resample(freq).max(),
                                  'SimLow': exchange_df['PRICE'].resample(freq).min(),
                                  'SimClose': exchange_df['PRICE'].resample(freq).apply(last),
                                  'SimVolume': exchange_df['SIZE'].resample(freq).sum(),
                                  'HistOpen': trades_df['open'],
                                  'HistHigh': trades_df['high'],
                                  'HistLow': trades_df['low'],
                                  'HistClose': trades_df['close'],
                                  'HistVolume': trades_df['volume'],
                })

    # fill in NaNs
    merged_df = merged_df.fillna(method='ffill')

    # print dataframe in CSV format
    merged_df.to_csv(sys.stdout)

if __name__ == '__main__':
    main()
