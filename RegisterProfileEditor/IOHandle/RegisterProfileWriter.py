import json
import traceback
import os
from PyQt5.QtCore import QRunnable
from .ExcelParser import ProgressSignal
from xlwt import Workbook, easyxf
from collections import OrderedDict
from RegisterProfileEditor.Views.BaseClass import Block


class JsonWriter(QRunnable):
    def __init__(self, blocks: list, filename: str, separately: bool=False):
        super(JsonWriter, self).__init__()
        self.signal = ProgressSignal()
        self.blocks = blocks
        self.filename = filename
        self.separately = separately

    def run(self):
        try:
            if self.separately:
                for block in self.blocks:
                    filename = os.path.join(self.filename, block.block_name+'.json')
                    with open(filename, 'w') as f:
                        json.dump(
                            block.toDict(),
                            f
                        )
                    self.signal.progress.emit(
                        f"# [INFO] {filename} Saved"
                    )
            else:
                blocks = []
                for block in self.blocks:
                    blocks.append(
                        block.toDict()
                    )
                with open(self.filename, 'w') as f:
                    json.dump(
                        blocks,
                        f
                    )
                self.signal.progress.emit(
                    f"# [INFO] {self.filename} Saved"
                )

        except Exception as e:
            self.signal.progress.emit(
                f"# [Error] Save {self.filename} failed\n"+traceback.format_exc()
            )

        finally:
            self.signal.done.emit()


# def preprocessing(df):
#     df.Name = df.Name.str.upper()
#     df.Name = df.Name.str.replace(' ', '')
#     #df[df.Name.str.match(r'^[0-9]')].Name.str.replace
#     # register name cant start with integer
#     df.Name = df.Name.str.replace('^[0-9]', 'n', regex=True)
#     df.Default = df.Default.str.replace('-', '0x0')
#     df.Default = df.Default.str.replace('CONF', '0x0')
#     df.Access = df.Access.str.replace('W1AC', 'WAC')
#     df.Access = df.Access.str.replace('^R{1}$', 'RO', regex=True)
#     df.Access = df.Access.str.replace('^W{1}$', 'WO', regex=True)
#     df.Access = df.Access.str.replace('R/W', 'RW', regex=True)
#     return df


