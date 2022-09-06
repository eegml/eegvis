# -*- coding: utf-8 -*-
# %% put code to view whole eeg files here
# moving to using panel widgets and layout instead of bokeh stuff
# to bokeh app which runs inside a panel.pane.Bokeh()
# compare with eegbokeh.py which focuses on using bokeh widgets
from __future__ import absolute_import, print_function, division, unicode_literals
from collections import OrderedDict
import pprint

import numpy as np

# import ipywidgets # use bokeh widgets instead of ipywidgets to reduce dependencies
# try panel instead
import panel as pn
import panel.widgets


# get layouts, start ith row, column
import bokeh.layouts

#%%
import bokeh.plotting
from bokeh.models import FuncTickFormatter, Range1d

# widgets
from bokeh.models import (
    BoxAnnotation,
    Button,
    Div,
    Select,
    Spinner,
    RadioGroup,
    CheckboxGroup,
    CustomJS,
)

# import panel as pn
# from panel.widgets import Button, Select, Spinner, RadioBoxGroup
#
from bokeh.models.tickers import FixedTicker, SingleIntervalTicker

from . import montageview #_stanford
from . import montage_derivations_edf_simplified
from . import stackplot_bokeh
from .stackplot_bokeh import limit_sample_check
from bokeh.io import push_notebook

import eegml_signal.filters as esfilters
import pdb
import signalslot

#%%

# """
# notes on setting ranges for a plot

# from bokeh.models import Range1d

# fig = make_fig()
# left, right, bottom, top = 3, 9, 4, 10
# fig.x_range=Range1d(left, right)
# fig.y_range=Range1d(bottom, top)
# show(fig)
# to update dynamically, then change fig.y_range.start = newbottom; fig.y_range.end = newtop
# """

# this is not used yet

#%% [markdown]
# ### [Bokeh Callbacks](https://docs.bokeh.org/en/latest/docs/user_guide/interaction/widgets.html)
# To use widgets, you must add them to your document and define their callbacks. Widgets can be added directly to the document root or nested inside a layout. There are two ways to use a widget’s functionality:

# - A CustomJS callback (see JavaScript Callbacks). This approach will work in standalone HTML documents or Bokeh server apps.

# - Use bokeh serve to start a Bokeh server and set up event handlers with .on_change (or for some widgets, .on_click).
#
# Event handlers are Python functions that users can attach to widgets. These functions are then called when certain attributes on the widget are changed. The function signature of event handlers is determined by how they are attached to widgets (e.g. whether by .on_change or .on_click).
#
# All widgets have an .on_change method that takes an attribute name and one or more event handlers as parameters. These handlers are expected to have the function signature, (attr, old, new), where attr refers to the changed attribute’s name, and old and new refer to the previous and updated values of the attribute.
# ```python
# def my_text_input_handler(attr, old, new):
#     print("Previous label: " + old)
#     print("Updated label: " + new)
#
# text_input = TextInput(value="default", title="Label:")
# text_input.on_change("value", my_text_input_handler)
# ```
# Additionally, some widgets, including the button, dropdown, and checkbox, have an .on_click method that takes an event handler as its only parameter. For a plain Button, this handler is called without parameters. For the other widgets with .on_click, the handler is passed the new attribute value.
# ```python
# def my_radio_handler(new):
#     print 'Radio button option ' + str(new) + ' selected.'
#
# radio_group = RadioGroup(labels=["Option 1", "Option 2", "Option 3"], active=0)
# radio_group.on_click(my_radio_handler)
# ```
#%% [markdown]
# ### [bokeh.events](https://docs.bokeh.org/en/latest/docs/reference/events.html)


#%%


def ignore_warnings():
    """suppress warnings trick
    this is not really tested yet"""
    import sys

    if not sys.warnoptions:
        import warnings

        warnings.simplefilter("ignore")


def setNotebookWidth100():
    from IPython.core.display import display, HTML

    display(HTML("<style>.container { width:100% !important; }</style>"))
    np.set_printoptions(linewidth=110)  # apply width to output formatting
    # cf jupyter themes https://github.com/dunovank/jupyter-themes
    # jt -t oceans16 -f roboto -fs 12 -cellw 100%
    # https://stackoverflow.com/questions/21971449/how-do-i-increase-the-cell-width-of-the-jupyter-ipython-notebook-in-my-browser


