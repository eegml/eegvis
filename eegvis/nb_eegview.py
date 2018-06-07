# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import montageview
from . import stackplot_bokeh
import ipywidgets

# these are montageview factor functions which require a spcific channel label list
MONTAGE_BUILTINS = { 
    'tcp': montageview.TCPMontageView,
    'db' : montageview.DoubleBananaMontageView,
    'laplacian' : montageview.LaplacianMontageView }

class Eegbrowser:
    def __init__(self, eegfile, page_width_seconds=10.0, start_sec=0,
                 montage='db'):
        """
        @eegfile is an eeghdf.Eeghdf() class instance representing the file
        @montage is either a string in the standard list or a montageview factory"""

        self.eeghdf_file = eegfile
        self.page_width_seconds = page_width_seconds
        self.start_sec = start_sec #!! not used yet
        
        if montage in MONTAGE_BUILTINS:
            self.cur_montageview_factory = MONTAGE_BUILTINS[montage]
            self.montage_options = MONTAGE_BUILTINS
        else:
            self.montage_options = MONTAGE_BUILTINS
            self.montage_options[montage.name] = montage
            self.cur_montageview_factory = montage

        shortlabels = eegfile.shortcut_elabels
        self.current_montageview = self.cur_montageview_factory(shortlabels)

        self.eegplot = stackplot_bokeh.IpyHdfEegPlot2(self.eeghdf_file.hdf,
                                                      page_width_seconds=page_width_seconds,
                                                      montage=self.current_montageview)
        
        self.eegplot.show()            
                                                 
    def set_montage(self,newmontage_key):
        pass
