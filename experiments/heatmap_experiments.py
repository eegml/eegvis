# %% [markdown]
# # Heatmap experiments
# In our work, we often would like to show a "heatmap" superimposed with an EEG. This may represent saliency, or a feature or where attention is directed.
#
# Here I am working out ways to show a heatmap with EEGs using the matplotlib backend.
#

# %%
# %matplotlib inline
import matplotlib.pyplot as plt

FIGSIZE = (12.0, 4.0)
plt.rc("figure", figsize=(12.0, 4.0))  # which is the best way to do this?

import numpy as np
import eegml_signal
import eegvis.mpl_helpers
from eegvis import stacklineplot
import eegvis.montageview
import eeghdf  # not actually necessary

# %%
# set notebook styling to use whole width of browser window
from IPython.core.display import display, HTML

display(HTML("<style>.container { width:100% !important; }</style>"))
# matplotlib.rcParams['figure.figsize'] = (40, 32)

# %%
# some quick test mockups of EEG and a heatmap
clip_length = 5.0  # 5 seconds
Fs = 200
NUM_CHUNKS = 20
NUM_CH = 19
heatmap_ex = np.random.uniform(size=(NUM_CH, NUM_CHUNKS))

# %%
testeeg = np.random.randn(19, Fs * NUM_CHUNKS)

# %%
# note I have pushed this change to stackplot_t to the eegvis repo
# but I am leaving the code here for reference

from matplotlib.collections import LineCollection


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

    ax.set_xlim(*xlm)
    # xticks(np.linspace(xlm, 10))
    dmin = data.min()
    dmax = data.max()
    dr = (dmax - dmin) * 0.7  # Crowd them a bit.
    y0 = dmin
    y1 = (numRows - 1) * dr + dmax
    ax.set_ylim(y0, y1)

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

    ax.set_xlabel("time (s)")
    return ax


# %%
# simple vis of heatmap, but not scaled right
plt.imshow(heatmap_ex)

# %%

INCLUDED_CHANNELS = [
    "EEG Fp1",
    "EEG Fp2",
    "EEG F3",
    "EEG F4",
    "EEG C3",
    "EEG C4",
    "EEG P3",
    "EEG P4",
    "EEG O1",
    "EEG O2",
    "EEG F7",
    "EEG F8",
    "EEG T3",
    "EEG T4",
    "EEG T5",
    "EEG T6",
    "EEG Fz",
    "EEG Cz",
    "EEG Pz",
]
# (testeeg.T, clip_length*NUM_CHUNKS, INCLUDED_CHANNELS)

## basic plot of an EEG
stacklineplot.stackplot(
    testeeg, seconds=clip_length * NUM_CHUNKS, ylabels=INCLUDED_CHANNELS, topdown=True
)

# %%
# figure out how to strecht a image

fig = plt.figure()
fig.set_size_inches(FIGSIZE[0], FIGSIZE[1])
plt.imshow(heatmap_ex, origin="upper", interpolation="bilinear", aspect="auto")
plt.axis("off")

# %% [markdown]
# ### Ok, now we are getting somewhere
# So at the very least, we should be able to put these two things one above the other

# %%
fig, axarr = plt.subplots(2, 1)
fig.set_size_inches(FIGSIZE[0], 2 * FIGSIZE[1])
# print()
# print(axarr, f"clip_length (sec): {clip_length},", f"seconds = {clip_length*NUM_CHUNKS},")
eegax = stackplot_t(
    testeeg.T,
    seconds=clip_length * NUM_CHUNKS,
    ylabels=INCLUDED_CHANNELS,
    topdown=True,
    ax=axarr[0],
)
axarr[1].imshow(heatmap_ex, origin="upper", interpolation="bilinear", aspect="auto")
axarr[1].axis("off")
# axarr[1].xaxis.set_visible(False) # Hide only x axis
# axarr[1].yaxis.set_visible(False) # Hide only x axis