class EeghdfBrowser:
    """
    take an hdfeeg file and allow for browsing of the EEG signal

    just use the raw hdf file and conventions for now

    Signals: move_sec, file_name
    Slots: receive_overviewloc_update
    """

    def __init__(
        self,
        stanford_file_names, #eeghdf_file_names
        tuh_file_names,
        stanford_files, #eeghdf_files,
        tuh_files,
        page_width_seconds=10.0,
        start_seconds=-1,
        montage="double banana",
        montage_options={},
        tuh = True,
        yscale=1.0,
        plot_width=950,
        plot_height=600,
    ):
        """
        @eegfile is an eeghdf.Eeghdf() class instance representing the file
        @montage is either a string in the standard list or a montageview factory
        @eeghdf_files - a list of eeghdf.Eeeghdf instances
        @page_width_seconds = how big to make the view in seconds
        @montage - montageview (class factory) OR a string that identifies a default montage (may want to change this to a factory function 
        @start_seconds - center view on this point in time
        @tuh - bool indicating if signal is coming from tuh

        BTW 'trace' is what NK calls its 'as recorded' montage - might be better to call 'raw', 'default' or 'as recorded'
        """
        self.tuh = tuh
        self.eeghdf_file_names = tuh_file_names #eeghdf_file_names
        self.eeghdf_files = tuh_files #eeghdf_files
        self.eeghdf_file = self.eeghdf_files[0]
        self.update_eeghdf_file(self.eeghdf_file, montage, montage_options)

        self.stanford_file_names = stanford_file_names
        self.tuh_file_names = tuh_file_names
        self.stanford_files = stanford_files
        self.tuh_files = tuh_files


        # display related
        self.page_width_seconds = page_width_seconds

        ## bokeh related

        self.page_width_secs = page_width_seconds
        if start_seconds < 0:
            self.loc_sec = (
                page_width_seconds / 2.0
            )  # default location in file by default at start if possible
        else:
            self.loc_sec = start_seconds

        # self.init_kwargs = kwargs
        self.move_signal = signalslot.Signal(args=["move_sec"])
        self.filename_signal = signalslot.Signal(args=["filename"])

        # other ones
        self.yscale = yscale
        self.ui_plot_width = plot_width
        self.ui_plot_height = plot_height

        self.bk_handle = None
        self.fig = None

        self.update_title()

        self.num_rows, self.num_samples = self.signals.shape
        self.line_glyphs = []  # not used?
        self.multi_line_glyph = None

        self.ch_start = 0
        self.ch_stop = self.current_montage_instance.shape[0]

        ####### set up filter cache: first try
        self.current_hp_filter = None
        self.current_lp_filter = None
        self._highpass_cache = OrderedDict()

        self._highpass_cache["None"] = None

        self._highpass_cache["0.1 Hz"] = esfilters.fir_highpass_firwin_ff(
            self.fs, cutoff_freq=0.1, numtaps=int(self.fs)
        )

        self._highpass_cache["0.3 Hz"] = esfilters.fir_highpass_firwin_ff(
            self.fs, cutoff_freq=0.3, numtaps=int(self.fs)
        )

        # ff = esfilters.fir_highpass_remez_zerolag(fs=self.fs, cutoff_freq=1.0, transition_width=0.5, numtaps=int(2*self.fs))
        ff = esfilters.fir_highpass_firwin_ff(
            fs=self.fs, cutoff_freq=1.0, numtaps=int(2 * self.fs)
        )
        self._highpass_cache["1 Hz"] = ff
        # ff = esfilters.fir_highpass_remez_zerolag(fs=self.fs, cutoff_freq=5.0, transition_width=2.0, numtaps=int(0.2*self.fs))
        ff = esfilters.fir_highpass_firwin_ff(
            fs=self.fs, cutoff_freq=5.0, numtaps=int(0.2 * self.fs)
        )
        self._highpass_cache["5 Hz"] = ff

        firstkey = "0.3 Hz"  # list(self._highpass_cache.keys())[0]
        self.current_hp_filter = self._highpass_cache[firstkey]

        self._lowpass_cache = OrderedDict()
        self._lowpass_cache["None"] = None
        self._lowpass_cache["15 Hz"] = esfilters.fir_lowpass_firwin_ff(
            fs=self.fs, cutoff_freq=15.0, numtaps=int(self.fs / 2.0)
        )
        self._lowpass_cache["30 Hz"] = esfilters.fir_lowpass_firwin_ff(
            fs=self.fs, cutoff_freq=30.0, numtaps=int(self.fs / 4.0)
        )
        self._lowpass_cache["50 Hz"] = esfilters.fir_lowpass_firwin_ff(
            fs=self.fs, cutoff_freq=50.0, numtaps=int(self.fs / 4.0)
        )
        self._lowpass_cache["70 Hz"] = esfilters.fir_lowpass_firwin_ff(
            fs=self.fs, cutoff_freq=70.0, numtaps=int(self.fs / 4.0)
        )

        self._notch_filter = esfilters.notch_filter_iir_ff(
            notch_freq=60.0, fs=self.fs, Q=60
        )
        self.current_notch_filter = None

    def receive_overviewloc_update(self, overview_loc, **kwargs):
        self.loc_sec = overview_loc
        self.update()

    @property
    def signals(self):
        return self.eeghdf_file.phys_signals

    def update_eeghdf_file(self, eeghdf_file, montage="double banana", montage_options={}):
        self.eeghdf_file = eeghdf_file
        hdf = eeghdf_file.hdf
        rec = hdf["record-0"]
        self.fs = int(rec.attrs["sample_frequency"])

        # TODO: this HACK is model specific, we cut out last (signal_length % 60) secs
        # we do this b/c model does not output probs for clips < 60sec
        #pdb.set_trace()
        signal_len = self.eeghdf_file.phys_signals.shape[1] / self.fs
        remaining_samples = int(self.fs * (signal_len % 60))
        if remaining_samples > 0:
            self.eeghdf_file._phys_signals = self.eeghdf_file.phys_signals[
                :, :-remaining_samples
            ]
        self.eeghdf_file.duration_seconds = (
            self.eeghdf_file.phys_signals.shape[1] / self.fs
        )

        # self.signals = rec['signals']
        blabels = rec["signal_labels"]  # byte labels
        # self.electrode_labels = [str(ss,'ascii') for ss in blabels]
        self.electrode_labels = eeghdf_file.electrode_labels
        # fill in any missing ones
        if len(self.electrode_labels) < eeghdf_file.phys_signals.shape[0]:
            d = eeghdf_file.phys_signals.shape[0] - len(self.electrode_labels)
            ll = len(self.electrode_labels)
            suppl = [str(ii) for ii in range(ll, ll + d)]
            self.electrode_labels += suppl
            print("extending electrode lables:", suppl)

        # reference labels are used for montages, since this is an eeghdf file, it can provide these

        if self.tuh:
            self.ref_labels = eeghdf_file.electrode_labels 
        else:
            self.ref_labels = eeghdf_file.shortcut_elabels

        #if not montage_options:
            # then use builtins and/or ones in the file
        if self.tuh:
            montage_options = montage_derivations_edf_simplified.EDF_SIMPLIFIED_MONTAGE_BUILTINS.copy()
        else:
            montage_options = montageview.MONTAGE_BUILTINS.copy()

            # print('starting build of montage options', montage_options)

            # montage_options = eeghdf_file.get_montages()

        # defines self.current_montage_instance
        self.current_montage_instance = None
        if type(montage) == str:  # then we have some work to do
            if montage in montage_options:
                #try:
                self.current_montage_instance = montage_options[montage](
                    self.ref_labels
                )
                #except:
                #    self.data_source.data.update(dict(xs=[0], ys=[0]))
                #    self.current_montage_instance = montage_options[0](self.ref_labels)
            else:
                raise Exception("unrecognized montage: %s" % montage)
        else:
            if montage:  # is a class
                self.current_montage_instance = montage(self.ref_labels)
                montage_options[self.current_montage_instance.name] = montage
            else:  # use default

                self.current_montage_instance = montage_options[0](self.ref_labels)

        assert self.current_montage_instance
        try:  # to update ui display
            self.ui_montage_dropdown.value = self.current_montage_instance.name
        except AttributeError:
            # guess is not yet instantiated
            pass

        self.montage_options = montage_options  # save the montage_options for later
        self.update_title()
        # note this does not do any plotting or update the plot

    def update_title(self):
        self.title = "hdf %s - montage: %s" % (
            self.eeghdf_file.hdf.filename,
            self.current_montage_instance.full_name
            if self.current_montage_instance
            else "",
        )

    #         if showchannels=='all':
    #             self.ch_start = 0  # change this to a list of channels for fancy slicing
    #             if montage:
    #                 self.ch_stop = montage.shape[0] # all the channels in the montage
    #             self.ch_stop = signals.shape[0] # all the channels in the original signal
    #         else:
    #             self.ch_start, self.ch_stop = showchannels
    #         self.num_rows, self.num_samples = signals.shape
    #         self.line_glyphs = []
    #         self.multi_line_glyph = None

    def plot(self, **kwargs):
        """create a Bokeh figure to hold EEG"""
        self.fig = self.show_montage_centered(
            self.signals,
            self.loc_sec,
            page_width_sec=self.page_width_secs,
            chstart=0,
            chstop=self.current_montage_instance.shape[0],
            fs=self.fs,
            ylabels=self.current_montage_instance.montage_labels,
            yscale=self.yscale,
            montage=self.current_montage_instance,
            **kwargs,
        )
        self.fig.xaxis.axis_label = "seconds"
        # make the xgrid mark every second
        self.fig.xgrid.ticker = SingleIntervalTicker(
            interval=1.0
        )  #  bokeh.models.tickers.SingleIntervalTicker
        return self.fig

    def show_for_bokeh_app(self):
        """try running intside a bokeh app, so don't need notebook stuff"""
        self.plot()

    def bokeh_show(self):
        """
        meant to run in notebook so sets up handles
        """
        self.plot()
        self.register_top_bar_ui()  # create the buttons
        self.bk_handle = bokeh.plotting.show(self.fig, notebook_handle=True)
        self.register_bottom_bar_ui()

    def update(self):
        """
        updates the data in the plot and does push_notebook
        so that it will show up
        """
        goto_sample = int(self.fs * self.loc_sec)
        page_width_samples = int(self.page_width_secs * self.fs)
        hw = int(page_width_samples / 2)
        s0 = limit_sample_check(goto_sample - hw, self.signals)
        s1 = limit_sample_check(goto_sample + hw, self.signals)
        window_samples = s1 - s0
        if window_samples != self.page_width_seconds * self.fs:
            # dont update
            return None

        signal_view = self.signals[:, s0:s1]
        inmontage_view = np.dot(self.current_montage_instance.V.data, signal_view)

        data = inmontage_view[self.ch_start : self.ch_stop, :]  # note transposed

        numRows = inmontage_view.shape[0]
        ########## do filtering here ############
        # start primative filtering
        if self.current_notch_filter:
            for ii in range(numRows):
                data[ii, :] = self.current_notch_filter(data[ii, :])

        if self.current_hp_filter:
            for ii in range(numRows):
                data[ii, :] = self.current_hp_filter(data[ii, :])
        if self.current_lp_filter:
            for ii in range(numRows):
                data[ii, :] = self.current_lp_filter(data[ii, :])

        ## end filtering
        t = (
            self.page_width_seconds
            * np.arange(window_samples, dtype=float)
            / window_samples
        )
        start_time = s0 / self.fs
        t = t + start_time
        # t = t[:s1-s0]
        ## this is not quite right if ch_start is not 0
        xs = [t for ii in range(numRows)]
        ys = [self.yscale * data[ii, :] + self.ticklocs[ii] for ii in range(numRows)]

        self.data_source.data.update(dict(xs=xs, ys=ys))  # could just use equals?

        # # update seizure box indicator
        # green_box = BoxAnnotation(left=4, right=10, fill_color="green", fill_alpha=0.1)
        # self.fig.add_layout(green_box)

    def stackplot_t(
        self,
        tarray,
        seconds=None,
        start_time=None,
        ylabels=None,
        yscale=1.0,
        topdown=True,
        **kwargs,
    ):
        """
        will plot a stack of traces one above the other assuming
        @tarray is an nd-array like object with format
        tarray.shape =  numSamples, numRows

        @seconds = with of plot in seconds for labeling purposes (optional)
        @start_time is start time in seconds for the plot (optional)

        @ylabels a list of labels for each row ("channel") in marray
        @yscale with increase (mutiply) the signals in each row by this amount
        """
        data = tarray
        numSamples, numRows = tarray.shape
        # data = np.random.randn(numSamples,numRows) # test data
        # data.shape = numSamples, numRows
        if seconds:
            t = seconds * np.arange(numSamples, dtype=float) / numSamples

            if start_time:
                t = t + start_time
                xlm = (start_time, start_time + seconds)
            else:
                xlm = (0, seconds)

        else:
            t = np.arange(numSamples, dtype=float)
            xlm = (0, numSamples)

        ticklocs = []
        if not "plot_width" in kwargs:
            kwargs[
                "plot_width"
            ] = (
                self.ui_plot_width
            )  # 950  # a default width that is wider but can just fit in jupyter, not sure if plot_width is preferred
        if not "plot_height" in kwargs:
            kwargs["plot_height"] = self.ui_plot_height

        if not self.fig:
            # print('creating figure')
            # bokeh.plotting.figure creases a subclass of plot
            fig = bokeh.plotting.figure(
                title=self.title,
                # tools="pan,box_zoom,reset,previewsave,lasso_select,ywheel_zoom",
                # tools="pan,box_zoom,reset,lasso_select,ywheel_zoom",
                tools="",
                **kwargs,
            )  # subclass of Plot that simplifies plot creation
            self.fig = fig

        ## xlim(*xlm)
        # xticks(np.linspace(xlm, 10))
        dmin = data.min()
        dmax = data.max()
        dr = (dmax - dmin) * 0.7  # Crowd them a bit.
        y0 = dmin
        y1 = (numRows - 1) * dr + dmax
        ## ylim(y0, y1)

        ticklocs = [ii * dr for ii in range(numRows)]
        bottom = -dr / 0.7
        top = (numRows - 1) * dr + dr / 0.7
        self.y_range = Range1d(bottom, top)
        self.fig.y_range = self.y_range

        if topdown == True:
            ticklocs.reverse()  # inplace

        # print("ticklocs:", ticklocs)

        offsets = np.zeros((numRows, 2), dtype=float)
        offsets[:, 1] = ticklocs
        self.ticklocs = ticklocs
        self.time = t
        ## segs = []
        # note could also duplicate time axis then use p.multi_line
        # line_glyphs = []
        # for ii in range(numRows):
        #     ## segs.append(np.hstack((t[:, np.newaxis], yscale * data[:, i, np.newaxis])))
        #     line_glyphs.append(
        #         fig.line(t[:],yscale * data[:, ii] + offsets[ii, 1] ) # adds line glyphs to figure
        #     )

        #     # print("segs[-1].shape:", segs[-1].shape)
        #     ##ticklocs.append(i * dr)
        # self.line_glyphs = line_glyphs

        ########## do filtering here ############
        # start primative filtering
        # remember we are in the stackplot_t so channels and samples are flipped -- !!! eliminate this junk
        if self.current_notch_filter:
            for ii in range(numRows):
                data[ii, :] = self.current_notch_filter(data[ii, :])

        if self.current_hp_filter:
            # print("doing filtering")
            for ii in range(numRows):
                data[:, ii] = self.current_hp_filter(data[:, ii])

        if self.current_lp_filter:
            for ii in range(numRows):
                data[ii, :] = self.current_lp_filter(data[ii, :])

        ## end filtering

        ## instead build a data_dict and use datasource with multi_line
        xs = [t for ii in range(numRows)]
        ys = [yscale * data[:, ii] + ticklocs[ii] for ii in range(numRows)]

        self.multi_line_glyph = self.fig.multi_line(
            xs=xs, ys=ys
        )  # , line_color='firebrick')
        self.data_source = self.multi_line_glyph.data_source

        # set the yticks to use axes coords on the y axis
        if not ylabels:
            ylabels = ["%d" % ii for ii in range(numRows)]
        ylabel_dict = dict(zip(ticklocs, ylabels))
        # print('ylabel_dict:', ylabel_dict)
        self.fig.yaxis.ticker = FixedTicker(
            ticks=ticklocs
        )  # can also short cut to give list directly
        self.fig.yaxis.formatter = FuncTickFormatter(
            code="""
            var labels = %s;
            return labels[tick];
        """
            % ylabel_dict
        )
        ## ax.set_yticklabels(ylabels)

        ## xlabel('time (s)')

        return self.fig

    def update_plot_after_montage_change(self):

        self.fig.title.text = self.title
        goto_sample = int(self.fs * self.loc_sec)
        page_width_samples = int(self.page_width_secs * self.fs)

        hw = half_width_epoch_sample = int(page_width_samples / 2)
        s0 = limit_sample_check(goto_sample - hw, self.signals)
        s1 = limit_sample_check(goto_sample + hw, self.signals)

        window_samples = s1 - s0
        signal_view = self.signals[:, s0:s1]
        inmontage_view = np.dot(self.current_montage_instance.V.data, signal_view)
        self.ch_start = 0
        self.ch_stop = inmontage_view.shape[0]

        numRows = inmontage_view.shape[0]  # ???
        # print('numRows: ', numRows)

        data = inmontage_view[self.ch_start : self.ch_stop, :]  # note transposed
        # really just need to reset the labels

        ticklocs = []

        ## xlim(*xlm)
        # xticks(np.linspace(xlm, 10))
        
        dmin = data.min()
        dmax = data.max()
        dr = (dmax - dmin) * 0.7  # Crowd them a bit.
        y0 = dmin
        y1 = (numRows - 1) * dr + dmax
        ## ylim(y0, y1)

        ticklocs = [ii * dr for ii in range(numRows)]
        ticklocs.reverse()  # inplace
        bottom = -dr / 0.7
        top = (numRows - 1) * dr + dr / 0.7
        self.y_range.start = bottom
        self.y_range.end = top
        # self.fig.y_range = Range1d(bottom, top)

        # print("ticklocs:", ticklocs)

        offsets = np.zeros((numRows, 2), dtype=float)
        offsets[:, 1] = ticklocs
        self.ticklocs = ticklocs
        # self.time = t

        ylabels = self.current_montage_instance.montage_labels
        ylabel_dict = dict(zip(ticklocs, ylabels))
        # print('ylabel_dict:', ylabel_dict)
        self.fig.yaxis.ticker = FixedTicker(
            ticks=ticklocs
        )  # can also short cut to give list directly
        self.fig.yaxis.formatter = FuncTickFormatter(
            code="""
            var labels = %s;
            return labels[tick];
        """
            % ylabel_dict
        )

        ## experiment with clearing the data source
        # self.data_source.data.clear() # vs .update() ???

    def stackplot(
        self,
        marray,
        seconds=None,
        start_time=None,
        ylabels=None,
        yscale=1.0,
        topdown=True,
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
        """
        tarray = np.transpose(marray)
        return self.stackplot_t(
            tarray,
            seconds=seconds,
            start_time=start_time,
            ylabels=ylabels,
            yscale=yscale,
            topdown=True,
            **kwargs,
        )

    def show_epoch_centered(
        self,
        signals,
        goto_sec,
        page_width_sec,
        chstart,
        chstop,
        fs,
        ylabels=None,
        yscale=1.0,
    ):
        """
        @signals array-like object with signals[ch_num, sample_num]
        @goto_sec where to go in the signal to show the feature
        @page_width_sec length of the window to show in secs
        @chstart   which channel to start
        @chstop    which channel to end
        @labels_by_channel
        @yscale
        @fs sample frequency (num samples per second)
        """

        goto_sample = int(fs * goto_sec)
        hw = half_width_epoch_sample = int(page_width_sec * fs / 2)

        # plot epochs of width page_width_sec centered on (multiples in DE)
        ch0, ch1 = chstart, chstop

        ptepoch = int(page_width_sec * fs)

        s0 = limit_sample_check(goto_sample - hw, signals)
        s1 = limit_sample_check(goto_sample + hw, signals)
        duration = (s1 - s0) / fs
        start_time_sec = s0 / fs

        return self.stackplot(
            signals[ch0:ch1, s0:s1],
            start_time=start_time_sec,
            seconds=duration,
            ylabels=ylabels[ch0:ch1],
            yscale=yscale,
        )

    def show_montage_centered(
        self,
        signals,
        goto_sec,
        page_width_sec,
        chstart,
        chstop,
        fs,
        ylabels=None,
        yscale=1.0,
        montage=None,
        topdown=True,
        **kwargs,
    ):
        """
        plot an eeg segment using current montage, center the plot at @goto_sec
        with @page_width_sec shown

        @signals array-like object with signals[ch_num, sample_num]

        @goto_sec where to go in the signal to show the feature
        @page_width_sec length of the window to show in secs
        @chstart   which channel to start
        @chstop    which channel to end

        @fs sample frequency (num samples per second)

        @ylabels a list of labels for each row ("channel") in marray
        @yscale with increase (mutiply) the signals in each row by this amount
        @montage instance 

        """

        goto_sample = int(fs * goto_sec)
        hw = half_width_epoch_sample = int(page_width_sec * fs / 2)

        # plot epochs of width page_width_sec centered on (multiples in DE)
        ch0, ch1 = chstart, chstop

        ptepoch = int(page_width_sec * fs)

        s0 = limit_sample_check(goto_sample - hw, signals)
        s1 = limit_sample_check(goto_sample + hw, signals)
        duration_sec = (s1 - s0) / fs
        start_time_sec = s0 / fs

        # signals[ch0:ch1, s0:s1]
        signal_view = signals[:, s0:s1]
        inmontage_view = np.dot(montage.V.data, signal_view)
        rlabels = montage.montage_labels
        # topdown = True

        # return self.stackplot(
        #     signals[ch0:ch1, s0:s1],
        #     start_time=start_time_sec,
        #     seconds=duration_sec,
        #     ylabels=ylabels[ch0:ch1],
        #     yscale=yscale)
        ### to here start stackplot_t
        # self.stackplot_t(
        #     tarray,
        #     seconds=seconds,
        #     start_time=start_time,
        #     ylabels=ylabels,
        #     yscale=yscale,
        #     topdown=True,
        #     **kwargs)

        data = inmontage_view[chstart:chstop, :]
        numRows, numSamples = data.shape
        # data = np.random.randn(numSamples,numRows) # test data
        # data.shape =  numRows, numSamples

        t = duration_sec * np.arange(numSamples, dtype=float) / numSamples

        t = t + start_time_sec  # shift over
        xlm = (start_time_sec, start_time_sec + duration_sec)

        ticklocs = []
        if not "plot_width" in kwargs:
            kwargs[
                "plot_width"
            ] = (
                self.ui_plot_width
            )  # 950  # a default width that is wider but can just fit in jupyter, not sure if plot_width is preferred
        if not "plot_height" in kwargs:
            kwargs["plot_height"] = self.ui_plot_height

        if not self.fig:
            # print('creating figure')
            fig = bokeh.plotting.figure(
                title=self.title,
                # tools="pan,box_zoom,reset,previewsave,lasso_select,ywheel_zoom",
                # tools="pan,box_zoom,reset,lasso_select,ywheel_zoom",
                tools="",  # crosshair
                **kwargs,
            )  # subclass of Plot that simplifies plot creation
            self.fig = fig

        ## xlim(*xlm)
        # xticks(np.linspace(xlm, 10))
        dmin = data.min()
        dmax = data.max()
        dr = (dmax - dmin) * 0.7  # Crowd them a bit.
        y0 = dmin
        y1 = (numRows - 1) * dr + dmax
        ## ylim(y0, y1)

        ticklocs = [ii * dr for ii in range(numRows)]
        bottom = -dr / 0.7
        top = (numRows - 1) * dr + dr / 0.7
        self.y_range = Range1d(bottom, top)
        self.fig.y_range = self.y_range

        if topdown == True:
            ticklocs.reverse()  # inplace

        # print("ticklocs:", ticklocs)

        offsets = np.zeros((numRows, 2), dtype=float)
        offsets[:, 1] = ticklocs
        self.ticklocs = ticklocs
        self.time = t
        ## segs = []
        # note could also duplicate time axis then use p.multi_line
        # line_glyphs = []
        # for ii in range(numRows):
        #     ## segs.append(np.hstack((t[:, np.newaxis], yscale * data[:, i, np.newaxis])))
        #     line_glyphs.append(
        #         fig.line(t[:],yscale * data[:, ii] + offsets[ii, 1] ) # adds line glyphs to figure
        #     )

        #     # print("segs[-1].shape:", segs[-1].shape)
        #     ##ticklocs.append(i * dr)
        # self.line_glyphs = line_glyphs

        ########## do filtering here ############
        # start primative filtering
        # remember we are in the stackplot_t so channels and samples are flipped -- !!! eliminate this junk
        if self.current_notch_filter:
            for ii in range(numRows):
                data[ii, :] = self.current_notch_filter(data[ii, :])

        if self.current_hp_filter:
            # print("doing filtering")
            for ii in range(numRows):
                data[ii, :] = self.current_hp_filter(data[ii, :])

        if self.current_lp_filter:
            for ii in range(numRows):
                data[ii, :] = self.current_lp_filter(data[ii, :])

        ## end filtering

        ## instead build a data_dict and use datasource with multi_line
        xs = [t for ii in range(numRows)]
        ys = [yscale * data[ii, :] + ticklocs[ii] for ii in range(numRows)]

        self.multi_line_glyph = self.fig.multi_line(
            xs=xs, ys=ys
        )  # , line_color='firebrick')
        self.data_source = self.multi_line_glyph.data_source

        # set the yticks to use axes coords on the y axis
        if not ylabels:
            ylabels = ["%d" % ii for ii in range(numRows)]
        ylabel_dict = dict(zip(ticklocs, ylabels))
        # print('ylabel_dict:', ylabel_dict)
        self.fig.yaxis.ticker = FixedTicker(
            ticks=ticklocs
        )  # can also short cut to give list directly
        self.fig.yaxis.formatter = FuncTickFormatter(
            code="""
            var labels = %s;
            return labels[tick];
        """
            % ylabel_dict
        )
        return self.fig

        # return self.stackplot(
        #     inmontage_view[ch0:ch1,:],
        #     start_time=start_time_sec,
        #     seconds=duration_sec,
        #     ylabels=rlabels,
        #     yscale=yscale,
        #     topdown=topdown)

    def register_top_bar_ui(self):

        self.ui_hospital_dropdown = Select(
            options=["Stanford","Temple"],
            value="Temple",
            title="Hospital:",
        )

        self.ui_filename_dropdown = Select(
            options=self.eeghdf_file_names,
            value=self.eeghdf_file_names[0],
            title="File Name:",
        )

        def on_hospital_dropdown_change(attr, oldvalue, newvalue, parent=self):
            if newvalue == "Temple":
                self.tuh = True
                self.eeghdf_file_names = self.tuh_file_names
                self.eeghdf_files = self.tuh_files
            else:
                self.tuh = False
                self.eeghdf_file_names = self.stanford_file_names
                self.eeghdf_files = self.stanford_files
            
            self.ui_filename_dropdown.options = self.eeghdf_file_names
            self.ui_filename_dropdown.value = self.eeghdf_file_names[0]


        def on_filename_dropdown_change(attr, oldvalue, newvalue, parent=self):
            new_file_index = self.eeghdf_file_names.index(newvalue)
            self.eeghdf_file = self.eeghdf_files[new_file_index]
            self.update_eeghdf_file(
                self.eeghdf_file,
                self.current_montage_instance.name,
                self.montage_options,
            )
            self.loc_sec = int(self.page_width_secs/2)
            self.update_plot_after_montage_change()
            self.update()
            self.filename_signal.emit(filename=newvalue)

        self.ui_hospital_dropdown.on_change("value", on_hospital_dropdown_change)
        self.ui_filename_dropdown.on_change("value", on_filename_dropdown_change)

        # mlayout = ipywidgets.Layout()
        # mlayout.width = "15em"
        self.ui_montage_dropdown = Select(
            # options={'One': 1, 'Two': 2, 'Three': 3},
            options=list(self.montage_options.keys()),  # or .montage_optins.keys()
            value=str(self.current_montage_instance.name),
            title="Montage:",
            # layout=mlayout, # set width to "15em"
        )

        def on_dropdown_change(attr, oldvalue, newvalue, parent=self):
            # print(
            #     f"on_dropdown_change: {repr(attr)}, {repr(oldvalue)}, {repr(newvalue)}, {parent}"
            # )

            parent.update_montage(newvalue)
            parent.update_plot_after_montage_change()
            parent.update()

        self.ui_montage_dropdown.on_change("value", on_dropdown_change)

        # flayout = ipywidgets.Layout()
        # flayout.width = "12em"
        self.ui_low_freq_filter_dropdown = Select(
            # options = ['None', '0.1 Hz', '0.3 Hz', '1 Hz', '5 Hz', '15 Hz',
            #           '30 Hz', '50 Hz', '100 Hz', '150Hz'],
            options=list(self._highpass_cache.keys()),
            value="0.3 Hz",
            title="LF",
            max_width=150,  # only problem is that I suspect this is pixels, maybe use panel?css
            # layout=flayout, # see https://panel.holoviz.org/user_guide/Customization.html
        )

        def lf_dropdown_on_change(attr, oldvalue, newvalue, parent=self):
            # print(
            #     f"on_dropdown_change: {repr(attr)}, {repr(oldvalue)}, {repr(newvalue)}, {parent}"
            # )
            parent.current_hp_filter = parent._highpass_cache[newvalue]
            parent.update()  #

        self.ui_low_freq_filter_dropdown.on_change("value", lf_dropdown_on_change)

        self.ui_high_freq_filter_dropdown = Select(
            # options = ['None', '15 Hz', '30 Hz', '50 Hz', '70Hz', '100 Hz', '150Hz', '300 Hz'],
            options=list(self._lowpass_cache.keys()),
            value="None",
            title="HF",
            max_width=150,
            # layout=flayout,
        )

        def hf_dropdown_on_change(attr, oldvalue, newvalue, parent=self):
            # print(
            #     f"on_dropdown_change: {repr(attr)}, {repr(oldvalue)}, {repr(newvalue)}, {parent}"
            # )
            # if change["name"] == "value":  # the value changed
            #    if change["new"] != change["old"]:
            #        # print('*** should change the filter to %s from %s***' % (change['new'], change['old']))
            self.current_lp_filter = self._lowpass_cache[newvalue]
            self.update()  #

        self.ui_high_freq_filter_dropdown.on_change("value", hf_dropdown_on_change)

        self.ui_notch_option = CheckboxGroup(
            labels=["60Hz Notch"], active=[0]
            # , "50Hz Notch"], max_width=100,  # disabled=False
        )

        def notch_change(newvalue, parent=self):
            # print(f"on_dropdown_change: {repr(newvalue)}, {parent}")
            if newvalue == [0]:
                self.current_notch_filter = self._notch_filter
            elif newvalue == []:
                self.current_notch_filter = None
            self.update()

        self.ui_notch_option.on_click(notch_change)
        self.ui_gain_bounded_float = pn.widgets.Spinner(
            name="gain",
            value=1.0,
            step=0.1,
            start=0.01,
            end=100.0,
            min_width=50,
            max_width=80,
            width_policy="fit",
        )
        # self.ui_gain_bounded_float = Spinner(
        #     value=1.0,
        #     # min=0.001,
        #     # max=1000.0,
        #     step=0.1,  # Interval(interval_type: (Int, Float), start, end, default=None, help=None)
        #     # page_step_multiplier=2.0, # may be supported in bokeh 2.2
        #     title="gain",
        #     # value_throtted=(float|int)
        #     # disabled=False,
        #     # continuous_update=False,  # only trigger when done
        #     # layout=flayout,
        #     width=100,
        # )

        def ui_gain_on_change(attr, oldvalue, newvalue, parent=self):
            # print(
            #     f"ui_gain_on_change: {repr(oldvalue)},\n {repr(newvalue)}, {repr(type(newvalue))},{parent}"
            # )

            self.yscale = float(newvalue)
            self.update()

        def ui_gain_watcher(ev, parent=self):
            "guess how to write a call back for a param watch "
            # print(repr(ev), repr(ev.new))
            # print(f"updating {self.yscale} -> {ev.new}")
            self.yscale = float(ev.new)
            self.update()

        self.ui_gain_bounded_float.param.watch(
            ui_gain_watcher, ["value"], onlychanged=True
        )  # (callback, ['options','value'], onlychanged=False)
        # self.ui_gain_bounded_float.on_change("value", ui_gain_on_change)

        # self.top_bar_layout = bokeh.layouts.row(
        self.top_bar_layout = pn.Row(
            self.ui_hospital_dropdown,
            self.ui_filename_dropdown,
            self.ui_montage_dropdown,
            self.ui_low_freq_filter_dropdown,
            self.ui_high_freq_filter_dropdown,
            self.ui_gain_bounded_float,
            self.ui_notch_option,
        )
        return self.top_bar_layout

    def _limit_time_check(self, candidate):
        hw = int(self.page_width_secs / 2)
        if candidate > self.eeghdf_file.duration_seconds - hw:
            return float(self.eeghdf_file.duration_seconds - hw)
        if candidate < hw:
            return float(hw)
        return candidate

    def register_bottom_bar_ui(self):
        # self.ui_buttonf = ipywidgets.Button(description="go forward 10s")
        BUTTON_WIDTH = 150
        self.ui_buttonf = Button(label="go forward 10s", width=BUTTON_WIDTH)
        # self.ui_buttonback = ipywidgets.Button(description="go backward 10s")
        self.ui_buttonback = Button(label="go backward 10s", width=BUTTON_WIDTH)
        # self.ui_buttonf1 = ipywidgets.Button(description="forward 1 s")
        self.ui_buttonf1 = Button(label="forward 1 s", width=BUTTON_WIDTH)
        # self.ui_buttonback1 = ipywidgets.Button(description="back 1 s")
        self.ui_buttonback1 = Button(label="back 1 s", width=BUTTON_WIDTH)
        # could put goto input here

        def go_forward(b, parent=self):
            old_loc = self.loc_sec
            self.loc_sec = self._limit_time_check(self.loc_sec + 10)
            self.move_signal.emit(move_sec=self.loc_sec - old_loc)
            self.update()

        self.ui_buttonf.on_click(go_forward)

        def go_backward(b):
            old_loc = self.loc_sec
            self.loc_sec = self._limit_time_check(self.loc_sec - 10)
            self.move_signal.emit(move_sec=self.loc_sec - old_loc)
            self.update()

        self.ui_buttonback.on_click(go_backward)

        def go_forward1(b, parent=self):
            old_loc = self.loc_sec
            self.loc_sec = self._limit_time_check(self.loc_sec + 1)
            self.move_signal.emit(move_sec=self.loc_sec - old_loc)
            self.update()

        self.ui_buttonf1.on_click(go_forward1)

        def go_backward1(b, parent=self):
            old_loc = self.loc_sec
            self.loc_sec = self._limit_time_check(self.loc_sec - 1)
            self.move_signal.emit(move_sec=self.loc_sec - old_loc)
            self.update()

        self.ui_buttonback1.on_click(go_backward1)

        # self.ui_current_location = FloatInput...  # keep in sync with jslink?
        def go_to_handler(attr, oldvalue, newvalue, parent=self):
            # print("change:", change)
            self.loc_sec = self._limit_time_check(float(newvalue))
            self.update()

        self.ui_bottom_bar_layout = bokeh.layouts.row(
            self.ui_buttonback, self.ui_buttonf, self.ui_buttonback1, self.ui_buttonf1,
        )
        return self.ui_bottom_bar_layout
        # print('displayed buttons')

    def update_montage(self, montage_name):
        Mv = self.montage_options[montage_name]
        new_montage = Mv(self.ref_labels)
        self.current_montage_instance = new_montage
        self.ch_start = 0
        self.ch_stop = new_montage.shape[0]
        self.update_title()
        # self.fig = None # this does not work


# class Eegbrowser:
#     def __init__(self, eegfile, page_width_seconds=10.0, start_sec=0,
#                  montage='double banana'):  # may want to change default to 'trace' or 'raw'
#         """
#         @eegfile is an eeghdf.Eeghdf() class instance representing the file
#         @montage is either a string in the standard list or a montageview factory"""

#         self.eeghdf_file = eegfile
#         self.page_width_seconds = page_width_seconds
#         self.start_sec = start_sec #!! not used yet

#         if montage in montageview.MONTAGE_BUILTINS:
#             self.cur_montageview_factory = montageview.MONTAGE_BUILTINS[montage]
#             self.montage_options = montageview.MONTAGE_BUILTINS
#         else:
#             self.montage_options = montageview.MONTAGE_BUILTINS.copy() # ordered dict
#             self.montage_options[montage.name] = montage
#             self.cur_montageview_factory = montage

#         shortlabels = eegfile.shortcut_elabels
#         self.current_montage_instance = self.cur_montageview_factory(shortlabels)

#         self.eegplot = stackplot_bokeh.IpyHdfEegPlot2(self.eeghdf_file,
#                                                       page_width_seconds=page_width_seconds,
#                                                       montage_class=self.cur_montageview_factory,
#                                                       montage_options=self.montage_options)

#         self.eegplot.show()


class EegBrowser(EeghdfBrowser):
    """
    take an minimal eeg file and allow for browsing of the EEG signal



    """

    def __init__(
        self,
        min_eeg,
        page_width_seconds,
        montage=None,
        montage_options=OrderedDict(),
        start_seconds=0,
        **kwargs,
    ):
        # def __init__(self, eeghdf_file, page_width_seconds=10.0, start_seconds=-1,
        #             montage='trace', montage_options={}, **kwargs):
        """
        @min_eeg file is a minimal_eeg_record class instance representing the file

        @montage is either a string in the standard list or a montageview factory
        @eeghdf_file - an eeghdf.Eeeghdf instance
        @page_width_seconds = how big to make the view in seconds
        @montage - montageview (class factory) OR a string that identifies a default montage (may want to change this to a factory function 
        @start_seconds - center view on this point in time

        BTW 'trace' is what NK calls its 'as recorded' montage - might be better to call 'raw'
        """

        self._signals = min_eeg.signals
        num_channels, num_samples = self._signals.shape

        # self.electrode_labels = [str(ss,'ascii') for ss in blabels]
        self.electrode_labels = min_eeg.electrode_labels
        if not self.electrode_labels:
            self.electrode_labels = [str(ii) for ii in range(num_channels)]
        self.ref_labels = montageview.standard2shortname(self.electrode_labels)

        # if montage in montageview.MONTAGE_BUILTINS:
        #     self.cur_montageview_factory = montageview.MONTAGE_BUILTINS[montage]
        #     self.montage_options = montageview.MONTAGE_BUILTINS
        # else:
        #     self.montage_options = montageview.MONTAGE_BUILTINS.copy() # ordered dict
        #     self.montage_options[montage.name] = montage
        #     self.cur_montageview_factory = montage

        if min_eeg.montage_options:
            # not sure if update works here
            montage_options.update(min_eeg.montage_options)
        if not montage_options:
            # then use builtins and/or ones in the file
            if self.tuh:
                montage_options = montage_derivations_edf_simplified.EDF_SIMPLIFIED_MONTAGE_BUILTINS.copy()
            else:
                montage_options = montageview.MONTAGE_BUILTINS.copy()
            # print('starting build of montage options', montage_options)

            # montage_options = eeghdf_file.get_montages()

        # defines self.current_montage_instance
        if type(montage) == str:  # then we have some work to do
            if montage in montage_options:

                self.current_montage_instance = montage_options[montage](
                    self.ref_labels
                )
            else:
                raise Exception("unrecognized montage: %s" % montage)
        else:
            if montage:  # is a class
                self.current_montage_instance = montage(self.ref_labels)
                montage_options[self.current_montage_instance.name] = montage
            else:  # use default

                self.current_montage_instance = montage_options[0](self.ref_labels)

        assert self.current_montage_instance
        self.montage_options = montage_options  # save the montage_options for later

        # display related
        self.page_width_seconds = page_width_seconds

        ## bokeh related

        self.page_width_secs = page_width_seconds
        if start_seconds < 0:
            self.loc_sec = (
                page_width_seconds / 2.0
            )  # default location in file by default at start if possible
        else:
            self.loc_sec = start_seconds

        # self.init_kwargs = kwargs

        if "yscale" in kwargs:
            self.yscale = kwargs["yscale"]
        else:
            self.yscale = 3.0

        self.bk_handle = None
        self.fig = None
        self.fs = rec.attrs["sample_frequency"]

        self.update_title()

        self.num_rows, self.num_samples = self.signals.shape
        self.line_glyphs = []  # not used?
        self.multi_line_glyph = None

        self.ch_start = 0
        self.ch_stop = self.current_montage_instance.shape[0]

        ####### set up filter cache: first try
        self.current_hp_filter = None
        self.current_lp_filter = None
        self._highpass_cache = OrderedDict()
        ff = esfilters.fir_highpass_remez_zerolag(
            fs=self.fs, cutoff_freq=1.0, transition_width=0.5, numtaps=int(2 * self.fs)
        )
        self._highpass_cache["None"] = None
        self._highpass_cache["1 Hz"] = ff
        ff = esfilters.fir_highpass_remez_zerolag(
            fs=self.fs,
            cutoff_freq=5.0,
            transition_width=2.0,
            numtaps=int(0.2 * self.fs),
        )
        self._highpass_cache["5 Hz"] = ff

        firstkey = "1 Hz"  # list(self._highpass_cache.keys())[0]
        self.current_hp_filter = self._highpass_cache[firstkey]

        self._lowpass_cache = OrderedDict()

    @property
    def signals(self):
        return self.eeghdf_file.phys_signals


# write a class with a plot at the bottom that scrolls either stays fixed or scrolls along with the eeg
# class EeghdfBrowserWithPlot(EeghdfBrowser):
#    pass

# %%
