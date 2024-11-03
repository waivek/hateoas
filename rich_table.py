import rich
import rich.box
from rich.table import Table
from collections import ChainMap

# def print_rich_tuple_rows(rows, headers=[], console=None, padding=1, pad_edge=True):
def print_rich_tuple_rows(rows, headers=[], console=None, **kwargs):
    # rich.Table kwargs {{{
    # *headers (Union[Column, str]): Column headers, either as a string, or :class:`~rich.table.Column` instance.
    # title (Union[str, Text], optional): The title of the table rendered at the top. Defaults to None.
    # caption (Union[str, Text], optional): The table caption rendered below. Defaults to None.
    # width (int, optional): The width in characters of the table, or ``None`` to automatically fit. Defaults to None.
    # min_width (Optional[int], optional): The minimum width of the table, or ``None`` for no minimum. Defaults to None.
    # box (box.Box, optional): One of the constants in box.py used to draw the edges (see :ref:`appendix_box`), or ``None`` for no box lines. Defaults to box.HEAVY_HEAD.
    # safe_box (Optional[bool], optional): Disable box characters that don't display on windows legacy terminal with *raster* fonts. Defaults to True.
    # padding (PaddingDimensions, optional): Padding for cells (top, right, bottom, left). Defaults to (0, 1).
    # collapse_padding (bool, optional): Enable collapsing of padding around cells. Defaults to False.
    # pad_edge (bool, optional): Enable padding of edge cells. Defaults to True.
    # expand (bool, optional): Expand the table to fit the available space if ``True``, otherwise the table width will be auto-calculated. Defaults to False.
    # show_header (bool, optional): Show a header row. Defaults to True.
    # show_footer (bool, optional): Show a footer row. Defaults to False.
    # show_edge (bool, optional): Draw a box around the outside of the table. Defaults to True.
    # show_lines (bool, optional): Draw lines between every row. Defaults to False.
    # leading (int, optional): Number of blank lines between rows (precludes ``show_lines``). Defaults to 0.
    # style (Union[str, Style], optional): Default style for the table. Defaults to "none".
    # row_styles (List[Union, str], optional): Optional list of row styles, if more than one style is given then the styles will alternate. Defaults to None.
    # header_style (Union[str, Style], optional): Style of the header. Defaults to "table.header".
    # footer_style (Union[str, Style], optional): Style of the footer. Defaults to "table.footer".
    # border_style (Union[str, Style], optional): Style of the border. Defaults to None.
    # title_style (Union[str, Style], optional): Style of the title. Defaults to None.
    # caption_style (Union[str, Style], optional): Style of the caption. Defaults to None.
    # title_justify (str, optional): Justify method for title. Defaults to "center".
    # caption_justify (str, optional): Justify method for caption. Defaults to "center".
    # highlight (bool, optional): Highlight cell contents (if str). Defaults to False.
    # }}}

    # if 'pad_edge' not in kwargs:
    #     kwargs['pad_edge'] = False # LIBRARY DEFAULT: True
    # if 'collapse_padding' not in kwargs:
    #     kwargs['collapse_padding'] = True # LIBRARY DEFAULT: False
    # if 'show_header' not in kwargs:
    #     kwargs['show_header'] = False
    # if 'box' not in kwargs:
    #     kwargs['box'] = None
    default_kwargs = {
        'pad_edge': False,        # LIBRARY DEFAULT: True
        'collapse_padding': True, # LIBRARY DEFAULT: False
        'show_header': False,
        'box': None,
    }

    # Use ChainMap to overlay kwargs on top of default_kwargs
    # If a key is in kwargs, it will override the value in default_kwargs
    combined_kwargs = ChainMap(kwargs, default_kwargs)

    if headers:
        table = Table(box=rich.box.ROUNDED)
    else:
        table = Table(**combined_kwargs)
    for column_name in headers:
        table.add_column(column_name)
    for row in rows:
        row = [str(cell) for cell in row]
        table.add_row(*row)
    if not console:
        console = rich.get_console()
    console.print(table)

def print_rich_dict_rows(dicts, console=None):
    # check that all dicts have the same keys {{{
    keys = set(dicts[0].keys())
    for D in dicts:
        if set(D.keys()) != keys:
            raise ValueError("All dicts must have the same keys")
    # }}}
    keys = list(dicts[0].keys()) # we do this so that the order of the keys is consistent
    rows = [ [d[k] for k in keys] for d in dicts ]
    print_rich_tuple_rows(rows, headers=list(keys), console=None)

if __name__ == "__main__":
    data = [
        {"name": "[green bold]Alice[/]", "age": 24},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 26},
    ]
    tuple_data = [(d["name"], d["age"]) for d in data]
    print_rich_tuple_rows(tuple_data)
    print_rich_dict_rows(data)
