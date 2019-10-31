import sys
from copy import deepcopy
import traceback
from PyQt5.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLineEdit, QUndoStack, QVBoxLayout, QMenu, QAction
from PyQt5.QtGui import QContextMenuEvent, QStandardItemModel, QStandardItem
import re
from .widgets import TreeView, LineEditDelegate, MessageBox
from .widgets import ListViewDelegate, TextEditDelegate, InputDialog
from .CommandStack import TreeInsertCommand, TreeRemoveCommand, TreeShiftCommand
from .CommandStack import DataChanged
from RegisterProfileEditor.config import register_contextmenu, new_reg, GUI_NAME, caption_formatter, block_columns
from .BaseClass import Block, Register

import qtawesome as qta


class BlockView(QWidget):

    selectionChanged = pyqtSignal(int, int, str)
    addAnalyzerTrigger = pyqtSignal(str)

    def __init__(self, parent, cols: dict, blocks: [Block], undoStack: QUndoStack):
        super(BlockView, self).__init__(parent=parent)
        self.undoStack = undoStack
        self.buffer = None
        self.cols = cols
        self.blocks = blocks
        self.tree = TreeView(self)
        self.model = QStandardItemModel()
        self.tree.setModel(self.model)
        self.entry = QLineEdit(self)
        self.entry.setPlaceholderText('Search for ...')
        self.entry.setClearButtonEnabled(True)
        self.entry.setMinimumHeight(35)
        self.entry.setMaximumWidth(250)
        vbox = QVBoxLayout()
        vbox.addWidget(self.entry)
        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.tree.selectionModel().selectionChanged.connect(self.selectionChangedEvent)
        self.tree.doubleClicked.connect(self.moduleModify)
        self.entry.textChanged.connect(self.searchTree)
        self.hiddenRows = {}

        self.create_ui()

    def clearHidden(self):
        if self.entry.text().strip() == '':
            for key, rows in self.hiddenRows.items():
                for row in rows:
                    self.tree.setRowHidden(
                        row,
                        key,
                        False
                    )
            self.hiddenRows = {}

    def searchTree(self):
        text = self.entry.text().strip()
        if text == '':
            self.clearHidden()
            return
        pattern = re.compile(text, re.IGNORECASE)
        field_pattern = re.compile(text, re.IGNORECASE)
        for row in range(self.model.rowCount()):
            item = self.model.item(row, 0)
            index = self.model.indexFromItem(item)
            block = self.blocks[index.row()]
            if item.hasChildren():
                for itemRow in range(item.rowCount()):
                    fields = block.get_register_fields(itemRow)
                    for itemCol in range(item.columnCount()):
                        child = item.child(itemRow, itemCol)
                        if pattern.search(child.text()):
                            self.tree.setRowHidden(
                                itemRow,
                                index,
                                False
                            )
                            break
                        if itemCol == item.columnCount() - 1:
                            if self.search_fields(fields, field_pattern):
                                self.tree.setRowHidden(
                                    itemRow,
                                    index,
                                    False
                                )
                                break
                    else:
                        self.hiddenRows.setdefault(index, [])
                        self.hiddenRows[index].append(itemRow)
                        self.tree.setRowHidden(
                            itemRow,
                            index,
                            True
                        )

    def search_fields(self, fields, pattern):
        for field in fields:
            for value in field.values():
                # if type(value) is int:
                #     value = str(value)
                if pattern.findall(value):
                    return True
        return False

    def dataBeforeChangedEvent(self, index: QModelIndex, new: str, old: str):
        if not index.isValid():
            return
        if index.data(Qt.UserRole) == 'block':
            return
        register = self.blocks[index.parent().row()].get_register(index.row())
        row = index.row()
        col = index.column()
        cmd = DataChanged(
            widget=self.model,
            newtext=new,
            oldtext=[old],
            index=[index],
            description=f'Table Data changed at ({row}, {col})',
            obj=register,
        )
        self.undoStack.push(cmd)

    def create_ui(self):
        self.create_actions()
        self.create_cols()
        self.create_rows()
        self.tree.setCurrentIndex(self.model.index(0, 0))

    def create_rows(self, blocks: [dict]=None):
        if blocks is not None:
            self.blocks = blocks
            self.model.removeRows(
                0,
                self.model.rowCount()
            )
        for block in self.blocks:
            block.setDisplayItem()
            root = block.getDisplayItem()
            for register in block:
                root[0].appendRow(
                    [
                        QStandardItem(
                            register.get(col)
                        ) for col in self.cols.keys()
                    ]
                )
            self.model.appendRow(
                root
            )

    def create_cols(self):
        self.model.setHorizontalHeaderLabels(self.cols.keys())

        for col, config in enumerate(self.cols.values()):
            widget = config.get('widget', None)
            width = config.get('width', None)
            if width:
                self.tree.setColumnWidth(col, width)
            if widget == "list":
                items = config.get('items', [])
                delegate = ListViewDelegate(self.tree, items)
            elif widget == 'textEdit':
                delegate = TextEditDelegate(self.tree)
            else:
                validator = config.get('type', None)
                items = config.get('items', None)
                delegate = LineEditDelegate(
                    self.tree,
                    items,
                    validator,
                    minValue=config.get('minValue', 0),
                    maxValue=config.get('maxValue', 31)
                )

            self.tree.setItemDelegateForColumn(col, delegate)
            delegate.dataBeforeChanged.connect(
                self.dataBeforeChangedEvent
            )

    def selectionChangedEvent(self):
        # self.blockSignals(True)
        index = self.tree.currentIndex()
        if not index.isValid():
            # print(index.row(), index.column(), 'is not exist')
            return
        try:
            if not index.model().hasChildren(index):
                block_index = index.parent()
                if not block_index.isValid():
                    return
                block_index = block_index.row()
                block = self.blocks[block_index]
                index = index.row()
                register = block.get_register(index)
                if register is None:
                    return
                self.selectionChanged.emit(
                    block_index,
                    index,
                    caption_formatter.format(
                        Module=block, Register=register
                    )
                )
        except Exception:
            traceback.print_exc(file=sys.stdout)

    def getRowValues(self, items=None):
        if items is None:
            items = self.tree.selectedIndexes()
        values = {}
        for item, col in zip(items, self.cols.keys()):
            values[col] = item.data()
        return values

    def iterItemPerSelectedRow(self) -> (int, QModelIndex):
        indexes = self.tree.selectedIndexes()
        col_length = len(self.cols.keys())

        for i in range(0, len(indexes), col_length):
            index = indexes[i]
            yield index.row(), index
            # yield indexes[i].row()

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu(self.tree)
        actions = {}

        for each_menu in register_contextmenu:
            label = each_menu.get('label')
            icon = each_menu.get('icon')
            buffer = each_menu.get('buffer', False)
            action = menu.addAction(label)

            if buffer and self.buffer is None:
                action.setEnabled(False)
            sc = each_menu.get('shortcut', None)
            if sc:
                action.setShortcut(sc)
            if icon:
                action.setIcon(qta.icon(icon, color='gray'))
            actions[action] = getattr(self, each_menu.get('action'))

        action = menu.exec_(self.mapToGlobal(event.pos()))
        func = actions.get(action)
        if callable(func):
            func()

    def create_actions(self):
        for config in register_contextmenu:
            sc = config.get('shortcut', None)
            if sc is None:
                continue
            label = config.get('label')
            qaction = QAction(label, self.tree)
            # func = actions.pop()
            func = getattr(self, config.get('action'))
            qaction.setShortcut(sc)
            qaction.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            qaction.triggered.connect(func)
            self.addAction(qaction)

    def append_new(self):
        row = self.tree.currentRow
        new = Register(deepcopy(new_reg))
        index = self.tree.currentIndex()
        if not index.isValid():
            return
        if index.data(Qt.UserRole) == 'block':
            return
        if index.column() != 0:
            index = index.sibling(index.row(), 0)
        try:
            offset = int(index.data(), 16) + 4
            new['Offset'] = "0x{0:04X}".format(offset)
            self.insert_row(
                row+1,
                [new],
            )
            self.tree.clearSelection()
            self.tree.setCurrentIndex(
                index.sibling(row+1, 0)
            )
        except ValueError:
            MessageBox.showError(
                self,
                "The Offset value of this row in not valid\n",
                GUI_NAME
            )

    def prepend_new(self):
        index = self.tree.currentIndex()
        if not index.isValid():
            return
        if index.data(Qt.UserRole) == 'block':
            return
        if index.column() != 0:
            index = index.sibling(index.row(), 0)
        row = self.tree.currentRow
        new = Register(deepcopy(new_reg))
        try:
            offset = int(index.data(), 16) - 4
            if offset < 0:
                offset = 0
            new['Offset'] = "0x{0:04X}".format(offset)
            self.insert_row(
                row,
                [new],
            )
            self.tree.clearSelection()
            self.tree.setCurrentIndex(
                index.sibling(row, 0)
            )
        except ValueError:
            MessageBox.showError(
                self,
                "The Offset value of this row in not valid\n",
                GUI_NAME
            )

    def append_copy(self):
        if self.buffer is None:
            return
        index = self.tree.currentIndex()
        if index.data(Qt.UserRole) == 'block':
            items = self.buffer.get('blocks')
        else:
            items = self.buffer.get('registers')
        if not items:
            return
        news = []
        for item in items:
            news.append(item.copy())
        row = self.tree.currentRow

        self.insert_row(
            row+1,
            news,
        )

    def prepend_copy(self):
        if self.buffer is None:
            return
        row = self.tree.currentRow
        news = []
        for register in self.buffer:
            news.append(register.copy())
        self.insert_row(
            row,
            news,
        )

    def insert_row(self, row, items):
        root = self.model.itemFromIndex(self.tree.currentIndex()).parent()
        if root is None:
            root = self.model
            block = self.blocks
            is_root = True
        else:
            block = self.blocks[root.row()].registers
            is_root = False
        for item in reversed(items):
            cmd = TreeInsertCommand(
                widget=root,
                block=block,
                row=row,
                items=item,
                cols=self.cols,
                description='tree insertion',
                is_root=is_root
            )
            self.undoStack.push(cmd)

    def copy(self):
        try:
            values = {
                'blocks': [],
                'registers': []
            }
            for row, index in self.iterItemPerSelectedRow():
                if index.data(Qt.UserRole) == 'block':
                    values['blocks'].append(self.blocks[row].copy())
                else:
                    register = self.blocks[index.parent().row()].get_register(row)
                    values['registers'].append(register.copy())
            if not values:
                self.buffer = None
            else:
                self.buffer = values
        except Exception as e:
            print(traceback.format_exc())

    def moduleModify(self, index: QModelIndex):
        if not index.isValid():
            return
        item = self.model.itemFromIndex(index)
        if item.data(Qt.UserRole) == 'block':
            block = self.blocks[index.row()]
            dialog = InputDialog(
                parent=self,
                title=GUI_NAME,
                inputs=block_columns,
                values=block,
                label='Module Information',
                resize=[600, 400]
            )
            info, save = dialog.get()
            if save:
                block.update(info)
                block.viewUpdate()

    def cut(self):
        self.copy()
        self.remove()

    def remove(self):
        if not self.blocks:
            return
        items = {}
        for row, index in self.iterItemPerSelectedRow():
            item = self.model.itemFromIndex(index)
            if not index.isValid():
                continue
            if item.data(Qt.UserRole) == 'block':
                if row >= len(self.blocks):
                    continue
                items[row] = [self.model, self.blocks]
            else:
                index = index.parent()
                items[row] = [self.model.itemFromIndex(index), self.blocks[index.row()].registers]
        if not items:
            return
        for row in sorted(items.keys(), reverse=True):
            widget = items[row][0]
            cmd = TreeRemoveCommand(
                widget=widget,
                row=row,
                description='remove',
                block=items[row][1]
            )
            self.undoStack.push(cmd)

    def setFocus(self):
        self.tree.setFocus()

    # def saveChanges(self):
    #     for row in range(self.model.rowCount()):
    #         item = self.model.item(row, 0)
    #         block = self.blocks[row]
    #         if item.hasChildren():
    #             for itemRow in range(item.rowCount()):
    #                 register = block.get_register(itemRow)
    #                 for col, header in enumerate(self.cols.keys()):
    #                     child = item.child(itemRow, col)
    #                     register[header] = child.text()

    def clearSelection(self):
        self.tree.clearSelection()

    def addAnalyzer(self):
        index = self.tree.currentIndex()
        if not index.isValid():
            return
        if index.data(Qt.UserRole) == 'block':
            return

        block_index = index.parent().row()
        address, _ = self.blocks[block_index].get_address_space(index.row())
        self.addAnalyzerTrigger.emit(address)

    def shiftBy(self):
        dialog = InputDialog(
            title=GUI_NAME,
            parent=self,
            label='You can use negative value. For example: -0x4, -8',
            inputs={
                "shift by": {},
            }
        )
        values, save = dialog.get()
        if not save:
            return
        # print(values)
        rows = {}
        for row, index in self.iterItemPerSelectedRow():
            item = self.model.itemFromIndex(index)
            if item.data(Qt.UserRole) == 'block':
                continue
            rows[row] = item
        index = self.tree.currentIndex().parent()
        if index.data(Qt.UserRole) != 'block':
            return
        cmd = TreeShiftCommand(
            rows=rows,
            registers=self.blocks[index.row()].registers,
            description='register shift',
            value=values.get('shift by', '0x0').strip()

        )
        self.undoStack.push(cmd)


