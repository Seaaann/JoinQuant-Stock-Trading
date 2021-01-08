def Daily_PnL(
    date,
    stock_index,
    start_date,
    end_date,
    frequency,
    threshold=0.001,
    transaction_fee=0.0003,
    tax=0.001,
):

    # get the data
    stock = stock_list[stock_index]

    all_stock_price = get_price(
        stock, start_date=start_date, end_date=end_date, frequency=frequency
    )
    ret = all_stock_price.close.pct_change()
    all_stock_price["ret"] = ret
    all_stock_price.dropna(inplace=True)

    date_str = all_stock_price.index.strftime("%Y-%m-%d")
    all_stock_price["date"] = date_str

    date_list = date_str.unique()

    all_stock_price["threshold"] = threshold
    all_stock_price["signal"] = 0

    all_stock_price["able"] = 1
    for i in range(0, len(all_stock_price)):
        if all_stock_price["volume"][i] <= 0.0:
            all_stock_price["able"][i] = 0

    for i in range(0, len(all_stock_price)):
        if (all_stock_price["ret"][i] > all_stock_price["threshold"][i]) & (
            all_stock_price["able"][i] != 0
        ):
            all_stock_price["signal"][i] = 1
        elif (all_stock_price["ret"][i] <= -all_stock_price["threshold"][i]) & (
            all_stock_price["able"][i] != 0
        ):
            all_stock_price["signal"][i] = -1

    all_stock_price["next.ask"] = all_stock_price["open"].shift(-1) + 0.01
    all_stock_price["next.bid"] = all_stock_price["open"].shift(-1) - 0.01

    # set the position for each day
    print("Looking at date: {}".format(date))
    stock_price = all_stock_price[all_stock_price["date"] == date]

    print(
        "Number of positive: {}, Number of negative: {}".format(
            sum(stock_price["ret"] > 0), sum(stock_price["ret"] < 0)
        )
    )
    n_bar = len(stock_price)

    position = stock_price.signal
    position[0] = 0
    position[n_bar - 1] = 0
    position[n_bar - 2] = 0
    change_of_position = position - position.shift(1)
    change_of_position[0] = 0
    change_base = np.zeros(n_bar)
    change_buy = np.array(change_of_position > 0)
    change_sell = np.array(change_of_position < 0)

    change_base[change_buy] = stock_price["next.ask"][change_buy] * (
        1 + transaction_fee
    )
    change_base[change_sell] = stock_price["next.bid"][change_sell] * (
        1 + transaction_fee + tax
    )

    stock_price.dropna(inplace=True)

    final_pnl = -sum(change_base * change_of_position)
    turnover = sum(change_base * abs(change_of_position))
    num = sum((position != 0) & (change_of_position != 0))
    hld_period = sum(position != 0)

    result = {
        "name": stock,
        "date": date,
        "final.pnl": final_pnl,
        "turnover": turnover,
        "num": num,
        "hld.period": hld_period,
    }
    print(result)

    return result


def PnL_Result_Plot(
    date_list,
    stock_index,
    start_date,
    end_date,
    frequency,
    threshold=0.001,
    transaction_fee=0.0003,
    tax=0.001,
    spread=1,
):

    result_df = pd.DataFrame()
    for date in date_list:
        result = Daily_PnL(
            date,
            0,
            start_date,
            end_date,
            "1m",
            threshold=0.001,
            transaction_fee=0.0003,
            tax=0.001,
        )
        df = pd.DataFrame.from_dict(result, orient="index").T.set_index("name")
        result_df = pd.concat([result_df, df])

    statistics = np.array(np.rec.fromrecords(result_df.values))
    np_names = result_df.dtypes.index.tolist()
    statistics.dtype.names = tuple([name for name in np_names])
    statistics = pd.DataFrame(statistics)

    pnl = statistics["final.pnl"].cumsum()

    plt.figure(1, figsize=(20, 8))
    plt.title("PnL for {}".format(result_df.index.values[0]))
    plt.xlabel("Date")
    plt.ylabel("PnL")
    plt.plot(result_df["date"], pnl)

    n_days = len(statistics)
    num = statistics["num"].mean()

    if statistics["final.pnl"].std() == 0:
        sharpe = 0
    else:
        sharpe = (
            statistics["final.pnl"].mean()
            / statistics["final.pnl"].std()
            * math.sqrt(250)
        )

    drawdown = max(pnl.cummax() - pnl) / pnl.iloc[-1]
    mar = 1 / drawdown
    win_ratio = sum(statistics["final.pnl"] > 0) / n_days
    print("Win Ratio: ", win_ratio)

    avg_pnl = sum(statistics["final.pnl"]) / sum(statistics["num"]) / spread
    print("Average PnL: ", avg_pnl)

    hld_period = sum(statistics["hld.period"]) / sum(statistics["num"])
    return OrderedDict(
        [
            ("sharpe", sharpe),
            ("drawdown", drawdown),
            ("mar", mar),
            ("win.ratio", win_ratio),
            ("num", num),
            ("avg.pnl", avg_pnl),
            ("hld.period", hld_period),
        ]
    )
