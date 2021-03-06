import csv
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random

from sklearn import metrics, preprocessing
from talib.abstract import *

class ContainerException(Exception):
    pass

class Container():
    def __init__(self):
        pass

    @property
    def num_assets(self):
        return self.train_data.shape[0]

    @property
    def train_length(self):
        return self.train_data.shape[1]

    @property
    def test_length(self):
        return self.test_data.shape[1]

    @property
    def num_asset_features(self):
        return self.train_data.shape[2]

    @property
    def num_flattened_features(self):
        return self.num_assets * self.num_asset_features + self.num_assets

    def get_data(self, train=True):
        if train:
            return self.train_data
        else:
            return self.test_data

    def get_prices(self, train=True):
        if train:
            return self.train_close 
        else:
            return self.test_close 

    def initial_time(self, train=True, episode_length=None):
        if train:
            init_time = np.random.randint(low=0,
                                          high=self.train_length - episode_length)
        else:
            init_time = 0
        end_time = init_time + episode_length
        return init_time, end_time 

    def get_asset_features(self, train, time):
        data = self.get_data(train=train)
        return data[:, time, :]

    def get_price(self, train, time):
        prices = self.get_prices(train=train)
        return prices[0, time, 0]

    def plot_prices(self, train):
        prices = self.get_prices(train=train)
        for ind in range(prices.shape[0]):
            plt.plot(prices[ind, :, 0])
        plt.show()

class TestContainer(Container):
    def __init__(self, shape='sine', num_assets=3, num_samples=200, train_split=0.7):
        super().__init__()

        if shape is 'sine':
            closes = [np.sin(2*np.pi*np.linspace(start=0, # [num_assets, num_samples]
                                                 stop=8,
                                                 num=num_samples)+(5*np.pi/8)*asset) for asset in range(num_assets)]
            closes = np.array(closes)
            closes = closes+100
        data = self.featurize(closes)
        closes = data[:, :, 0:1]
        data = data[:, :, 1:]

        split_level = int(num_samples * train_split)
        self.train_data = data[:, 0:split_level, :]
        self.train_close = closes[:, 0:split_level, :]                                                                                                                        
        self.test_data = data[:, split_level:, :]
        self.test_close = closes[:, split_level:, :]

        print("SHAPES:", self.train_data.shape, self.train_close.shape, self.test_data.shape, self.test_close.shape)

    def featurize(self, closes):
        all_features = []
        for close in closes:
            diff = np.diff(close)
            diff = np.insert(diff, 0, 0)
            features = np.column_stack((close, diff)) # [num_samples, 2]
            all_features.append(features)
        return np.array(all_features) # [num_assets, num_samples, 2]

class BitcoinTestContainer(Container):
    def __init__(self, csv_file_name=None, train_split=0.7):
        assert csv_file_name is not None
        file = open(csv_file_name)
        reader = csv.DictReader(file)

        self.data = {
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': []
        }
        times = []

        for line in reader:
            for key in self.data:
                self.data[key].append(float(line[key]))
            times.append(int(line['time']))

        self.df = pd.DataFrame(data=self.data,
                               index=times)
        split_level = int(len(times) * train_split)
        self.train_df = self.df.iloc[:split_level, :]
        self.test_df = self.df.iloc[split_level:, :]
        self.process(train_df=self.train_df,
                     test_df=self.test_df)

    def featurize(self, df):
        close = df['close'].values
        diff = np.diff(close)
        diff = np.insert(diff, 0, 0)
        sma15 = SMA(df, timeperiod=15)
        sma60 = SMA(df, timeperiod=60)
        rsi = RSI(df, timeperiod=14)
        atr = ATR(df, timeperiod=14)

        data = np.column_stack((diff, sma15, close-sma15, sma15-sma60, rsi, atr))
        data = np.nan_to_num(data) 
        return np.array(data), np.expand_dims(close, 1) # [num_periods, num_features], [num_periods, 1]

    def process(self, train_df, test_df):
        self.pre_train_data, self.pre_train_close = self.featurize(train_df)
        self.pre_test_data, self.pre_test_close = self.featurize(test_df)

        self.feature_scaler = preprocessing.MinMaxScaler()
        self.train_data = self.feature_scaler.fit_transform(self.pre_train_data) # [num_periods, features]
        self.test_data = self.feature_scaler.transform(self.pre_test_data)

        self.pre_train_data, self.pre_test_data, self.train_data, self.test_data = \
            [np.array([arr]) for arr in [self.pre_train_data, self.pre_test_data, self.train_data, self.test_data]]
        # [1, num_periods, num_features]

        self.price_scaler = preprocessing.MinMaxScaler()
        self.train_close = self.feature_scaler.fit_transform(self.pre_train_close)
        self.test_close = self.feature_scaler.transform(self.pre_test_close)

        self.pre_train_close, self.pre_test_close, self.train_close, self.test_close = \
            [np.array([arr]) for arr in [self.pre_train_close, self.pre_test_close, self.train_close, self.test_close]]

        self.train_close = self.pre_train_close
        self.test_close = self.pre_test_close
        # [1, num_periods, 1]


