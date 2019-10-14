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
                        continue
                    if cells[0] == col_to_read[0] and cells[1] == col_to_read[1]:
                        read_en = True
                    if 'ABSTRACT' in cells[0] and module:
                        offset = cells[1]
                        if offset.strip() == '':
                            offset = '0x0'
                        if addr_offset is not None:
                            offset = addr_offset

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
                            continue
            if not read_en:
                self.signal.emit('# [Warning] The column headers of the {0} failed to locate.'.format(each_block))

    def registers(self):
        df = pd.DataFrame(self.register_set,
                          columns=self.col
                          )
        df = df[df.iloc[:, 2] != 'RESERVED']
        return df

    # def to_excel(self, name='auto_naming'):
    #     df = self.registers()
    #     col = df.columns
    #     col_cnt = 0
    #     workbook = Workbook()
    #     sheet = workbook.add_sheet(name)
    #     style = easyxf('align: wrap on, vert top, horiz left')
    #     index_replace_nan = [0, 1, 2, 4, 5]
    #     for i in range(len(col)):
    #         row_cnt = 0
    #         series = df.iloc[:, i]
    #         header = col[i]
    #         if i == 6:
    #             header = 'Public\n(Y/N)'
    #         sheet.write(row_cnt, col_cnt, header, style)
    #         row_cnt += 1
    #         if i in index_replace_nan:
    #             series = series.replace('', np.nan)
    #         series.fillna(method='ffill', inplace=True)
    #         for value in series:
    #             sheet.write(row_cnt, col_cnt, value, style)
    #             row_cnt += 1
    #         col_cnt += 1
    #     sheet.col(0).width = 4000
    #     # sheet.col(1).width = 6000
    #     sheet.col(2).width = 6000
    #     sheet.col(4).width = 4000
    #     sheet.col(5).width = 9000
    #     sheet.col(9).width = 6000
    #     sheet.col(11).width = 15000
    #     sheet.col(15).width = 5000
    #     workbook.save(name+'.xls')
    #
    # def __call__(self, *args, **kwargs):
    #     self.read_index()
    #     self.get_blocks()
    #     self.registers()


