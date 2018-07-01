# -*- encoding: utf-8 -*-
from __future__ import print_function, division, unicode_literals
import functools
import os.path as path
from pprint import pprint

import pandas as pd
import numpy as np
import h5py


import bokeh.plotting as bplt
import bokeh.models
import bokeh.models.widgets
import bokeh.layouts as layouts  # column, row, ?grid
# import bokeh.models.widgets as bmw
# import bokeh.models.sources as bms
from bokeh.models import FuncTickFormatter
from bokeh.models.tickers import FixedTicker


# from bokeh.models import Button
from bokeh.palettes import RdYlBu3
from bokeh.plotting import figure, curdoc

# stuff to define new widget 
from bokeh.models import LayoutDOM
from bokeh.util.compiler import TypeScript
from bokeh.core.properties import Int # String, Instance 

import eeghdf
import eegvis.nb_eegview

ARCHIVEDIR = r'../../eeg-hdfstorage/data/'
#EEGFILE = ARCHIVEDIR + 'spasms.eeghdf'
EEGFILE = ARCHIVEDIR + 'absence_epilepsy.eeghdf'
hf = eeghdf.Eeghdf(EEGFILE)

eegbrow = eegvis.nb_eegview.EeghdfBrowser(hf, montage='double banana', start_seconds=1385, plot_width=1800, plot_height=800)
## set up some synthetic data

# N = 200
# x = np.linspace(0, 4*np.pi, N)
# y = np.sin(x)
# source = bokeh.models.ColumnDataSource(data=dict(x=x, y=y))

## 

DOC = curdoc() # hold on to an instance of current doc in case need multithreads
SIZING_MODE =  'fixed' # 'scale_width' also an option, 'scale_both', 'scale_width', 'scale_height', 'stretch_both'



#placeholder figure
mainfig = figure(tools="previewsave",  width=600, height=400)

#desc = bokeh.models.Div(text=open(path.join(path.dirname(__file__), "description.html")).read(), width=800)
desc = bokeh.models.Div(text="""Some placeholder text""")

### layout ###
# there are unicode labels which would look better
MVT_BWIDTH = 50
# note am setting button width as same as widget box (wbox50) to make one abut the next
bBackward10 = bokeh.models.widgets.Button(label='<<', width=MVT_BWIDTH)
bBackward1 = bokeh.models.widgets.Button(label='\u25C0', width=MVT_BWIDTH)  # <-
bForward10 = bokeh.models.widgets.Button(label='>>', width=MVT_BWIDTH)
bForward1 = bokeh.models.widgets.Button(label='\u25B6', width=MVT_BWIDTH) # -> or '\u279F'

bottomrowctrls = [bBackward10,bBackward1,bForward1, bForward10]
toprowctrls = [bokeh.models.widgets.Select(title='Montage',value='trace', options=['trace', 'db','tcp']),
               bokeh.models.widgets.Select(title='Sensitivity',value='7uV/div', options=['1uV/div', '3uV/div','7uV/div','10uV/div']),
               bokeh.models.widgets.Select(title='LF',value='0.3Hz', options=['None', '0.1Hz','0.3Hz','1Hz','5Hz']),
               bokeh.models.widgets.Select(title='HF',value='70Hz', options=['None', '15Hz','30Hz','50Hz','70Hz']),

]
                 

#for control in controls:
#    control.on_change('value', lambda attr, old, new: update())



#inputs = widgetbox(*controls[:3], sizing_mode=SIZING_MODE)
wbox50 = functools.partial(layouts.widgetbox, sizing_mode=SIZING_MODE, width=MVT_BWIDTH)
wbox20 = functools.partial(layouts.widgetbox, sizing_mode=SIZING_MODE, width=150)
toprow = layouts.row(*map(wbox20, toprowctrls))
# toprow = layouts.row(wbox(layouts.row(children=toprowctrls)))
print(toprow)
bottomrow = layouts.row(*map(wbox50, bottomrowctrls))

L = layouts.layout([
    [desc],
    [toprow],
    [mainfig],
    [bottomrow]
    ], sizing_mode=SIZING_MODE)

DOC.add_root(L)
