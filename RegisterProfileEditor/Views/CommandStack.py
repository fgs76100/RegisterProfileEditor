from PyQt5.QtWidgets import QUndoCommand, QTableView, QHeaderView
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import QModelIndex, Qt
from .BaseClass import Register
import traceback
import sys


class TableRemoveCommand(QUndoCommand):
    
    def __init__(self, widget: QTableView, items: {int: [QStandardItem]}, description: str, obj: list):
        super(TableRemoveCommand, self).__init__(description)
        self.widget = widget
        self.items = items
        self.obj = obj

    def redo(self):
        last_row = int
        for row in sorted(self.items.keys(), reverse=True):
            self.widget.model().takeRow(row)
            last_row = row
            self.obj.pop(row)
        self.widget.selectRow(last_row)

    def undo(self):
        last_row = int
        model = self.widget.model()
        for row, items in self.items.items():
            # item = self.items[len(self.rows)-row-1]
            model.insertRow(
                row,
                [QStandardItem(item) for item in items]
            )
            self.widget.resizeRowToContents(row)
            field = {}
            for col in range(model.columnCount()):
                field[model.horizontalHeaderItem(col).text()] = items[col]
            self.obj.insert(row, field)
            last_row = row

        self.widget.selectRow(last_row)


class TableInsertCommand(QUndoCommand):

    def __init__(self, widget: QTableView, row: int, items: [QStandardItem], description: str, obj: list):
        super(TableInsertCommand, self).__init__(description)
        self.widget = widget
        self.items = items
        self.row = row
        self.obj = obj

    def redo(self):
        model = self.widget.model()
        try:
            model.insertRow(
                self.row,
                [QStandardItem(item) for item in self.items]
            )
            field = {}
            for col in range(model.columnCount()):
                field[model.horizontalHeaderItem(col).text()] = self.items[col]
            self.obj.insert(self.row, field)

        except TypeError:
            traceback.print_exc(file=sys.stdout)
            print([item.text() for item in self.items])

        self.widget.selectRow(self.row)
        self.widget.resizeRowToContents(self.row)

    def undo(self):
        self.widget.model().removeRow(self.row)
        self.obj.pop(self.row)


class DataChanged(QUndoCommand):
    def __init__(self,
                 widget: QStandardItemModel, newtext: str, oldtext: [str],
                 index: [QModelIndex], description: str, obj=None
                 ):
        super(DataChanged, self).__init__(description)
        self.widget = widget
        self.newText = newtext
        self.oldText = oldtext
        self.index = index
        self.obj = obj

    def redo(self):
        for each_index in self.index:
            self.widget.itemFromIndex(each_index).setText(self.newText)
            if self.obj:
                if not isinstance(self.obj, Register):
                    obj = self.obj[each_index.row()]
                else:
                    obj = self.obj
                obj[self.widget.horizontalHeaderItem(each_index.column()).text()] = self.newText

    def undo(self):
        for each_index, oldText in zip(self.index, self.oldText):
            self.widget.itemFromIndex(each_index).setText(oldText)
            if self.obj:
                if not isinstance(self.obj, Register):
                    obj = self.obj[each_index.row()]
                else:
                    obj = self.obj
                obj[self.widget.horizontalHeaderItem(each_index.column()).text()] = oldText


class TreeRemoveCommand(QUndoCommand):

    def __init__(self, widget: QStandardItem, row: int, description: str, block: list):
        super(TreeRemoveCommand, self).__init__(description)
        self.widget = widget
        self.row = row
        self.item = None
        self.block_value = None
        self.block = block

    def redo(self):
        self.item = self.widget.takeRow(self.row)
        self.block_value = self.block.pop(self.row)

    def undo(self):
        self.widget.insertRow(self.row, self.item)
        self.block.insert(self.row, self.block_value)


class TreeInsertCommand(QUndoCommand):

    def __init__(self, widget: QStandardItem,
                 block: list, row: int, items, description: str,
                 cols: dict, is_root=False
                 ):
        super(TreeInsertCommand, self).__init__(description)
        self.widget = widget
        self.row = row
        self.items = items
        self.block = block
        self.cols = cols
        self.is_root = is_root
        self.widget_item = None

    def redo(self):
        if not self.is_root:
            if self.widget_item is None:
                self.widget.insertRow(
                    self.row,
                    [
                        QStandardItem(
                            self.items.get(col)
                        ) for col in self.cols.keys()
                    ]
                )
            else:
                self.widget.insertRow(self.row, self.widget_item)
        else:
            if self.widget_item is None:
                self.items.setDisplayItem()
                root = self.items.getDisplayItem()
                for register in self.items:
                    root[0].appendRow(
                        [
                            QStandardItem(
                                register.get(col)
                            ) for col in self.cols.keys()
                        ]
                    )
                self.widget.insertRow(self.row, root)
            else:
                self.widget.insertRow(self.row, self.widget_item)

        self.block.insert(
            self.row,
            self.items
        )

    def undo(self):
        self.widget_item = self.widget.takeRow(self.row)
        self.block.pop(self.row)


class TreeShiftCommand(QUndoCommand):

    def __init__(self, rows: dict, registers, description: str, value: str):
        super(TreeShiftCommand, self).__init__(description)
        self.rows = rows
        self.registers = registers
        self.value = value

    def redo(self):
        for row, item in self.rows.items():
            offset = self.registers[row].shift(self.value)
            if offset:
                item.setText(offset)

    def undo(self):
        if self.value.startswith('-'):
            value = self.value.replace('-', '')
        else:
            value = '-' + self.value
        for row, item in self.rows.items():
            offset = self.registers[row].shift(value)
            if offset:
                item.setText(offset)


# class TreeDataChanged(QUndoCommand):
#     def __init__(self, widget: QStandardItemModel, newtext: str, oldtext: str, index: QModelIndex, description: str):
#         super(TreeDataChanged, self).__init__(description)
#         self.widget = widget
#         self.newText = newtext
#         self.oldText = oldtext
#         self.index = index
#
#     def redo(self):
#         self.widget.itemFromIndex(self.index).setText(self.newText)
#
#     def undo(self):
#         self.widget.itemFromIndex(self.index).setText(self.oldText)

class ReplaceCommand(QUndoCommand):
    def __init__(self, widget: QTableView, new: str, old: str, index:QModelIndex, description: str):
        super(ReplaceCommand, self).__init__(description)
        self.widget = widget
        self.new = new
        self.old = old
        self.index = index

    def redo(self):
        item = self.widget.model().itemFromIndex(self.index)
        item.setData(self.new, Qt.DisplayRole)
        self.widget.selectionModel().clearSelection()
        self.widget.setCurrentIndex(self.index)

    def undo(self):
        item = self.widget.model().itemFromIndex(self.index)
        item.setData(self.old, Qt.DisplayRole)
        # self.widget.clearFocus()
        self.widget.selectionModel().clearSelection()
        self.widget.setCurrentIndex(self.index)
        self.widget.setFocus()




