# -*- coding: utf-8 -*
from __future__ import division, print_function, absolute_import

""" based on multilineplot example in matplotlib with MRI data (I think)
uses line collections (might actually be from pbrain example)
- clm """
# TODO: probably want to modernize this to newer maptlotlib interface for better control
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

# the idea behind a stacklineplot (from pyeeg) is that we have a bunch of
# uniformly sampled data in which we want to display one trace a little above the
# next usually time or samples is the x-axis and we want to be able to make it so
# the first sample data[0] sits on the leftmost edge of the frame and the last
# data sample (data[-1]) sits on the right-most edge of the frame


def stackplot(
    marray,
    seconds=None,
    start_time=None,
    ylabels=[],
    yscale=1.0,
    topdown=False,
    ax=None,
    **kwargs,
):
    """
    will plot a stack of traces one above the other assuming
    @marray contains the data you want to plot
    marray.shape = numRows, numSamples

    @seconds = with of plot in seconds for labeling purposes (optional)
    @start_time is start time in seconds for the plot (optional)

    @ylabels a list of labels for each row ("channel") in marray
    @yscale with increase (mutiply) the signals in each row by this amount


    @ysensitivity can be set to an absolute sensitivity along the y dimension in
      terms of millimeters of the plot
      for EEG this might be 7.0 or 10.0 to stand in for 7uV/mm
      this prevents the automatic scaling to the data size that is the default
      - should not usually be used with @yscale
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
        **kwargs,
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
    ysensitivity=None,
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

    @ysensitivity can be set to an absolute sensitivity along the y dimension in
      terms of millimeters of the plot
      for EEG this might be 7.0 or 10.0 to stand in for 7uV/mm
      this prevents the automatic scaling to the data size that is the default
      should not usually be used with @yscale
    """
    data = tarray
    numSamples, numRows = tarray.shape

    if seconds:
        t = seconds * np.arange(numSamples, dtype=float) / (numSamples - 1)

        if start_time:
            t = t + start_time
            xlm = (start_time, start_time + seconds)
        else:
            xlm = (0, seconds)

    else:
        t = np.arange(numSamples, dtype=float)  # should dtype=int?
        xlm = (0, numSamples - 1)

    # if want to add ability to space by label
    # would do it here, check if labels; make sure right number
    # then interate, use special label to indicate a space
    ticklocs = []
    if not ax:
        ax = plt.subplot(
            111
        )  # would it be better to use fig=figure(), then fig.subplots(1,1)?

    ax.set_xmargin(
        0
    )  # may be redundant, not we may be altering settings of an exisiting ax

    ax.set_xlim(*xlm)
    # # xticks(np.linspace(xlm, 10))
    dmin = data.min()
    dmax = data.max()
    # dr = (dmax - dmin) * 0.7  # Crowd them a bit.
    # y0 = dmin
    # y1 = (numRows - 1) * dr + dmax
    # ax.set_ylim(y0, y1)

    # segs = []
    # for ii in range(numRows):
    #     segs.append(np.hstack((t[:, np.newaxis], yscale * data[:, ii, np.newaxis])))
    #     # print("segs[-1].shape:", segs[-1].shape)
    #     ticklocs.append(ii * dr)
    if not ysensitivity:
        dr = (dmax - dmin) * 0.7  # Crowd them a bit.
        y0 = dmin
        y1 = (numRows - 1) * dr + dmax
        ax.set_ylim(y0, y1)
        segs = []
        for ii in range(numRows):
            segs.append(np.hstack((t[:, np.newaxis], yscale * data[:, ii, np.newaxis])))
            # print("segs[-1].shape:", segs[-1].shape)
            ticklocs.append(ii * dr)
    elif ysensitivity:  # in this case we have an absolute number of y-units per page
        # this is again to setting 7 uV per mm on a page or where 7 may vary
        # basically it figure out how many mm high the plot is, figures out how many
        # uV that covers, then divides up the available unit space among the
        # channels. Would need to do something differen tif wanted to show a subset
        # of channels then scroll them
        myfig = ax.get_figure()
        figsizex_inch, figsizey_inch = myfig.get_size_inches()
        dpi = myfig.dpi
        dpmm = dpi / 25.4

        figsizex_mm = 25.4 * figsizex_inch
        figsizey_mm = 25.4 * figsizey_inch

        # sensetivity such as 7 uV/mm is
        total_uV = ysensitivity * figsizey_mm
        # assume data is in uV
        # is lower lim of y still dmin? No
        perchan_uV = total_uV / numRows
        dr = perchan_uV
        y0 = 0
        y1 = total_uV
        ax.set_ylim(y0, y1)

        segs = []
        for ii in range(numRows):
            segs.append(np.hstack((t[:, np.newaxis], yscale * data[:, ii, np.newaxis])))
            # print("segs[-1].shape:", segs[-1].shape)
            ticklocs.append(ii * dr + dr / 2.0)

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

    if seconds:
        ax.set_xlabel("time (s)")
    else:
        ax.set_xlabel("sample num")
    return ax


