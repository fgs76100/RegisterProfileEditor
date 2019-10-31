from collections import OrderedDict
from .__version__ import __version__

caption_formatter = "{Module}/{Register}"
register_formatter = "{Offset}({Name})"
block_formatter = "{BaseAddress}({ModuleName})"
loop_formatter = "{Name}_{integer}"
GUI_NAME = "RegisterProfileEditor"

offset_length = 4

new_field = dict(
    MSB=31,
    LSB=0,
    Field='New',
    Access='RW',
    Default='0x0',
    Description=''
)

new_reg = dict(
    Offset='0x0',
    Name='New',
    Description="",
    Loop="1",
    Incr="0x0",
    Fields=[
        new_field.copy()
    ]
)

reserve_field = dict(
    MSB=31,
    LSB=0,
    Field='RESERVED',
    Access='RO',
    Default='0x0',
    Description=''
)

register_columns = OrderedDict([
    ('Offset',  dict(
        width=150,
        type='hex',
        default='0x0'
    )),
    ('Name', dict(
        width=200,
        default='NameNotFound'
    )),
    ('Description', dict(
        width=150,
        # widget='textEdit',
        default=''
    )),
    # ('Loop', dict(
    #     width=50,
    #     default='1',
    #     type='int',
    #     minValue=1,
    #     maxValue=100,
    # )),
    # ('Incr', dict(
    #     width=50,
    #     default='0x0',
    #     type='hex'
    # )),
])

block_columns = OrderedDict([
    ('BaseAddress',  dict(
        default='0x0',
        type='hex',
        display=True
    )),
    ('ModuleName', dict(
        default='New',
        display=True,
    )),
    ('Description', dict(
        display=True,
        widget='textEdit'
    )),
    ('Author', dict(
    )),
    ('Version', dict(
    )),
    ('Revisions', dict(
        widget='textEdit'
    )),

])

register_contextmenu = [
    dict(
        label='Add Analyzer',
        shortcut='A',
        action='addAnalyzer',
        icon='fa.th',
    ),
    dict(
        label='Append copy',
        shortcut='Ctrl+V',
        action='append_copy',
        icon='fa.clipboard',
        buffer=True
    ),
    dict(
        label='Prepend copy',
        shortcut='Ctrl+Shift+P',
        action='prepend_copy',
        icon='fa.clipboard',
        buffer=True
    ),
    dict(
        label='Copy',
        shortcut='Ctrl+C',
        icon='fa.files-o',
        action='copy'
    ),
    dict(
        label='Append new',
        shortcut='Ctrl+N',
        action='append_new',
        icon='fa.file-code-o'
    ),
    dict(
        label='Prepend new',
        shortcut='Ctrl+Shift+N',
        action='prepend_new',
        icon='fa.file-code-o'
    ),
    dict(
        label='Cut',
        shortcut='Ctrl+X',
        action='cut',
        icon='fa.scissors'
    ),

    dict(
        label='Remove',
        shortcut='Ctrl+D',
        action='remove',
        icon='fa.trash-o'
    ),
    dict(
        label='Shift by',
        shortcut='Shift+S',
        action='shiftBy',
        icon='fa.arrows-v'
    )
]

field_contextmenu = [
    dict(
        label='Add Reversed',
        shortcut='Ctrl+Shift+R',
        action='reserved',
        icon='fa.rocket'
    ),
    dict(
        label='Search and Replace',
        shortcut='Ctrl+R',
        action='searchAndReplace',
        icon='fa.search'
    ),
    dict(
        label='Append copy',
        shortcut='Ctrl+V',
        action='append_copy',
        buffer=True,
        icon='fa.clipboard',
    ),
    dict(
        label='Prepend copy',
        shortcut='Ctrl+Shift+V',
        action='prepend_copy',
        icon='fa.clipboard',
        buffer=True
    ),
    dict(
        label='Copy',
        shortcut='Ctrl+C',
        icon='fa.files-o',
        action='copy'
    ),
    dict(
        label='Append new',
        shortcut='Ctrl+N',
        action='append_new',
        icon='fa.file-code-o'
    ),
    dict(
        label='Prepend new',
        shortcut='Ctrl+Shift+N',
        action='prepend_new',
        icon='fa.file-code-o'
    ),
    dict(
        label='Cut',
        shortcut='Ctrl+X',
        action='cut',
        icon='fa.scissors'
    ),
    # dict(
    #     label='Save Table',
    #     shortcut='Ctrl+S',
    #     action='saveTable',
    #     icon='fa.floppy-o'
    # ),
    dict(
        label='Remove',
        shortcut='Ctrl+D',
        action='remove',
        icon='fa.trash-o'
    )
]

field_columns = OrderedDict([
    ("Public", dict(
        width=65,
        widget='list',
        default='Y',
        items=['Y', 'N'],
        drop=True
    )),
    ("MSB", dict(
        width=50,
        require=True,
        type='int',
        minValue=0,
        maxValue=31,
    )),
    ("LSB", dict(
        width=50,
        require=True,
        type='int',
        minValue=0,
        maxValue=31,
    )),
    ("Field", dict(
        width=220,
        widget='lineEdit',
        items=['RESERVED'],
        require=True,
     )),
    ("Access", dict(
        width=80,
        # widget='list',
        items=['RW', 'RO', 'RWAC'],
        require=True,
    )),
    ("Default", dict(
        width=120,
        require=True,
    )),
    ("Testable", dict(
        width=85,
        widget='list',
        default='Y',
        items=['Y', 'N'],
        # belongto='Description'
        drop=True
    )),
    ("Description", dict(
        width=400,
        widget='textEdit',
        resize=True,
        require=False,
     )),
])


menubar_configs = [
    {
        "File": [

            dict(
                text='New Module',
                action='newModule',
                icon='ei.file-new'
            ),

            dict(
                text='Open Files',
                shortcut='Ctrl+F',
                action='openFiles',
                icon='fa.file-o'
            ),

            dict(
                text="Open Directory",
                action="openDir",
                icon='fa.folder-open-o',
            ),
            dict(
                text="Save",
                action="saveAsOne",
                icon='fa.floppy-o',
            ),
            dict(
                text="Save Separately",
                icon='fa.floppy-o',
                sub=[
                    dict(
                        text="As Excel",
                        action="saveExcelSeparately",
                        icon='fa.file-excel-o'
                    ),
                    dict(
                        text="As Json",
                        action="saveJsonSeparately",
                        icon='fa.file-text-o'
                    ),
                ]
            ),
            dict(
                text="Save As HTML",
                action="saveAsHTML",
            ),
            #
            # dict(
            #     text="Save File",
            #     action="saveFile",
            #     icon='fa.folder-open-o',
            # ),

        ]
    },
    {
        "Edit": [
            dict(
                text='Undo',
                shortcut="Ctrl+Z",
                action='undo',
                icon='fa.undo'
            ),
            dict(
                text='Redo',
                shortcut="Ctrl+Shift+Z",
                action='redo',
                icon="fa.repeat"

            ),

        ]
    },
    {
        "Style": [
            dict(
                text='Font',
                # shortcut=None,
                action='selectFont',
                icon='fa.font'
            ),
        ]
    },
    {
        "About": [
            dict(
                text=f"Version: {__version__}",
                icon='fa.key',
                action='doNothing',
            ),
            dict(
                text='Author: Berdych',
                icon='fa.user-secret',
                action='doNothing',
            )
        ]
    }
]











