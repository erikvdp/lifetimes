import numpy as np
import pandas as pd
from lifetimes.utils import coalesce, calculate_alive_path

__all__ = [
    'plot_period_transactions',
    'plot_calibration_purchases_vs_holdout_purchases',
    'plot_frequency_recency_matrix',
    'plot_expected_repeat_purchases',
    'plot_probability_alive_matrix',
    'plot_history_alive'
]


def plot_period_transactions(model, **kwargs):
    from matplotlib import pyplot as plt

    bins = kwargs.pop('bins', range(9))
    labels = kwargs.pop('label', ['Actual', 'Model'])

    n = model.data.shape[0]
    simulated_data = model.generate_new_data(size=n)

    ax = plt.hist(np.c_[model.data['frequency'].values, simulated_data['frequency'].values],
                  bins=bins, label=labels)
    plt.legend()
    plt.xticks(np.arange(len(bins))[:-1] + 0.5, bins[:-1])
    plt.title('Frequency of Repeat Transactions')
    plt.ylabel('Customers')
    plt.xlabel('Number of Calibration Period Transactions')
    return ax


def plot_calibration_purchases_vs_holdout_purchases(model, calibration_holdout_matrix, kind="frequency_cal", n=7, **kwargs):
    """
    This currently relies too much on the lifetimes.util calibration_and_holdout_data function.

    Parameters:
        model: a fitted lifetimes model
        calibration_holdout_matrix: dataframe from calibration_and_holdout_data function
        kind: x-axis :"frequency_cal". Purchases in calibration period,
                      "recency_cal". Age of customer at last purchase,
                      "T_cal". Age of customer at the end of calibration period,
                      "time_since_last_purchase". Time since user made last purchase
        n: number of ticks on the x axis

    """
    from matplotlib import pyplot as plt

    x_labels = {
        "frequency_cal": "Purchases in calibration period",
        "recency_cal": "Age of customer at last purchase",
        "T_cal": "Age of customer at the end of calibration period",
        "time_since_last_purchase": "Time since user made last purchase"
    }
    summary = calibration_holdout_matrix.copy()
    duration_holdout = summary.iloc[0]['duration_holdout']

    summary['model_predictions'] = summary.apply(lambda r: model.conditional_expected_number_of_purchases_up_to_time(duration_holdout, r['frequency_cal'], r['recency_cal'], r['T_cal']), axis=1)

    if kind == "time_since_last_purchase":
        summary["time_since_last_purchase"] = summary["T_cal"] - summary["recency_cal"]
        ax = summary.groupby(["time_since_last_purchase"])[['frequency_holdout', 'model_predictions']].mean().ix[:n].plot(**kwargs)
    else:
        ax = summary.groupby(kind)[['frequency_holdout', 'model_predictions']].mean().ix[:n].plot(**kwargs)

    plt.title('Actual Purchases in Holdout Period vs Predicted Purchases')
    plt.xlabel(x_labels[kind])
    plt.ylabel('Average of Purchases in Holdout Period')
    plt.legend()

    return ax


def plot_frequency_recency_matrix(model, T=1, max_x=None, max_t=None, **kwargs):
    """
    Plot a figure of expected transactions in T next units of time by a customer's
    frequency and recency.

    Parameters:
        model: a fitted lifetimes model.
        T: next units of time to make predictions for
        max_x: the maximum frequency to plot. Default is max observed frequency.
        max_t: the maximum recency to plot. This also determines the age of the customer.
            Default to max observed age.
        kwargs: passed into the matplotlib.imshow command.

    """
    from matplotlib import pyplot as plt

    if max_x is None:
        max_x = int(model.data['frequency'].max())

    if max_t is None:
        max_t = int(model.data['T'].max())

    Z = np.zeros((max_t + 1, max_x + 1))
    for i, t_x in enumerate(np.arange(max_t + 1)):
        for j, x in enumerate(np.arange(max_x + 1)):
            Z[i, j] = model.conditional_expected_number_of_purchases_up_to_time(T, x, t_x, max_t)

    interpolation = kwargs.pop('interpolation', 'none')

    ax = plt.subplot(111)
    ax.imshow(Z, interpolation=interpolation, **kwargs)
    plt.xlabel("Customer's Historical Frequency")
    plt.ylabel("Customer's Recency")
    plt.title('Expected Number of Future Purchases for %d Unit%s of Time,'
              '\nby Frequency and Recency of a Customer' % (T, "s"[T == 1:]))

    # turn matrix into square
    forceAspect(ax)

    # necessary for colorbar to show up
    PCM = ax.get_children()[2]
    plt.colorbar(PCM, ax=ax)

    return ax


