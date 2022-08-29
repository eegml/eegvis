def wide_notebook():
    """enable classic jupyter notebook to use full width of display"""
    from IPython.core.display import display, HTML
    display(HTML("<style>.container { width:100% !important; }</style>"))