# class RegisterProfileWriter:
#     def __init__(self, xls, ip, blocks=None, project=''):
#         self.xls = xls
#         self.blocks = blocks
#         self.df = None
#         self.mode = 'mod_' + ip
#         self.file = 'file_' + ip
#         self.ip = ip.upper()
#         self.workbook = Workbook()
#         self.mod_sheet = self.workbook.add_sheet(sheetname=self.mode, cell_overwrite_ok=True)
#         # self.file_sheet = self.workbook.add_sheet(sheetname=self.file, cell_overwrite_ok=True)
#         self.col_name = None
#         self.stype = easyxf('align: wrap on, vert top, horiz left')
#         self.mem_blocks = None
#         self.project = project
#
#     def read_file(self):
#         # with open_workbook(self.file) as xls:
#         #     sheet_names = xls.sheet_names()
#         #     for sheet_name in sheet_names:
#         #         sheet = xls.sheet_by_name(sheet_name)
#         #         nrows = sheet.nrows
#         col_to_index = ['ADDR', 'PUBLIC\n(Y/N)', 'NAME', 'RTLNAME', 'MEM_BLOCK', 'DESCRIPTION',
#                         #'Public\n(Y/N)'
#                         ]
#         df = pd.read_excel(self.xls,
#                            #index_col=[0, 1, 2, 3, 4, 5]
#                            )
#         col_to_insert = ['DIM1: LPORT\nDIM2: LIDX1\n(decimal)',
#                        'DIM1: HPORT\nDIM2: HIDX1\n(decimal)', 'DIM1: LARRAY\nDIM2: LIDX2\n(decimal)',
#                        'DIM1: HARRAY\nDIM2: HIDX2\n(decimal)', 'BIT_OFFSET\n(decimal)']
#         for col in reversed(col_to_insert):
#             df.insert(4, column=col, value=np.nan)
#             col_to_index.insert(4, col)
#         # df.insert()
#         df = df.fillna('')
#         self.mem_blocks = pd.unique(df['MEM_BLOCK']).tolist()
#         self.col_name = df.columns.to_list()[1:]
#         self.col_name = [x.replace('.1', '') for x in self.col_name]
#         df['ADDR'] = df['ADDR'].apply(lambda x: int(x, 16))
#         df.set_index(['ADDR',], inplace=True)
#         # col_name = df.columns
#         # if there is a duplicate column name, pandas will add .1 to uniquify columns
#         # col_name = [x.replace('.1', '') for x in col_name]
#         # df.columns = col_name
#
#         # diff = df['ADDR'].rolling(window=2).apply(lambda x: self.rolling(x), raw=True)
#
#         # df['ADDR'] = df['ADDR'].apply(lambda x: '0x{0:08X}'.format(int(x)))
#         # print(df.to_string())
#         self.df = df
#
#     @staticmethod
#     def rolling(x):
#         if x[1] - x[0] <= 4:
#             return np.nan
#         else:
#             diff = (x[1] - x[0])/4
#             return diff - 2
#         # return
#
#     def create_mode_sheet(self):
#         xml = ['File list of registers in DATA_MUX (*.xml)']
#         if not self.blocks:
#             self.blocks = self.mem_blocks
#         for block in self.blocks:
#             if block not in self.mem_blocks:
#                 raise IndexError
#             xml.append('file_{}.xml'.format(block.upper()))
#         mode_des = OrderedDict(
#             DATA_MUX='Please provide the following information that will be shown in DATA_MUX Level',
#             NAME=self.ip,
#             DESCRIPTION='This chapter describes ' + self.ip,
#             COMMENT='Comment of RTL code',
#             REGNUM='',
#             AUTHOR='',
#             DATE='',
#             VERSION='',
#             ABSTRACT='',
#             HISTORY='',
#             REG_FILE=xml,
#         )
#         self.create_description(desr=mode_des, sheet=self.mod_sheet)
#
#     def create_file_sheet(self):
#
#         row = ['REGISTER', 'Content of registers', '', '', '', '', '', '', '', '', 'FIELD', 'Content of register fields']
#         for block in self.blocks:
#             block = block.upper()
#             file_des = OrderedDict(
#                 FILE='Please provide the following information that will be shown in FILE Level',
#                 PUBLIC='Y',
#                 NAME=block,
#                 DESCRIPTION=block + ' Register Sets',
#                 COMMENT='Comment of RTL code',
#                 REGNUM='',
#                 AUTHOR='',
#                 DATE='',
#                 VERSION='',
#                 ABSTRACT='',
#                 HISTORY='',
#             )
#             sheet = self.workbook.add_sheet(sheetname='file_{}'.format(block), cell_overwrite_ok=True)
#             current_row = self.create_description(desr=file_des, sheet=sheet)
#             for i in range(len(row)):
#                 sheet.write(current_row, i, row[i])
#             current_row += 1
#
#             for i, name in enumerate(self.col_name):
#                 sheet.write(current_row, i, name, self.stype)
#             current_row += 1
#             df = self.df.loc[self.df.loc[:, 'MEM_BLOCK'] == block]
#             if df.empty:
#                 raise ImportError('DataFrame is empty')
#             index = df.index
#             start_addr = None
#             print(df.to_string())
#             register = df.values
#             for each_field, addr in zip(register, index):
#                 msb = each_field[11]
#                 if int(msb) == 31:
#                     if start_addr:
#                         jump = addr - start_addr
#                         if jump > 4:
#                             dummy = ['N', 'RESERVED', '', '', '', '0', '{:.0f}'.format((jump / 4) - 2),
#                                      '32', block, '', 'N', '31', '0', 'RESERVED', '', '', 'RO', '0x{0:08X}'.format(0)]
#                             self.loop_same_row(current_row, col_list=dummy, sheet=sheet)
#                             current_row += 1
#                         if jump < 0:
#                             raise IndexError
#                     for i in range(self.col_name.index('DESCRIPTION') + 1):
#                         sheet.write(current_row, i, each_field[i], self.stype)
#                     start_addr = addr
#                 for i in range(self.col_name.index('Public\n(Y/N)'), self.col_name.index('CONSTRAINT')):
#                     sheet.write(current_row, i, each_field[i], self.stype)
#                 current_row += 1
#             sheet.col(self.col_name.index('Description')).width = 15000
#             sheet.col(self.col_name.index('DESCRIPTION')).width = 10000
#             sheet.col(self.col_name.index('MEM_BLOCK')).width = 5000
#             sheet.col(self.col_name.index('SYNC\nDEFAULT\n(hex)')).width = 5000
#             sheet.col(13).width = 5000
#             sheet.col(1).width = 6000
#         self.save()
#
#     def save(self):
#         if self.project != '':
#             name = '{}_RegisterProfile_{}.xls'.format(self.ip, self.project)
#         else:
#             name = '{}_RegisterProfile.xls'.format(self.ip)
#         self.workbook.save(name)
#
#     @staticmethod
#     def loop_same_row(row, col_list, sheet):
#         for i in range(len(col_list)):
#             if col_list[i] == '':
#                 continue
#             sheet.write(row, i, col_list[i])
#
#     @staticmethod
#     def create_description(desr, sheet):
#         row = 0
#         for key, items in desr.items():
#             sheet.write(row, 0, key)
#             if isinstance(items, list):
#                 for i in range(len(items)):
#                     sheet.write(row + i, 1, items[i])
#             else:
#                 sheet.write(row, 1, items)
#             row += 1
#         sheet.col(0).width = 5000
#         sheet.col(1).width = 5000
#         return row
#
# # # blocks = ['MEM_SRAM', 'MEM_ROM', 'MEM_SRAM_ASYNC', 'DRAM_ZONE']
# # #
# # # reader = RegisterProfileReader(xls_file=file_to_read, blocks=blocks)
# # # reader()
# # # # reader.to_execl('sramctrl.xls')
# # # reader.to_excel('sramctrl')
# #
#
# if __name__ == '__main__':
#
#     writer = RegisterProfileWriter('sramctrl.xls', 'MEM_SRAM',
#                                    # blocks=['SRAM_OC0', 'SRAM_ASYNC', 'MEM_ROM'],
#                                    project='RL6537',
#                                    )
#     writer.read_file()
#     writer.create_mode_sheet()
#     writer.create_file_sheet()
