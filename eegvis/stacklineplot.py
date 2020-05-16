# -*- coding: utf-8 -*
from __future__ import division, print_function, absolute_import

""" based on multilineplot example in matplotlib with MRI data (I think)
uses line collections (might actually be from pbrain example)
- clm """
# TODO: probably want to modernize this to newer maptlotlib interface for better control
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def stackplot(
    marray,
    seconds=None,
    start_time=None,
    ylabels=[],
    yscale=1.0,
    topdown=False,
    ax=None,
    **kwargs
):
    """
    will plot a stack of traces one above the other assuming
    @marray contains the data you want to plot
    marray.shape = numRows, numSamples

    @seconds = with of plot in seconds for labeling purposes (optional)
    @start_time is start time in seconds for the plot (optional)

    @ylabels a list of labels for each row ("channel") in marray
    @yscale with increase (mutiply) the signals in each row by this amount
    """
    tarray = np.transpose(marray)
    return stackplot_t(
        tarray,
        seconds=seconds,
        start_time=start_time,
        ylabels=ylabels,
        yscale=yscale,
        topdown=topdown,
        ax=ax,
        **kwargs
    )


def stackplot_t(
    tarray,
    seconds=None,
    start_time=None,
    ylabels=[],
    yscale=1.0,
    topdown=False,
    ax=None,
    linecolor=None,
    linestyle=None,
):
    """
    will plot a stack of traces one above the other assuming
    @tarray is an nd-array like object with format
    tarray.shape =  numSamples, numRows

    @seconds = with of plot in seconds for labeling purposes (optional)
    @start_time is start time in seconds for the plot (optional)

    @ylabels a list of labels for each row ("channel") in marray
    @yscale with increase (mutiply) the signals in each row by this amount

    @ax is the option to pass in a matplotlib axes obj to draw with
    """
    data = tarray
    numSamples, numRows = tarray.shape
    # data = np.random.randn(numSamples,numRows) # test data
    # data.shape = numSamples, numRows
    if seconds:
        t = seconds * np.arange(numSamples, dtype=float) / numSamples
        # import pdb
        # pdb.set_trace()
        if start_time:
            t = t + start_time
            xlm = (start_time, start_time + seconds)
        else:
            xlm = (0, seconds)

    else:
        t = np.arange(numSamples, dtype=float)
        xlm = (0, numSamples)

    # if want to add ability to space by label
    # would do it here, check if labels; make sure right number
    # then interate, use special label to indicate a space
    ticklocs = []
    if not ax:
        ax = plt.subplot(111)

    plt.xlim(*xlm)
    # xticks(np.linspace(xlm, 10))
    dmin = data.min()
    dmax = data.max()
    dr = (dmax - dmin) * 0.7  # Crowd them a bit.
    y0 = dmin
    y1 = (numRows - 1) * dr + dmax
    plt.ylim(y0, y1)

    segs = []
    for ii in range(numRows):
        segs.append(np.hstack((t[:, np.newaxis], yscale * data[:, ii, np.newaxis])))
        # print("segs[-1].shape:", segs[-1].shape)
        ticklocs.append(ii * dr)

    offsets = np.zeros((numRows, 2), dtype=float)
    offsets[:, 1] = ticklocs
    if topdown == True:
        segs.reverse()

    linekwargs = {}
    if linecolor:
        linekwargs["color"] = linecolor
    if linestyle:
        linekwargs["linestyle"] = linestyle

    lines = LineCollection(segs, offsets=offsets, transOffset=None, **linekwargs)

    ax.add_collection(lines)

    # set the yticks to use axes coords on the y axis
    ax.set_yticks(ticklocs)
    # ax.set_yticklabels(['PG3', 'PG5', 'PG7', 'PG9']) # testing
    if len(ylabels) == 0:
        ylabels = ["%d" % ii for ii in range(numRows)]
    if topdown == True:
        ylabels = ylabels.copy()
        ylabels.reverse()  # this acts on ylabels in place
    ax.set_yticklabels(ylabels)

    plt.xlabel("time (s)")
    return ax


def test_stacklineplot():
    numSamples, numRows = 800, 5
    data = np.random.randn(numRows, numSamples)  # test data
    stackplot(data, 10.0)


def test_stacklineplot_colors():
    numSamples, numRows = 800, 5
    data = np.random.randn(numRows, numSamples)  # test data
    stackplot(data, 10.0, linecolor="green")
    plt.title("this plot should have green lines")


def limit_sample_check(x, signals):
    if x < 0:
        return 0
    num_chan, chan_len = signals.shape
    if x > chan_len:
        return chan_len
    return x


def show_epoch_centered(
    signals,
    goto_sec,
    epoch_width_sec,
    chstart,
    chstop,
    fs,
    ylabels=[],
    yscale=1.0,
    topdown=True,
    ax=None,
    **kwargs
):
    """
    @signals array-like object with signals[ch_num, sample_num]
    @goto_sec where to go in the signal to show the feature
    @epoch_width_sec length of the window to show in secs
    @chstart   which channel to start
    @chstop    which channel to end
    @labels_by_channel
    @yscale
    @fs sample frequency (num samples per second)
    """

    goto_sample = int(fs * goto_sec)
    hw = int(epoch_width_sec * fs / 2)  # half_width_epoch_sample

    # plot epochs of width epoch_width_sec centered on (multiples in DE)
    ch0, ch1 = chstart, chstop

    # epoch = 53
    # ptepoch = int(10 * fs)
    # dp = int(0.5 * ptepoch)
    s0 = limit_sample_check(goto_sample - hw, signals)
    s1 = limit_sample_check(goto_sample + hw, signals)
    duration = (s1 - s0) / fs
    start_time_sec = s0 / fs

    return stackplot(
        signals[ch0:ch1, s0:s1],
        start_time=start_time_sec,
        seconds=duration,
        ylabels=ylabels[ch0:ch1],
        yscale=yscale,
        topdown=topdown,
        ax=ax,
        **kwargs
    )


def show_montage_centered(
    signals,
    montage,
    goto_sec,
    epoch_width_sec,
    chstart,
    chstop,
    fs,
    ylabels=[],
    yscale=1.0,
    topdown=True,
    ax=None,
    **kwargs
):
    """
    @signals array-like object with signals[ch_num, sample_num]
    @goto_sec where to go in the signal to show the feature
    @epoch_width_sec length of the window to show in secs
    @chstart   which channel to start
    @chstop    which channel to end
    @labels_by_channel
    @yscale
    @fs sample frequency (num samples per second)
    """

    goto_sample = int(fs * goto_sec)
    hw = int(epoch_width_sec * fs / 2)  # half_width_epoch_sample

    # plot epochs of width epoch_width_sec centered on (multiples in DE)
    ch0, ch1 = chstart, chstop

    # ptepoch = int(10 * fs)
    # dp = int(0.5 * ptepoch)
    s0 = limit_sample_check(goto_sample - hw, signals)
    s1 = limit_sample_check(goto_sample + hw, signals)
    duration = (s1 - s0) / fs
    start_time_sec = s0 / fs
    # signals[ch0:ch1, s0:s1]
    # signal_view will not work if channels are not contiguous
    # TODO: use fancy indexing instead?
    signal_view = signals[:, s0:s1]
    inmontage_view = np.dot(montage.V.data, signal_view)

    rlabels = montage.montage_labels
    return stackplot(
        inmontage_view,
        start_time=start_time_sec,
        seconds=duration,
        ylabels=rlabels,
        yscale=yscale,
        topdown=topdown,
        ax=ax,
    )
