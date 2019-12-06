from .RegisterProfilerReader import RegisterProfileReader
from numpy import nan
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject
import json
from RegisterProfileEditor.Views.BaseClass import Block
import traceback
from RegisterProfileEditor.config import offset_length


class ProgressSignal(QObject):
    progress = pyqtSignal(str)
    done = pyqtSignal()


class ExcelParser(QRunnable):

    def __init__(self, filename: str, blocks: list):
        super(ExcelParser, self).__init__()
        self.filename = filename
        self.blocks = blocks
        self.signal = ProgressSignal()

    def run(self):
        filename = self.filename.split("/")[-1]
        try:
            reader = RegisterProfileReader(xls_file=self.filename, signal=self.signal.progress)
            reader.read_index()
            reader.get_blocks()
            df = reader.registers()
            modules = reader.modules

            # handle data
            col_to_keep = [0, 2, 4, 5, 6, 7, 8, 9, 11, 12, 13, 18]
            col_to_rename = ['ADDR', 'NAME', 'BLOCK', 'Register Description', 'Public', 'MSB', 'LSB', 'Field',
                             'Description', 'Access', 'Default', "Testable"]
            df = df.iloc[:, col_to_keep]
            df = df.replace('', nan)

            df.columns = col_to_rename
            check = df['ADDR'].dropna()
            # print(check.is_unique)
            if not check.is_unique:
                self.signal.progress.emit(
                    f'# [Warning]\nThe Address space of {filename} is not unique.\nSome address are duplicate.'
                )
            df[['ADDR', 'NAME', 'BLOCK', 'Register Description']] = \
                df[['ADDR', 'NAME', 'BLOCK', 'Register Description']].fillna(method='ffill')
            df = df.replace(nan, '')
            df['Testable'] = df['Testable'].replace('', 'Y')
            df['Testable'] = df['Testable'].replace('^(?!.*Y).*$', 'N', regex=True)
            df.MSB = df['MSB'].apply(int)
            df.LSB = df['LSB'].apply(int)
            block_group = df.groupby(['BLOCK'])

            for block, group in block_group:

                baseaddr = modules.get(block)
                registers = group.drop(['BLOCK'], axis=1)
                registers = registers.groupby(['ADDR', "NAME", "Register Description"])
                module = {
                    "ModuleName": block,
                    "BaseAddress": baseaddr,
                    "Registers": []
                }
                module.update(reader.get_info(block))
                for register, fields in registers:
                    addr, name, description = register
                    addr = int(addr, 16) - int(baseaddr, 16)
                    module["Registers"].append(
                        dict(
                            Offset=f'0x{addr:0{offset_length}X}',
                            Name=name,
                            Description=description,
                            Fields=fields.drop(
                                ['ADDR', "NAME", "Register Description"], axis=1
                            ).to_dict(orient='records')
                        )
                    )
                self.blocks.append(Block(module))
            self.signal.progress.emit(
                f'# [INFO] Load {filename} done successfully'
            )
        except Exception as e:
            self.signal.progress.emit(
                f"# [Error] Parsing {filename} failed\n"+traceback.format_exc()
            )
        finally:
            self.signal.done.emit()


class JsonLoad(QRunnable):
    def __init__(self, filename: str, blocks: list):
        super(JsonLoad, self).__init__()
        self.filename = filename
        self.blocks = blocks
        self.signal = ProgressSignal()

    def run(self):
        filename = self.filename.split("/")[-1]
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for block in data:
                        self.blocks.append(Block(block))
                elif isinstance(data, dict):
                    self.blocks.append(Block(data))
                else:
                    self.signal.progress.emit(
                        f'# [Warning] This {filename} type of file not support'
                    )
                    return
            self.signal.progress.emit(
                f'# [INFO] Load {filename} done successfully'
            )
        except Exception as e:
            self.signal.progress.emit(
                f'# [Error] Load {filename} failed\n'+traceback.format_exc()
            )

        finally:
            self.signal.done.emit()