def test_stacklineplot():
    numSamples, numRows = 800, 5
    data = np.random.randn(numRows, numSamples)  # test data
    stackplot(data, 10.0)


def test_stacklineplot0():
    "using all default arguments"
    numSamples, numRows = 4, 2
    data = np.random.randn(numRows, numSamples)  # test data
    stackplot(data)


def test_stacklineplot1():
    numSamples, numRows = 4, 2
    data = np.random.randn(numRows, numSamples)  # test data
    stackplot(data, seconds=3.0)


def test_stacklineplot2():
    numSamples, numRows = 2000, 5
    data = np.random.randn(numRows, numSamples)  # test data
    stackplot(data, seconds=10.0)


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


# minimal EEG object needs:
# data: signals : array-like (n_chan, n_samples)
# sample_frequency
# optional: channel labels


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
    **kwargs,
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
    s1 = limit_sample_check(
        goto_sample + hw, signals
    )  # TODO: fix note that this does check for end
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
        **kwargs,
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
    **kwargs,
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

    inmontage_view = np.dot(
        montage.V.data, signal_view
    )  # montage.V.data is matrix (linear transform)

    rlabels = montage.montage_labels
    return stackplot(
        inmontage_view,
        start_time=start_time_sec,
        seconds=duration,
        ylabels=rlabels,
        yscale=yscale,
        topdown=topdown,
        ax=ax,
        **kwargs,
    )


def stackplot_t_with_heatmap(
    tarray,
    seconds=None,
    start_time=None,
    ylabels=[],
    yscale=1.0,
    topdown=False,
    ax=None,
    linecolor=None,
    linestyle=None,
    heatmap_image=None,
    alpha=0.5,
    cmap="magma",
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
    @heatmap_image should be an ndarray usually this will be of shape something                    like (NUM_CH, NUM_TIME_STEPS)
    @alpha is how to blend this

    generally want to choose a perceptually uniform colormap
    inferno, magma, viridis, cividis, etc see also
    colorcet.cm.fire, .bmw etc for excellent colormaps

    >>> heatmap_image = np.random.uniform(size=(NUM_CH, NUM_CHUNKS))

    """
    if not ax:
        fig, ax = plt.subplots(1, 1)
        # fig.set_size_inches(FIGSIZE[0], 2 * FIGSIZE[1])
    # print()
    # print(axarr, f"clip_length (sec): {clip_length},", f"seconds = {clip_length*NUM_CHUNKS},")
    eegax = stackplot_t(
        tarray,
        seconds=seconds,  # this looks like a mistake!!!
        ylabels=ylabels,
        topdown=True,
        ax=ax,
    )
    # to get the image to scale to the plot, reset the extent to match the current limits
    left, right = eegax.get_xlim()
    bottom, top = eegax.get_ylim()
    # choose to overwrite plot with image but use alpha to modify blending
    # if want EEG plot on top then set zorder to lower like 0
    if heatmap_image is not None:
        eegax.imshow(
            heatmap_image,
            origin="upper",
            interpolation="bilinear",
            aspect="auto",
            extent=[left, right, bottom, top],
            alpha=alpha,
            zorder=3,
            cmap=cmap,
        )  # inferno, magma, viridis, cividis, etc

    return ax  # or eegax?, should there be a way to get the figure too?


def stackplot_t_with_rgba_heatmap(
    tarray,
    heatmap_image,
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
    @heatmap_image should be an ndarray usually this will be of shape something                    like (NUM_CH, NUM_TIME_STEPS, 4) so that it includes RGB and alpha values
    this allows you to control the alpha value as part of the mask

    generally want to choose a perceptually uniform colormap
    inferno, magma, viridis, cividis, etc see also
    colorcet.cm.fire, .bmw etc for excellent colormaps

    >>> heatmap_image = np.random.uniform(size=(NUM_CH, NUM_CHUNKS))

    """
    if not ax:
        fig, ax = plt.subplots(1, 1)
        # fig.set_size_inches(FIGSIZE[0], 2 * FIGSIZE[1])
    # print()
    # print(axarr, f"clip_length (sec): {clip_length},", f"seconds = {clip_length*NUM_CHUNKS},")
    eegax = stackplot_t(
        tarray,
        seconds=seconds,
        ylabels=ylabels,
        topdown=True,
        ax=ax,
    )
    # to get the image to scale to the plot, reset the extent to match the current limits
    left, right = eegax.get_xlim()
    bottom, top = eegax.get_ylim()
    # choose to overwrite plot with image but use alpha to modify blending
    # if want EEG plot on top then set zorder to lower like 0

    eegax.imshow(
        heatmap_image,
        origin="upper",
        interpolation="bilinear",
        aspect="auto",
        extent=[left, right, bottom, top],
        zorder=3,
    )

    return ax  # or eegax?, should there be a way to get the figure too?
