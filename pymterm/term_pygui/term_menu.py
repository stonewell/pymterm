from GUI.GStdMenus import build_menus, \
    fundamental_cmds, help_cmds, pref_cmds, file_cmds, print_cmds, edit_cmds

file_cmds += 'new_window_cmd'
file_cmds += 'open_session_cmd'

_file_menu_items = [
    ("New Tab/^T",   'new_cmd'),
    ("New Window/^N",  'new_window_cmd'),
    ("Close/^W",    'close_cmd'),
    "-",
    ([], 'open_session_cmd'),
    "-",
    ("Exit/Q",   'quit_cmd'),
]

_edit_menu_items = [
    ("Copy/^C",       'copy_cmd'),
    ("Paste/^V",      'paste_cmd'),
    ("Clear",        'clear_cmd'),
]

_help_menu_items = [
    ("About <app>",    'about_cmd'),
]

#------------------------------------------------------------------------------

def basic_menus(substitutions = {}, include = None, exclude = None):
    return build_menus([
        ("File", _file_menu_items, False),
        ("Edit", _edit_menu_items, False),
        ("Help", _help_menu_items, True),
    ],
    substitutions = substitutions,
    include = include,
    exclude = exclude)
