# -*- coding: utf-8 -*
from __future__ import division, print_function, absolute_import

""" based on multilineplot example in matplotlib with MRI data (I think)
uses line collections (might actually be from pbrain example)
- clm """
# TODO: probably want to modernize this to newer maptlotlib interface for better control
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import matplotlib.transforms
from matplotlib.lines import Line2D
from matplotlib.text import Text


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
    # as of matplotlib 3.5, don't get data offets by default
    # instead defaults to display/screen coordinates
    data_scale = np.zeros((3, 3), dtype=np.float64)
    data_scale[:2, :2] = ax.transData.get_matrix()[:2, :2]
    offsets_trans = matplotlib.transforms.Affine2D(data_scale)
    # offsetDeltaAf
    # matplotlib 3.6 renames transOffset to offset_transform, may need update in future
    lines = LineCollection(
        segs, offsets=offsets, transOffset=offsets_trans, **linekwargs
    )

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


# work on vertical scale bar

def add_data_vertical_scalebar(
    ax,
    data_height=100,
    units="",
    end_line_extent=0.01,
    color="black",
    anchor_position="lower right",
):
    """add_data_vertical_scalebar: add a vertical scalebar to a stackplot specific height in and units

    Args:
        ax (matplot figure axis object): axes object where to add the scalebar
        data_height (number): how high you want the scalebar in data units. Defaults to 100.
        units (str, optional): data units to use for height, e.g. "$\mu$V". Defaults to "".
        end_line_extent (float, optional): length in axes coordinate system of endlines. Defaults to 0.01.
        color (str, optional): color to use for scalebar. Defaults to "black".
        anchor_position (str, optional): where to anchor in ('upper left', 'center',...). Defaults to "lower right".
            see matplotlib AnchorOffset documentation
    returns: ax, the original axis object
    
    >>> fig, ax = plt.subplots()    
    >>> ax = stackplot(data, ax=ax)
    >>> add_data_vertical_scalebar(ax=ax,units=r'$\mu$V')
    >>> fig.figsave('fig.png')
    
    
    """

    linekw = {}
    trans = ax.transAxes
    transiv = ax.transAxes + ax.transData.inverted()  # axes->display -> data

    _x, size_axes = transiv.inverted().transform((0.0, data_height))
    size_bar = matplotlib.offsetbox.AuxTransformBox(trans)

    ## draw the vertical scale bar in axes coordiates
    #      Line2D(xdata, ydata, *, ...)
    line = Line2D([0, 0], [0, size_axes], color=color)  # , **linekw)
    vline1 = Line2D(
        [-end_line_extent / 2.0, end_line_extent / 2.0], [0, 0], color=color
    )
    vline2 = Line2D(
        [-end_line_extent / 2.0, end_line_extent / 2.0],
        [size_axes, size_axes],
        color=color,
    )
    size_bar.add_artist(line)
    size_bar.add_artist(vline1)
    size_bar.add_artist(vline2)
    txtbox = matplotlib.offsetbox.TextArea(
        f"{data_height}{units}", textprops=dict(color=color)
    )

    hpac = matplotlib.offsetbox.HPacker(
        children=[size_bar, txtbox], align="center", pad=0, sep=2
    )
    # hpac = size_bar # to just test size_bar
    big_artist = matplotlib.offsetbox.AnchoredOffsetbox(
        anchor_position, child=hpac, frameon=False
    )
    #
    ax.add_artist(big_artist)

    return ax

def add_relative_vertical_scalebar(
    ax,
    relative_height=0.1, # approx fraction of axes to use for vertical area
    units="",
    end_line_extent=0.01,
    color="black",
    anchor_position="lower right",
):
    """add a vertical scale bar with the same approximate size in the 
    figure (as defined by the axis). Will be rounded to nearest single
    precision number

    Args:
        ax (matplot figure axis object): axis object to draw to
        relative_height (float, optional): fraction of figure height. Defaults to 0.1.
        units (str, optional): data units to use for height, e.g. "$\mu$V". Defaults to "".
        end_line_extent (float, optional): length in axes coordinate system of endlines. Defaults to 0.01.
        color (str, optional): color to use for scalebar. Defaults to "black".
        anchor_position (str, optional): where to anchor in ('upper left', 'center',...). Defaults to "lower right".
            see matplotlib AnchorOffset documentation

    returns: the original axis, ax
            
    >>> fig, ax = plt.subplots()    
    >>> ax = stackplot(data, ax=ax)
    >>> add_relative_vertical_scalebar(ax=ax,units=r'$\mu$V')
    >>> fig.figsave('fig.png')
    """

    linekw = {}
    trans = ax.transAxes # axes -> display
    # + is a kind of weird composition operator, reverse what I thought
    transiv = ax.transAxes + ax.transData.inverted()  # axes->display -> data
    # _x, display_height = trans.transform((0.0, relative_height))
    #_x, data_height = ax.transData.inverted().transform((0, display_height))
    # hack to use only one significant digit by default
    _x, data_height = transiv.transform((0.0, relative_height))
    print(f"{data_height=} before")
    data_height = float("%.1g" % data_height)
    print(f"{data_height=} after")
    
    _x, size_axes = transiv.inverted().transform((0.0, data_height))
    print(f"{size_axes=}")
    size_bar = matplotlib.offsetbox.AuxTransformBox(trans)

    ## draw the vertical scale bar in axes coordiates
    #      Line2D(xdata, ydata, *, ...)
    line = Line2D([0, 0], [0, size_axes], color=color)  # , **linekw)
    vline1 = Line2D(
        [-end_line_extent / 2.0, end_line_extent / 2.0], [0, 0], color=color
    )
    vline2 = Line2D(
        [-end_line_extent / 2.0, end_line_extent / 2.0],
        [size_axes, size_axes],
        color=color,
    )
    size_bar.add_artist(line)
    size_bar.add_artist(vline1)
    size_bar.add_artist(vline2)
    txtbox = matplotlib.offsetbox.TextArea(
        f"{data_height}{units}", textprops=dict(color=color)
    )

    hpac = matplotlib.offsetbox.HPacker(
        children=[size_bar, txtbox], align="center", pad=0, sep=2
    )
    # hpac = size_bar # to just test size_bar
    big_artist = matplotlib.offsetbox.AnchoredOffsetbox(
        anchor_position, child=hpac, frameon=False
    )
    #
    ax.add_artist(big_artist)
    
    return ax