class ProfileWriter:
    def __init__(self, block: Block=None, ip='', base_addr=None, index_info: dict=None):
        self.base_addr = base_addr
        self.workbook = Workbook()
        self.mode = 'mod_' + ip
        self.file = 'file_' + ip
        self.block = block
        self.ip = ip.upper()
        self.has_index = False
        if index_info:
            self.index_info = index_info
            self.has_index = True
            self.index_sheet = self.workbook.add_sheet(sheetname='chip_index', cell_overwrite_ok=True)
            self.index_des = OrderedDict(
                CHIP=self.index_info.get('HEADPAGE', ''),
                HEADPAGE=self.index_info.get('HEADPAGE', ''),
                PREFIX=self.index_info.get('PREFIX', ''),
                PPRANGE="0x100",
                DATA_MUX_FILE=['File list of DATA_MUX (*.xml)'],
                MEMORY_BLOCK='Memory Block of Chip Module Design',
            )
            self.index_blocks = [['NAME', 'OFFSET ADDR', 'NUMBER', 'DESCRIPTION', 'Belong to']]
        if ip != '':
            self.mod_sheet = self.workbook.add_sheet(sheetname=self.mode, cell_overwrite_ok=True)
            self.file_sheet = self.workbook.add_sheet(sheetname=self.file, cell_overwrite_ok=True)
        else:
            self.mod_sheet = None
            self.file_sheet = None
        self.stype = easyxf('align: wrap on')

    def set_ip(self, ip):
        self.mode = 'mod_' + ip
        self.file = 'file_' + ip
        self.ip = ip.upper()
        self.mod_sheet = self.workbook.add_sheet(sheetname=self.mode, cell_overwrite_ok=True)
        self.file_sheet = self.workbook.add_sheet(sheetname=self.file, cell_overwrite_ok=True)

    def set_base_address(self, base_addr):
        self.base_addr = base_addr

    def set_block(self, block: Block):
        self.block = block

    def create_index_blocks(self):
        if not self.has_index:
            return
        index_row = self.create_description(self.index_des, self.index_sheet, real_row=True)
        for block in self.index_blocks:
            for col, value in enumerate(block):
                self.index_sheet.write(index_row, col, value)
            index_row += 1

        revisions = [
            [''],
            ['HISTORY', 'Revision History'],
            ['PUBLIC', 'REV', 'DATE', 'DESCRIPTION', 'AUTHOR'],
            ['Y', 'v0.0.1', self.index_info.get('DATE', ''),
             self.index_info.get('DESCRIPTION', ''),
             self.index_info.get('AUTHOR', '')]
        ]
        for items in revisions:
            for col, item in enumerate(items):
                self.index_sheet.write(index_row, col, item)
            index_row += 1

    def create_mode_sheet(self):
        if self.has_index:
            last_offset = self.block.get_register(-1).offset
            reg_num = int(last_offset, 16)//4+1
            self.index_des['DATA_MUX_FILE'].append(
                self.mode+'.xml'
            )
            self.index_blocks.append(
                [
                    self.block.block_name, self.block.base_address,
                    reg_num, self.block.get('Description'),
                    self.block.block_name
                ]
            )
        mode_des = OrderedDict(
            DATA_MUX='Please provide the following information that will be shown in DATA_MUX Level',
            NAME=self.ip,
            DESCRIPTION='',
            COMMENT='Comment of RTL code',
            REGNUM='',
            AUTHOR='',
            DATE='',
            VERSION='',
            ABSTRACT=self.base_addr,
            HISTORY='',
            REG_FILE=['File list of registers in DATA_MUX (*.xml)', self.file + '.xml'],
        )
        self.create_description(desr=mode_des, sheet=self.mod_sheet)

    def create_file_sheet(self, df: dict, hasbase=True, text_wrap=True):
        file_des = OrderedDict(
            FILE='Please provide the following information that will be shown in FILE Level',
            PUBLIC='Y',
            NAME=self.ip,
            DESCRIPTION=self.block.get('Description'),
            COMMENT='Comment of RTL code',
            REGNUM='',
            AUTHOR=self.block.get('Author'),
            DATE='',
            VERSION=self.block.get('Version'),
            ABSTRACT=self.base_addr,
            HISTORY=self.block.get('Revisions'),
        )

        row = ['REGISTER', 'Content of registers', '', '', '', '', '', '', '', '', 'FIELD', 'Content of register fields']
        current_row = self.create_description(desr=file_des, sheet=self.file_sheet)
        for i in range(len(row)):
            self.file_sheet.write(current_row, i, row[i])
        current_row += 1
        if df:
            col = OrderedDict()
            col['PUBLIC\n(Y/N)_0'] = 'Y'
            col['NAME_0'] = self.ip
            col['RTLNAME_0'] = ''
            col['DIM1: LPORT\nDIM2: LIDX1\n(decimal)'] = ''
            col['DIM1: HPORT\nDIM2: HIDX1\n(decimal)'] = ''
            col['DIM1: LARRAY\nDIM2: LIDX2\n(decimal)'] = ''
            col['DIM1: HARRAY\nDIM2: HIDX2\n(decimal)'] = ''
            col['BIT_OFFSET\n(decimal)'] = 'addr_jump'
            col['MEM_BLOCK'] = 'dpi_dll_top_wrap'
            col['DESCRIPTION'] = 'Register'
            col['PUBLIC\n(Y/N)_1'] = 'Y'
            col['MSB\n(decimal)'] = 'MSB'
            col['LSB\n(decimal)'] = 'LSB'
            col['NAME_1'] = 'Name'
            col['RTLNAME_1'] = ''
            col['Description'] = 'Description'
            col['R/W'] = 'Access'
            col['SYNC\nDEFAULT\n(hex)'] = 'Default'
            col['ASYNC\nDEFAULT\n(hex)'] = ''
            col['H/W\nPIN STRAP'] = ''
            col['HIERARCHY_PATH'] = ''
            col['REG/LATCH'] = ''
            col['RANDOM'] = ''
            col['CONSTRAINT'] = ''
            keys = list(col.keys())
            pre_addr = None
            for i in range(len(keys)):
                each_key = keys[i]
                # if col[each_key] != '':
                #     self.file_sheet.col(i).width = 8000
                if 'PUBLIC' in each_key:
                    each_key = 'PUBLIC\n(Y/N)'
                elif 'RTLNAME' in each_key:
                    each_key = 'RTLNAME'
                elif 'NAME' in each_key:
                    each_key = 'NAME'
                self.file_sheet.write(current_row, i, each_key)
            # print(df.to_string())
            current_row += 1
            # address = df['Offset'].drop_duplicates()

            for index, field in df.items():
                each_address = index[0]
                name = index[1]
                register_description = index[2]
                all_public = field['Public'].drop_duplicates().tolist()
                field = field.values

                if hasbase:
                    each_address = int(each_address, 16)
                else:
                    each_address = int(each_address, 16)
                if pre_addr is None:
                    pre_addr = each_address
                addr_jump = each_address - pre_addr
                # print(each_address, pre_addr, addr_jump)
                if addr_jump > 4:
                    dummy = ['N', 'RESERVED', '', '', '', '0', '{:.0f}'.format((addr_jump/4)-2),
                             '32', self.ip, '', 'N', '31', '0', 'RESERVED', '', '', 'RO', '0x{0:08X}'.format(0)]
                    self.loop_same_row(current_row, col_list=dummy, sheet=self.file_sheet)
                    current_row += 1
                if addr_jump < 0:
                    line = 'current address: 0x{:08X}\n' \
                           'next    address: 0x{:08X}'.format(each_address, pre_addr)
                    raise IndexError('Address got wrong order\n'+line)
                pre_addr = each_address
                if len(all_public) == 1:
                    self.file_sheet.write(current_row, 0, all_public[0])
                else:
                    self.file_sheet.write(current_row, 0, 'Y')
                self.file_sheet.write(current_row, 1, name.upper())  # register name
                self.file_sheet.write(current_row, 8, self.ip)  # mem_block
                if register_description.strip() == '':
                    register_description = name
                self.file_sheet.write(current_row, 9, register_description)  # register description

                for each_field in field:
                    self.file_sheet.write(current_row, 10, each_field[0])  # public
                    self.file_sheet.write(current_row, 11, each_field[1])  # msb
                    self.file_sheet.write(current_row, 12, each_field[2])  # lsb
                    self.file_sheet.write(current_row, 13, each_field[3])  # field name
                    self.file_sheet.write(current_row, 16, each_field[4])  # access
                    self.file_sheet.write(current_row, 17, each_field[5])  # default
                    if each_field[6] != 'Y':
                        self.file_sheet.write(current_row, 22, 'NA')  # Random(testable)
                    # remove non-breaking space
                    comments = each_field[7]
                    comments = comments.encode('UTF-8', 'strict')
                    comments = comments.replace(b"\xc2\xa0", b" ")
                    comments = comments.decode('UTF-8', 'strict')
                    if text_wrap:
                        self.file_sheet.write(current_row, 15, comments, self.stype)  # description
                    else:
                        self.file_sheet.write(current_row, 15, comments)
                    current_row += 1
        self.file_sheet.col(15).width = 15000

    @staticmethod
    def create_description(desr, sheet, real_row=False):
        row = 0
        for key, items in desr.items():
            sheet.write(row, 0, key)
            if isinstance(items, list):
                for i in range(len(items)):
                    if not real_row:
                        sheet.write(row + i, 1, items[i])
                    else:
                        sheet.write(row, 1, items[i])
                        row += 1
            else:
                sheet.write(row, 1, items)
            row += 1
        sheet.col(0).width = 5000
        sheet.col(1).width = 5000
        return row

    @staticmethod
    def loop_same_row(row, col_list, sheet):
        for i in range(len(col_list)):
            if col_list[i] == '':
                continue
            sheet.write(row, i, col_list[i])

    def __save__(self, filename):
        self.workbook.save(filename)


