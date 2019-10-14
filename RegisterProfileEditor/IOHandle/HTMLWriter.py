from PyQt5.QtCore import QRunnable
from .ExcelParser import ProgressSignal
from .RegisterProfileWriter import find_duplicates
from RegisterProfileEditor.config import field_columns
import json
import traceback


class HTMLWriter(QRunnable):

    def __init__(self, template: str, filename: str, blocks, project):
        super(HTMLWriter, self).__init__()
        self.blocks = blocks
        self.template = template
        self.filename = filename
        self.signal = ProgressSignal()
        self.project = project

    def run(self):
        data = {
            "project": [self.project['Project']], "top_module": [self.project['Module']]
        }
        try:
            for block in self.blocks:
                block_name = block.block_name
                data[block_name] = []
                block, success, msg = block.toDataFrame(expand=True)

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

                for index, df in block.items():

                    all_public = df['Public'].drop_duplicates().tolist()
                    if len(all_public) == 1:
                        if all_public[0] == 'N':
                            continue
                    df.MSB = df['MSB'].apply(int)
                    df.LSB = df['LSB'].apply(int)
                    for col, config in field_columns.items():
                        drop = config.get('drop', False)
                        belongto = config.get('belongto', None)
                        if drop:
                            df.drop(col, axis=1, inplace=True)
                        if belongto:
                            df[belongto] = df[belongto] + f'\n{col}: ' + df[col]
                            df.drop(col, axis=1, inplace=True)
                    df['Description'] = df.apply(
                        lambda x: change_reserved(x), axis=1
                    )
                    data[block_name].append(
                        dict(
                            address=index[0],
                            name=index[1],
                            fields=df.to_dict(orient='records')
                        )
                    )
            with open(self.template, 'r') as f:
                template = f.read()
                template = template.replace(
                    '//python gen data',
                    'var tableData =' + json.dumps(data) + ';'
                )

            with open(self.filename, 'w') as f:
                f.write(template)
        except Exception as e:
            self.signal.progress.emit(
                f'# [Error] Create {self.filename} failed.\n'++traceback.format_exc()
            )
        finally:
            self.signal.progress.emit(
                f'# [INFO] Create {self.filename} successfully.'
            )


def change_reserved(df):
    if df['Field'] == 'RESERVED':
        return 'RESERVED'
    else:
        return df['Description']
