# -*- coding: utf-8 -*-
# this is where I can "store" my accumulated knowledge about matplotlib
"""
Coordinate  | Transformation Object | Description
data        | ax.transData          | The userland data coordinate system, controlled by the xlim and ylim
axes        | ax.transAxes          | The coordinate system of the Axes; (0,0) is bottom left of the axes, and
            |                       | (1,1) is top right of the axes.
figure      | fig.transFigure       | The coordinate system of the Figure; (0,0) is bottom left of the
            |                       | figure, and (1,1) is top right of the figure.
display     | None                  | This is the pixel coordinate system of the display; (0,0) is the bottom
            |                       | left of the display, and (width, height) is the top right of the display
            |                       | in pixels. Alternatively, the identity transform
            |                       | (matplotlib.transforms.IdentityTransform()) may be used instead of None.

The important thing to remember is that the transforms all convert from the source coordinate system to display coordinates


"""
import matplotlib
import matplotlib.pyplot as plt
import numpy as np


def transformAxesCoord2FigureCoord(coordarr, ax, fig=None):
    """ 
    "axes coord" [0,1]x[0,1] -> "display coord" -> "figure coord"
    useful to find the correct ax extent in figure coordates

    if @ax is an Axes object
    If it has a figure attached already, can just use that, otherwise, specify the figure as @fig

    This is not efficient for repetitive use because it calcs the inverse each time, 
    Look at the code to create a more efficent version
    """
    if not fig:
        fig = ax.figure

    # transform display -> figure coords [0,1]x[0,1]
    figtrans_inv = fig.transFigure.inverted()

    return figtrans_inv.transform(ax.transAxes.transform(coordarr))


def new_blank_axis_full_figure(frameon=False):
    """create a figure with out the background frame
    create an axis object for drawing which uses the full extent of the figure
    so that extent=[0,0, 0.0, 1.0, 1.0]
    so ax.set_axis_of to turn off the axis lines, ticks, ticklables, grid and axis labels

    The idea is to create something akin to a "blank canvas" to work on

    return (figure, axis) objects
    """
    fig = plt.figure(frameon=frameon)
    # fig.set_tight_layout(True)
    ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])  # origin [x,y, w,h]
    ax.set_axis_off()
    fig.add_axes(ax)

    return fig, ax


def overlay_image_on_plot(ax, imarr, frameon=True, aspect="auto", alpha=None, zorder=2):
    """assume that you make a regular matplotlib plot using axis @ax
    then take the image array @imarr and replace the inside of the plot
    with the image

    I have not figured out how to blend this directly

    plot imarr as an image over the plot section used in
    axis object ax
    if was originally a (pillow) PIL.Image, then use_default_template

    imarr = numpy.array(im)

    Note this function is not quite right yet. The extent is being set for
    the axes image as 0,0,1,0 but which acts like it is display
    coordinates at first but is actually data coordinates from what I
    can tell. It works in narrow cases but does not make sense more generally

    """

    fig = ax.figure
    # find lower left and upper right corners of ax "canvas" in display coords
    x0y0 = transformAxesCoord2FigureCoord((0.0, 0.0), ax)
    x1y1 = transformAxesCoord2FigureCoord((1.0, 1.0), ax)
    # create an Axes object just to hold the image
    im_ax = plt.Axes(
        fig,
        [  # place in new axis in the same place as ax drawing area
            x0y0[0],  # x0
            x0y0[1],  # y0
            x1y1[0] - x0y0[0],  # width
            x1y1[1] - x0y0[1],  # height
        ],
        frameon=frameon,  # background frame is drawn
        aspect=aspect,  # probably want 'auto' to scale to fit whole plotting area
        alpha=alpha,  # not sure yet if this works
    )  # alpha a, xlim, ylim, xticks, yticks, etc.. zorder?

    axesimage = matplotlib.image.AxesImage(
        im_ax,
        extent=[  # need to make extent 1x1 square or won't use whole image
            0.0,
            1.0,
            0.0,
            1.0,
        ],
        zorder=zorder,  # make sure it is ontop
    )

    axesimage.set_data(imarr)
    im_ax.add_image(axesimage)
    im_ax.set_axis_off()  # don't draw the splines
    fig.add_axes(im_ax)

    return im_ax  # return the new axes object in case want to do more with it


def test_overlay_image_on_plot(frameon=True, aspect="auto", alpha=None, zorder=2):
    # create a sine plot
    # wonder if I should be specifcying backend at this point
    # note this shows that this works, but there is something not right
    # if another plot is done after the image is added
    t = np.arange(10.0, step=0.01)
    y = np.sin(2 * np.pi * t)

    fig1 = plt.figure()
    ax1 = plt.subplot(111)

    ax1.plot(t, y)

    q = np.arange(1, 10)
    Q = np.outer(q, q)

    overlay_image_on_plot(
        ax1, Q, frameon=frameon, aspect=aspect, alpha=alpha, zorder=zorder
    )
    return fig1, ax1