class ExcelWriter(QRunnable):
    def __init__(self, filename: str, blocks: list, index_info: dict, separately: bool=False, ):
        super(ExcelWriter, self).__init__()

        self.filename = filename
        self.blocks = blocks
        self.signal = ProgressSignal()
        self.separately = separately
        self.index_info = index_info

    def run(self):
        try:
            if self.separately:
                for block in self.blocks:
                    block_name = block.block_name
                    base_address = block.base_address
                    writer = ProfileWriter(
                        block=block,
                        ip=block_name,
                        base_addr=base_address
                    )
                    block, success, msg = block.toDataFrame()
                    if not success:
                        self.signal.progress.emit(
                            f'# [Error] {block_name}: {msg}'
                        )
                        return
                    offset = [
                        index[0] for index in block.keys()
                    ]
                    duplicates = find_duplicates(offset)
                    for duplicate in duplicates:
                        self.signal.progress.emit(
                            f'# [Error] The address {duplicate} is duplicated in {block_name}.'
                        )
                    if duplicates:
                        self.signal.progress.emit(
                            f'# [Error] Save {self.filename} failed due to duplicate offset.'
                        )
                        return


                    writer.create_mode_sheet()
                    writer.create_file_sheet(df=block)
                    filename = os.path.join(self.filename, block_name+'.xls')
                    writer.__save__(filename)
                    self.signal.progress.emit(
                        f"# [INFO] {filename} Saved"
                    )
            else:
                writer = ProfileWriter(
                    block=None,
                    ip='',
                    base_addr=None,
                    index_info=self.index_info
                )
                for block in self.blocks:
                    writer.set_block(block)
                    block_name = block.block_name
                    base_address = block.base_address
                    block, success, msg = block.toDataFrame()
                    if not success:
                        self.signal.progress.emit(
                            f'# [Error] {block_name}: {msg}'
                        )
                        return
                    offset = [
                        index[0] for index in block.keys()
                    ]
                    duplicates = find_duplicates(offset)
                    for duplicate in duplicates:
                        self.signal.progress.emit(
                            f'# [Error] The Offset {duplicate} is duplicated in {block_name}.'
                        )
                    if duplicates:
                        self.signal.progress.emit(
                            f'# [Error] Save {self.filename} failed due to duplicate offset.'
                        )
                        return
                    writer.set_ip(block_name)
                    writer.set_base_address(base_address)
                    writer.create_mode_sheet()
                    writer.create_file_sheet(df=block)
                writer.create_index_blocks()
                writer.__save__(self.filename)
                self.signal.progress.emit(
                    f"# [INFO] {self.filename} Saved"
                )

        except Exception as e:
            self.signal.progress.emit(
                f"# [Error] Save {self.filename} failed\n"+traceback.format_exc()
            )

        finally:
            self.signal.done.emit()


def find_duplicates(alist):
    tmp_list = []
    dupliates = []
    for item in alist:
        if item not in tmp_list:
            tmp_list.append(item)
        else:
            dupliates.append(item)
    return dupliates

