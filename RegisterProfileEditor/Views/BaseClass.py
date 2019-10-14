from RegisterProfileEditor.config import register_columns, field_columns, new_reg, new_field, register_formatter, block_formatter
from RegisterProfileEditor.config import loop_formatter, offset_length
import pandas as pd
from copy import deepcopy
from collections import OrderedDict


class Register:

    def __init__(self, register: dict, parent=None):
        super(Register, self).__init__()
        if "Fields" in register.keys():
            self.fields = register.pop('Fields')
        else:
            self.fields = [new_field.copy()]
        self.parent = parent
        self.init_fields()
        self._register = {
            "Offset": '0x0',
            "Name": "NameNotFound",
            "Description": '',
            "Loop": '1',
            "Incr": "0x0"
        }
        self._register.update(register)
        self.inti_register()

    def toDataFrame(self) -> (set, pd.DataFrame, bool):
        success = self.linting()
        for i in range(int(self.loop)):
            df = pd.DataFrame(self.fields, columns=field_columns.keys())
            index = []
            for col in ['Offset', 'Name', 'Description']:
                value = self.get(col)
                if col == 'Name' and self.loop > 1:
                    value = loop_formatter.format(Name=value, integer=i)
                if col == 'Offset' and self.loop > 1:
                    value = int(value, 16) + int(self.incr, 16)*i
                    value = "0x{0:0{len}X}".format(value, len=offset_length)
                index.append(value)
            yield index, df, success

    def linting(self):
        success = False
        msb = int(field_columns.get('MSB').get('maxValue', 31))
        if not self.fields:
            return False
        for values in self.fields:
            for header, config in field_columns.items():
                require = config.get('require', True)
                value = values.get(header, '')
                if require:
                    if value == '':
                        success = False
                        break
                if header == "MSB":
                    value = int(value)
                    lsb = int(values.get('LSB', msb))
                    success = (value == msb) & (msb >= lsb)
                    msb = lsb - 1
                    if not success:
                        break
            if not success:
                break
        if msb >= 0:
            success = False
        return success

    def toDict(self):
        data = self._register.copy()
        data['Fields'] = self.fields
        return data

    def init_fields(self):
        for field in self.fields:
            for key, config in field_columns.items():
                text = field.get(key, None)
                if text is None:
                    text = config.get('default', '')
                field[key] = str(text).strip()

    def inti_register(self):
        for col, config in register_columns.items():
            text = self._register.get(col, None)
            if text is None:
                self._register[col] = config.get('default', '')

    @property
    def loop(self):
        return int(self._register.get('Loop', 1))

    @property
    def incr(self):
        return self._register.get("Incr", '0x0')

    @property
    def offset(self) -> str:
        return self._register.get('Offset', '0x0')

    @property
    def name(self) -> str:
        return self._register.get("Name", '')

    def get(self, key):
        return self._register.get(key, '')

    def get_keys(self):
        return self._register.keys()

    def __str__(self):
        return register_formatter.format(**self._register)

    def __len__(self):
        return len(self.fields)

    def __iter__(self) -> dict:
        for i in range(len(self)):
            yield self.fields[i]

    def __getitem__(self, key):
        return self._register.get(key)

    def __setitem__(self, key, data):
        self._register[key] = data


class Block:
    def __init__(self, block: dict):
        super(Block, self).__init__()
        if "Registers" in block.keys():
            self.registers = block.pop("Registers")
        else:
            self.registers = [deepcopy(new_reg)]

        self.init_registers()
        self._block = {
            "ModuleName": "ModuleNameNotFound",
            "BaseAddress": "0x0"
        }
        self._block.update(block)
        # self.ptr = 0

    def init_registers(self):
        for index, register in enumerate(self.registers):
            self.registers[index] = Register(register, parent=self)

    def get(self, key):
        return self._block.get(key, '')

    @property
    def block_name(self) -> str:
        return self._block.get('ModuleName', '')

    @property
    def base_address(self) -> str:
        return self._block.get('BaseAddress', '0x0')

    def toDataFrame(self, expand=False) -> (dict, bool):
        df = OrderedDict()
        self.registers.sort(
            key=lambda x: x.offset
        )
        for register in self.registers:
            for index, dataframe, success in register.toDataFrame():

                if expand:
                    address = int(index[0], 16) + int(self.base_address, 16)
                    index[0] = f'0x{address:08X}'

                index = tuple(index)

                if not success:
                    return df, False, f'The {register} linting failed.'
                if index in df:
                    return df, False, f'The {register} is duplicated'

                df[index] = dataframe

        return df, True, ''

    def toDict(self) -> dict:
        registers = []
        for register in self.registers:
            # for to_dict in register.toDict():
            registers.append(
                register.toDict()
            )

        return {
            "ModuleName": self.block_name,
            "BaseAddress": self.base_address,
            "Registers": registers
        }

    def get_register(self, index: int):
        try:
            return self.registers[index]
        except IndexError:
            return None

    def get_register_fields(self, index: int):
        return self.get_register(index).fields

    def __getitem__(self, key):
        return self._block.get(key, None)

    def __setitem__(self, key, data):
        self._block[key] = data

    def get_keys(self):
        return self._block.keys()

    def __str__(self):
        return block_formatter.format(**self._block)

    def __len__(self):
        return len(self.registers)

    def __iter__(self) -> Register:
        for i in range(len(self)):
            yield self.registers[i]

    def address_space(self):
        for register in self:
            address = int(self.base_address, 16) + int(register.offset, 16)
            yield f"0x{address:08X} ({self.block_name}/{register.name})", register.fields






