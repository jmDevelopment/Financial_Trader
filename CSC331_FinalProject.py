from nlib import *
import random
import matplotlib.pyplot as plt
import matplotlib.patches as patch

symbol = "AAPL"
# Stock symbols to be explored
symbol_list = ["AAPL", "MSFT", "YHOO", "FB", "IBM", "GOOG", "TSLA",  "BBY", "TGT", "WMT"]
# Number of days
L = 7

class Trader(object):
    
    def __init__(self, amount = 10000.0):
        self.bank_balance = amount
        self.number_of_shares = 0          

    def get_data(self, symbol = "AAPL"):
        # PersistentDictionary Object to hold all historical prices
        # *** MIGHT NEED TO CHANGE LATER ***
        storage = PersistentDictionary("stockDB.db")
        # If symbol is in storage
        #       Historical is from storage given the symbol.
        #       Else
        #           Get symbol from Yahoo
        #           Put it in the storage

        if symbol in storage:
            h = storage[symbol]
        else:
            h = YStock(symbol).historical()
            storage[symbol] = h
        self.h = h[-200:]

    def get_time_window(self, t = 0, L = 7):
        # Time window of past 7 days.
        return self.h[t : t + L]

    def print_time_window(self, t = 0, L = 7):
        time_window = self.get_time_window(t, L)
        # For each day
        #   print date & the adjusted close for that date
        for day in time_window:
            print day["date"].isoformat(), day["adjusted_close"]

    def model(self, t = 0, L = 7):
        w = self.get_time_window(t, L)
        data = []
        for t, day in enumerate(w):
            data.append((t, day["adjusted_close"], 0.1))
        c, chi2, f = fit_least_squares(data, QUADRATIC)

        return f(L)

    def sma(self):
        "Purpose: Calcute the simpe moving average for a period of 200 days."
        "It returns the list of averages."
        #Get the full data set
        time_window = self.get_time_window(0, 200)
        #Locally store the values within data
        data = []

        for day in time_window:
            # Populate the data from time window
            data.append(day["adjusted_close"])
        average = [sum(data[i:i+5])/5 for i in range(len(data)-4)]
        self.average = average

        return self.average

    def plot_SMA(self, t = 0, L = 7, title = symbol):

        time_window = self.get_time_window(0, 200)
        average = self.sma()

        plt.plot(average)
        plt.title("Simple Moving Average - %s" % symbol)
        plt.ylabel("Adjusted_Price($)")
        plt.xlabel("Closing_Date")
        plt.show()
            
    def bollinger_bands(self, L = 7, multiplier = 2):
        "Purpose: using the simple moving average function, it calculates the top and bottom Bollinger Bands"
        "It returns three lists: bottom_band, middle_band, and top_band."

        L = 200
        bottom_band = []
        middle_band = []
        top_band = []
        
        simple_moving_average = self.sma()

        x = 0
        while x < len(simple_moving_average):
            currentSMA = simple_moving_average[x]
            currentSD = sd(simple_moving_average[0: x])

            # print "CSMA: ", currentSMA, "\t", "CSD: " , currentSD

            TB = currentSMA + (currentSD * multiplier)
            BB = currentSMA - (currentSD * multiplier)

            top_band.append(TB)
            bottom_band.append(BB)
            middle_band.append(currentSMA)
            x += 1
            
        return bottom_band, middle_band, top_band

    def plot_BB(self, title = symbol):
        "Purpose: Calculate the bollinger bands associated with a stock's simple moving average"
        "The simple moving average is also plotted on the chart."

        BB, MB, TB = self.bollinger_bands(200, 2)
        
        plt.plot(BB, "r")
        plt.plot(MB, "b")
        plt.plot(TB, "g")
        plt.title("Bollinger Band Chart - %s" % symbol)
        plt.ylabel("Adjusted_Price($)")
        plt.xlabel("Date")
        plt.show()
        
    def plot_VOL(self, title = symbol):
        "Calculate the ongoing volume and plot those points"
        "Also plot the average daily volume for each day."

        average_volume_data = []
        adjusted_closing_price_data = []
        onbalance_volume_data = []
        ongoing_volume = 0
        
        #Get the full window for average volume.
        time_window = self.get_time_window(0, 200)

        for day in time_window:
            average_volume_data.append(day["adjusted_vol"])
            adjusted_closing_price_data.append(day["adjusted_close"])
            
        i = 0
        while i < len(adjusted_closing_price_data) - 1:
            today_price = adjusted_closing_price_data[i + 1]
            yesterday_price = adjusted_closing_price_data[i]
            current_volume = average_volume_data[i]

            if today_price > yesterday_price:
                ongoing_volume += current_volume
            elif today_price < yesterday_price:
                ongoing_volume = - ongoing_volume
            else:
                ongoing_volume = ongoing_volume

            onbalance_volume_data.append(ongoing_volume)
            i += 1

        plt.plot(average_volume_data, "r")
        plt.plot(onbalance_volume_data, "g")
        plt.title("Average Volume Chart - %s" % symbol)
        plt.ylabel("Average Volume (in Millions)")
        plt.xlabel("Date")
        plt.show()

    def volume_strategy(self, t, L):
        "Purpose: calculate an ongoing total of average daily volume"
        "If the ongoing volume is negative than shares should be bought; opposite, if the ongoing volume is positive"
        "Net worth is returned.

        today_price = self.h[t]["adjusted_close"]
        yesterday_price = self.h[t - 1]["adjusted_close"]
        current_volume = self.h[t]["adjusted_vol"]
        ongoing_volume = 0
        

        if today_price > yesterday_price:
            ongoing_volume = +ongoing_volume
            ongoing_volume += current_volume
        elif today_price < yesterday_price:
            ongoing_volume -= current_volume
            ongoing_volume = -ongoing_volume
        else:
            ongoing_volume = ongoing_volume

        if ongoing_volume > 0:
            new_shares = int(self.bank_balance/today_price)
            self.number_of_shares += new_shares
            self.bank_balance -= new_shares * today_price
        elif ongoing_volume < 0:
            self.bank_balance += self.number_of_shares * today_price
            self.number_of_shares = 0
        net_worth = self.bank_balance + today_price * self.number_of_shares
        
        if False:
            print "%s\t$%.2f\t%i\t%.2f" % (
            self.h[t]["date"].isoformat(),
            self.bank_balance,
            self.number_of_shares,
            net_worth)
            
        return net_worth

    def SMA_strategy(self, t, L):
        "Purpose: calculate the simple moving average over 200 days and compare today's adjusted closing price against the day's moving average."
        "If the price is larger than current moving average, then sell the shares; opposite, if the today price is less than the current moving average."
        "Net worth is returned.

        moving_average = self.sma()
        today_price = self.h[t]['adjusted_close']

        current_MA = moving_average[t]

        if today_price > current_MA:
            self.bank_balance += self.number_of_shares * today_price
            self.number_of_shares = 0
        elif today_price < current_MA:
            new_shares = int(self.bank_balance/today_price)
            self.number_of_shares += new_shares
            self.bank_balance -= new_shares * today_price
            
        net_worth = self.bank_balance + today_price * self.number_of_shares
        
        if False:
            print "%s\t$%.2f\t%i\t%.2f" % (
            self.h[t]["date"].isoformat(),
            self.bank_balance,
            self.number_of_shares,
            net_worth)
        return net_worth
    
            
    def BB_strategy(self, t, L):
        "Purpose: to take the simple moving average calculate the top, middle, and bottom bands, and return the net worth"
        "a comparison is taken between the absolute values of the middle - top band and the middle - bottom bands"
        "This is used to determine whether to buy or sell the shares of the stock"
        

        BB, MB, TB = self.bollinger_bands()
        today_price = self.h[t]["adjusted_close"]
        
        today_BB = BB[t]
        today_MB = MB[t]
        today_TB = TB[t]

        comparison_MB_BB = abs(today_BB - today_MB)
        comparison_MB_TB = abs(today_TB - today_MB)

        if comparison_MB_BB < comparison_MB_TB:
                new_shares = int(self.bank_balance/today_price)
                self.number_of_shares += new_shares
                self.bank_balance -= new_shares * today_price
        elif comparison_MB_BB > comparison_MB_TB:
                self.bank_balance += self.number_of_shares * today_price
                self.number_of_shares = 0

        net_worth = self.bank_balance + today_price * self.number_of_shares

        # print "BB: ", today_BB, "\t", "MB: ", today_MB, "\t", "TB: ", today_TB
                
        if False:
            print "%s\t$%.2f\t%i\t%.2f" % (
                self.h[t]["date"].isoformat(),
                self.bank_balance,
                self.number_of_shares,
                net_worth)

        return net_worth
    
    def BB_simulate(self, L = 7):
        "Purpose to run the bollinger band strategy and return the most curren tnet worth"
        for t in range(L, len(self.h) - 4):
            net_worth = self.BB_strategy(t, L)
        return net_worth

    def SMA_simulate(self, L = 7):
        "Purpose: to run the simple moving average strategy and return the most current net worth"
        for t in range(L, len(self.h) - 4):
            net_worth = self.SMA_strategy(t, L)
        return net_worth

    def volume_simulate(self, L = 7):
        "Purpose to run the volume strategy and return the most current net worth"
        
        for t in range(L, len(self.h)):
            net_worth = self.volume_strategy(t,L)
        return net_worth

for symbol in symbol_list:
    trader = Trader(amount = 10000)
    trader.get_data(symbol)
    net_worth_BB_strategy = trader.BB_simulate()
    net_worth_SMA_strategy = trader.SMA_simulate()
    net_worth_VOL_strategy = trader.volume_simulate()
    print"NET_WORTH FROM BB (%s): " % symbol, net_worth_BB_strategy, "NET_WORTH FROM SMA (%s): " % symbol, net_worth_SMA_strategy, "NET_WORTH FROM VOL (%s)" % symbol, net_worth_VOL_strategy
    trader.plot_BB(title = symbol)
    trader.plot_SMA(title = symbol)
    trader.plot_VOL(title = symbol)










        