# %% [markdown]
# ## Next thing, see about fusing two plots together
# This looks quite good and the image fills up the EEG plot completely.
# There is the possibility of some slight misalignment, I suppose but I think it is adequate.
#
# I think this approach will work for most of the matplotlib based EEG plots when they need an image to back them.

# %%
fig, axarr = plt.subplots(1, 1)
fig.set_size_inches(FIGSIZE[0], 2 * FIGSIZE[1])
# print()
# print(axarr, f"clip_length (sec): {clip_length},", f"seconds = {clip_length*NUM_CHUNKS},")
eegax = stacklineplot.stackplot_t(
    testeeg.T,
    seconds=clip_length * NUM_CHUNKS,
    ylabels=INCLUDED_CHANNELS,
    topdown=True,
    ax=axarr,
)
# to get the image to scale to the plot, reset the extent to match the current limits
left, right = axarr.get_xlim()
bottom, top = axarr.get_ylim()
# choose to overwrite plot with image but use alpha to modify blending
# if want EEG plot on top then set zorder to lower like 0
axarr.imshow(
    heatmap_ex,
    origin="upper",
    interpolation="bilinear",
    aspect="auto",
    extent=[left, right, bottom, top],
    alpha=0.5,
    zorder=3,
    cmap="inferno",
)  # inferno, magma, viridis, cividis, etc


# %%
heatmap_ex.shape

# %%
axarr.get_xlim()

# %%
axarr.get_ylim()

# %% [markdown]
# Here is the same thing but without the interpolation. You can see how the bottom squares don't completely center on the EEG trace of EEG Pz.
# Could probably change the bottom extent a little to fix this.

# %%

import colorcet

fig, axarr = plt.subplots(1, 1)
fig.set_size_inches(FIGSIZE[0], 2 * FIGSIZE[1])
# print()
# print(axarr, f"clip_length (sec): {clip_length},", f"seconds = {clip_length*NUM_CHUNKS},")

eegax = stacklineplot.stackplot_t(
    testeeg.T,
    seconds=clip_length * NUM_CHUNKS,
    ylabels=INCLUDED_CHANNELS,
    topdown=True,
    ax=axarr,
)
# to get the image to scale to the plot, reset the extent to match the current limits
left, right = axarr.get_xlim()
bottom, top = axarr.get_ylim()
# choose to overwrite plot with image but use alpha to modify blending
# if want EEG plot on top then set zorder to lower like 0
axarr.imshow(
    heatmap_ex,
    origin="upper",
    interpolation="bilinear",
    aspect="auto",
    extent=[left, right, bottom, top],
    alpha=0.5,
    zorder=3,
    cmap=colorcet.cm.bmw,
)  # inferno, magma, viridis, cividis, etc 
# colorcet.cm.fire, colorcet.cm.blues, gray, bgwy, bmw, etc. 

# %%
from colorcet.plotting import swatch, swatches
import holoviews as hv
hv.extension('matplotlib')

# %%
swatches()

# %%


# %%

# %%

fig, axarr = plt.subplots(1, 1)
fig.set_size_inches(2*FIGSIZE[0], 2*2 * FIGSIZE[1])
# print()
# print(axarr, f"clip_length (sec): {clip_length},", f"seconds = {clip_length*NUM_CHUNKS},")
eegax = stacklineplot.stackplot_t(
    testeeg.T,
    seconds=clip_length * NUM_CHUNKS,
    ylabels=INCLUDED_CHANNELS,
    topdown=True,
    ax=axarr,
)
# to get the image to scale to the plot, reset the extent to match the current limits
left, right = axarr.get_xlim()
bottom, top = axarr.get_ylim()
# choose to overwrite plot with image but use alpha to modify blending
# if want EEG plot on top then set zorder to lower like 0
axarr.imshow(
    testeegalpha,
    origin="upper",
    interpolation="bilinear",
    aspect="auto",
    extent=[left, right, bottom, top],
    
    zorder=3,
    cmap="inferno",
)  # inferno, magma, viridis, cividis, etc


# %%
