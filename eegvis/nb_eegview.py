# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
from collections import OrderedDict 

from . import montageview
from . import stackplot_bokeh
import ipywidgets


class Eegbrowser:
    def __init__(self, eegfile, page_width_seconds=10.0, start_sec=0,
                 montage='double banana'):  # may want to change default to 'trace' or 'raw'
        """
        @eegfile is an eeghdf.Eeghdf() class instance representing the file
        @montage is either a string in the standard list or a montageview factory"""

        self.eeghdf_file = eegfile
        self.page_width_seconds = page_width_seconds
        self.start_sec = start_sec #!! not used yet
        
        if montage in montageview.MONTAGE_BUILTINS:
            self.cur_montageview_factory = montageview.MONTAGE_BUILTINS[montage]
            self.montage_options = montageview.MONTAGE_BUILTINS
        else:
            self.montage_options = montageview.MONTAGE_BUILTINS.copy() # ordered dict
            self.montage_options[montage.name] = montage
            self.cur_montageview_factory = montage

        shortlabels = eegfile.shortcut_elabels
        self.current_montageview = self.cur_montageview_factory(shortlabels)

        self.eegplot = stackplot_bokeh.IpyHdfEegPlot2(self.eeghdf_file,
                                                      page_width_seconds=page_width_seconds,
                                                      montage_class=self.cur_montageview_factory,
                                                      montage_options=self.montage_options)
        
        self.eegplot.show()            
                                                 
    def set_montage(self,newmontage_key):
        pass
