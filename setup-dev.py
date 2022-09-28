# -*- coding: utf-8 -*-
from __future__ import division, print_function, absolute_import

import setuptools  # required to allow for use of python setup.py develop, may also be important for cython/compiling if it is used

from distutils.core import setup



setup(
    name="eegvis",
    version="0.3.0",
    description="""eeg visualization functions""",
    author="""Chris Lee-Messer""",
    url="https://github.com/eegml/eegvis",
    # url="http://bitbucket.org/cleemesser/eegvis",
    # download_url="http://bitbucket.org/cleemesser/eegvis/downloads",
    classifiers=["Topic :: Science :: EEG"],
    packages=["eegvis"],
    install_requires = [
        'xarray','ipywidgets >= 7.0', 'bokeh>=0.12.16', 'matplotlib',
        'eeghdf'],
    # package_data={}
    # data_files=[],
    # scripts = [],
)
