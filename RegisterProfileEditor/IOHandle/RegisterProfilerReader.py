from xlrd import open_workbook
from xlrd.biffh import XLRDError

import pandas as pd
from PyQt5.QtCore import pyqtSignal, QObject


class RegisterProfileReader(QObject):

    def __init__(self, xls_file, blocks=None, signal: pyqtSignal=None):
        super(RegisterProfileReader, self).__init__(None)
        self.xls = xls_file
        self.blocks = blocks
        self.mem_blocks = {}
        # self.register_set = OrderedDict()
        self.register_set = []
        self.col = []
        self.modules = {}
        self.signal = signal
        self.info = {
            "Author": '',
            "Description": "",
            "Version": "",
            "History": "",
        }
        self.module_info = {}

    def get_col(self, module):
        if not module:
            col_to_read = ['NAME', 'OFFSET ADDR', 'NUMBER', 'DESCRIPTION', 'Belong to']
            col_to_exit = ['HISTORY', 'Revision History']
        else:
            col_to_read = ['REG_FILE', 'File list of registers in DATA_MUX (*.xml)']
            col_to_exit = ['', '']
        return col_to_read, col_to_exit

    def read_index(self, index='chip_index', addr_offset=None):
        offset = '0x0'
        with open_workbook(self.xls) as xls:
            module_name = xls.sheet_names()
            if index in module_name:
                sheets = [index]
                module = False
            else:
                sheets = [x for x in module_name if 'mod_' in x]
                module = True
            col_to_read, col_to_exit = self.get_col(module)
            for sheet in sheets:
                index_sheet = xls.sheet_by_name(sheet)
                nrows = index_sheet.nrows
                read_en = False
                info = self.info.copy()
                for i in range(nrows):
                    cells = [x.value for x in index_sheet.row(i)]
                    if read_en:
                        if cells[0] == col_to_exit[0] and cells[1] == col_to_exit[1]:
                            break
                        cells.append(0)
                        if not module:
                            self.mem_blocks[cells[0]] = cells[1:]
                        else:
                            name = cells[1].replace('.xml', '').replace('file_', '')
                            value = [offset, ]
                            value.extend(cells[1:])
                            self.mem_blocks[name] = value
                            self.module_info[name] = info.copy()
                        continue
                    if cells[0] == col_to_read[0] and cells[1] == col_to_read[1]:
                        read_en = True
                    if 'ABSTRACT' in cells[0] and module:
                        offset = cells[1]
                        if offset.strip() == '':
                            offset = '0x0'
                        if addr_offset is not None:
                            offset = addr_offset

                    # title = cells[0].strip().lower().capitalize()
                    # if title in self.info.keys():
                    #     info[title] = cells[1]

                if not read_en:
                    self.signal.emit('# [Warning] {} column headers failed to locate.'.format(sheet))

    def get_blocks(self):
        col_to_read = ['PUBLIC\n(Y/N)', 'NAME', 'RTLNAME', 'DIM1: LPORT\nDIM2: LIDX1\n(decimal)',
                       'DIM1: HPORT\nDIM2: HIDX1\n(decimal)', 'DIM1: LARRAY\nDIM2: LIDX2\n(decimal)',
                       'DIM1: HARRAY\nDIM2: HIDX2\n(decimal)', 'BIT_OFFSET\n(decimal)', 'MEM_BLOCK',
                       'DESCRIPTION', 'PUBLIC\n(Y/N)', 'MSB\n(decimal)', 'LSB\n(decimal)', 'NAME', 'RTLNAME',
                       'Description', 'R/W', 'SYNC\nDEFAULT\n(hex)', 'ASYNC\nDEFAULT\n(hex)', 'H/W\nPIN STRAP',
                       'HIERARCHY_PATH', 'REG/LATCH', 'RANDOM', 'CONSTRAINT']
        none = ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
        col_to_drop = ['DIM1: LPORT\nDIM2: LIDX1\n(decimal)',
                        'DIM1: HPORT\nDIM2: HIDX1\n(decimal)', 'DIM1: LARRAY\nDIM2: LIDX2\n(decimal)',
                        'DIM1: HARRAY\nDIM2: HIDX2\n(decimal)', 'BIT_OFFSET\n(decimal)']
        index_to_drop = [col_to_read.index(x) for x in col_to_drop]
        # for x in sorted(index_to_drop, reverse=True):
        #     col_to_read.pop(x)
        # print(col_to_read)
        col = ['ADDR']
        # for index in index_to_read:
        #     col.append(col_to_read[index])
        col.extend(col_to_read)
        for x in sorted(index_to_drop, reverse=True):
            col.pop(x+1)
        self.col = col
        col_to_exit = ['TABLE', 'Content of registers', '', '', '', '', '', '',
                       '', '', 'FIELD', 'Content of register fields', '', '',
                       '', '', '', '', '', '', '', '', '', '']
        if self.blocks is None:
            self.blocks = self.mem_blocks.keys()
        save_block = None
        # print(self.blocks)
        for each_block in self.blocks:
            # print(each_block, self.mem_blocks[each_block])
            read_en = False

            if each_block == '':
                continue
            self.signal.emit(f'# [INFO] Parsing {each_block} module.')
            with open_workbook(self.xls) as xls:
                try:
                    sheet = xls.sheet_by_name('file_{0}'.format(each_block))
                except XLRDError:
                    self.signal.emit('# [Warning] The sheet of the "file_{0}" Not Found.'.format(each_block))
                    continue
                else:
                    nrows = sheet.nrows
                    info = self.info.copy()
                    for i in range(nrows):
                        cells = [x.value for x in sheet.row(i)]
                        if read_en:
                            if cells == col_to_exit:
                                read_en = False
                                continue
                            if cells == none:
                                continue
                            belong_to = col_to_read.index('MEM_BLOCK')
                            mem_block = cells[belong_to]
                            lc = ['']
                            if mem_block != '':
                                offset_addr = self.mem_blocks[mem_block][0]
                                self.modules[each_block] = offset_addr
                                # addr = self.mem_blocks[mem_block][-1]
                                addr = int(offset_addr, 16) + self.mem_blocks[mem_block][-1]
                                save_block = mem_block
                                addr = int(addr)
                                lc = ['0x{:08X}'.format(addr)]
                            lsb = col_to_read.index('LSB\n(decimal)')
                            lsb = cells[lsb]
                            bit = col_to_read.index('BIT_OFFSET\n(decimal)')
                            num = col_to_read.index('DIM1: HARRAY\nDIM2: HIDX2\n(decimal)')
                            bit = cells[bit]
                            num = cells[num]
                            for x in sorted(index_to_drop, reverse=True):
                                cells.pop(x)
                            lc.extend(cells)
                            self.register_set.append(lc)
                            if int(lsb) == 0:
                                # print(bit, num, lc)
                                # print(lsb, num, lc)
                                cnt = self.mem_blocks[save_block][-1]
                                try:
                                    self.mem_blocks[save_block][-1] = cnt + (int(bit)/8) * (int(num) + 1)
                                except ValueError:

                                    self.mem_blocks[save_block][-1] = cnt + 4
                            continue
                        if cells[0].lower() == col_to_read[0].lower() and cells[1].lower() == col_to_read[1].lower():
                            read_en = True
                            self.module_info[each_block] = info
                            continue
                        title = cells[0].strip().lower().capitalize()
                        if title in self.info.keys():
                            info[title] = cells[1]
            if not read_en:
                self.signal.emit('# [Warning] The column headers of the {0} failed to locate.'.format(each_block))

    def registers(self):
        df = pd.DataFrame(self.register_set,
                          columns=self.col
                          )
        df = df[df.iloc[:, 2] != 'RESERVED']
        return df

    def get_info(self, module):
        info = self.module_info.get(module, {})
        if info:
            info['Revisions'] = info.pop('History')
        return info