def plot_probability_alive_matrix(model, max_x=None, max_t=None, **kwargs):
    """
    Plot a figure of the probability a customer is alive based on their
    frequency and recency.

    Parameters:
        model: a fitted lifetimes model.
        max_x: the maximum frequency to plot. Default is max observed frequency.
        max_t: the maximum recency to plot. This also determines the age of the customer.
            Default to max observed age.
        kwargs: passed into the matplotlib.imshow command.
    """
    from matplotlib import pyplot as plt

    z = model.conditional_probability_alive_matrix(max_x, max_t)

    interpolation = kwargs.pop('interpolation', 'none')

    ax = plt.subplot(111)
    ax.imshow(z, interpolation=interpolation, **kwargs)
    plt.xlabel("Customer's Historical Frequency")
    plt.ylabel("Customer's Recency")
    plt.title('Probability Customer is Alive,\nby Frequency and Recency of a Customer')

    # turn matrix into square
    forceAspect(ax)

    # necessary for colorbar to show up
    PCM = ax.get_children()[2]
    plt.colorbar(PCM, ax=ax)

    return ax


def plot_expected_repeat_purchases(model, **kwargs):
    from matplotlib import pyplot as plt

    ax = kwargs.pop('ax', None) or plt.subplot(111)
    color_cycle = ax._get_lines.color_cycle

    label = kwargs.pop('label', None)
    color = coalesce(kwargs.pop('c', None), kwargs.pop('color', None), next(color_cycle))
    max_T = model.data['T'].max()

    times = np.linspace(0, max_T, 100)
    ax = plt.plot(times, model.expected_number_of_purchases_up_to_time(times), color=color, label=label, **kwargs)

    times = np.linspace(max_T, 1.5 * max_T, 100)
    plt.plot(times, model.expected_number_of_purchases_up_to_time(times), color=color, ls='--', **kwargs)

    plt.title('Expected Number of Repeat Purchases per Customer')
    plt.xlabel('Time Since First Purchase')
    plt.legend(loc='lower right')
    return ax


def plot_history_alive(model, transactions, datetime_col, units, freq='D', **kwargs):
    """
    Draws a graph showing the probablility of being alive for a customer in time
    :param model: A fitted lifetimes model
    :param transactions: a Pandas DataFrame containing the transactions history of the customer_id
    :param datetime_col: the column in the transactions that denotes the datetime the purchase was made
    :param units: the number of time units since the birth we want to draw the p_alive
    :param freq: Default 'D' for days. Other examples= 'W' for weekly
    """

    from matplotlib import pyplot as plt

    start_date = kwargs.pop('start_date', min(transactions[datetime_col]))
    ax = kwargs.pop('ax', None) or plt.subplot(111)

    # Get purchasing history of user
    customer_history = transactions[[datetime_col]].copy()
    customer_history.index = pd.DatetimeIndex(customer_history[datetime_col])

    # Add transactions column
    customer_history['transactions'] = 1
    customer_history = customer_history.resample(freq, how='sum').reset_index()

    # plot alive_path
    path = calculate_alive_path(model, transactions, datetime_col, units, freq)
    path_dates = pd.date_range(start=min(transactions[datetime_col]), periods=len(path), freq=freq)
    plt.plot(path_dates, path, '-', label='P_alive')

    # plot buying dates
    payment_dates = customer_history[customer_history['transactions'] >= 1]['index']
    plt.vlines(payment_dates.values, ymin=0, ymax=1, colors='r', linestyles='dashed', label='purchases')

    plt.ylim(0, 1.0)
    plt.yticks(np.arange(0, 1.1, 0.1))
    plt.xlim(start_date, path_dates[-1])
    plt.legend(loc=3)
    plt.ylabel('P_alive')
    plt.title('History of P_alive')

    return ax


def forceAspect(ax, aspect=1):
    im = ax.get_images()
    extent = im[0].get_extent()
    ax.set_aspect(abs((extent[1] - extent[0]) / (extent[3] - extent[2])) / aspect)
