
# eegvis
- work in progress to visualize EEG files in python
- currently lots of experimentation - not ready for general consumption
- goal is to provide portion of software infrastructure for EEG analysis

## Scope of Project
- functions to work with matplotlib to visualize EEG
- functions to interactively plot EEGs in the jupyter notebook
- web (bokeh) applications to browse and annotate EEGs

### Status
- currently this is still experimental, but it has a useful eeg browser for the jupyter notebook
- basic filtering added, with notch and low-pass/high-pass filter 

- version 0.2.1 works with bokeh 2.0.2 !

### install
jupyter nbextension enable --py widgetsnbextension  --sys-prefix


### To do
- [x] matplotlib EEG plotting (firstdraft)
- [x] basic [bokeh](bokeh.org) EEG plotting (firstdraft)
- [x] basic montage EEG plotting, (firstdraft)
- [x] simple browsing EEG with bokeh in jupyter (firstdraft)
- [x] first filtering dropdowns added to nb browser tool
- [x] allow kwargs to set plot width and height
- [/] notch and HF filters dropdowns - problem with ringing on current firwin filters
- [ ] need scale/calibration bars
- [ ] catch when current displayed data is not big enough to filter
- [ ] add common avg reference montage (CAR)

- [ ] remove cruft from plotting in various widgets
- [/] bokeh application to browse + annotate EEG, - still experimenting
- [ ] montage parser/loader (priority long-term)
- [ ] keyboard responses, howto?
- [ ] add ability to control scale of each electrode waveform individually
- [ ] rewrite and package
- [ ] publish
- [ ] possible re-write/extend Bokeh for canvas widget
- [x] update to bokeh 1.0.x (now at 2.3)
- [ ] tests for mpl_helpers
- [ ] clearcut examples of using plotting tools with:
  - [ ] numpy arrays
  - [ ] edf EEGs
  - [ ] eeghdf EEGs
  
- [ ] trial implement [panel](https://panel.holoviz.org) based version of browser widget
- [ ] explore low-level implementation of browser widget using bokeh for more control
- [ ] explroe new annotation bokeh controls
- [ ] switch to new packaging for ppa using pyproject.toml and move setup.py to setup-dev.py
- [ ] add tools to mark events in plots and in bokeh



### Other notes
- Note, to respond to keyboard commands in bokeh, probably need an extension:
  see: 
  https://groups.google.com/a/continuum.io/forum/#!searchin/bokeh/keypress/bokeh/XCLqg1nyIgE/CU7lJGcuBgAJ



### Developer Install
currently this is developer only package
```
    git clone https://github.com/eegml/eegvis.git
    cd eegvis
    pip install -e .
```   

### jupyter notebook use
conda install ipywidgets
conda install widgetsnbextension
    
### jupyter lab use
jupyter labextension install jupyterlab_bokeh
jupyter labextension install @jupyter-widgets/jupyterlab-manager
