import copy
from PyQt5.QtCore import QModelIndex, Qt, QSizeF, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLineEdit, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox, QMenu
from PyQt5.QtWidgets import QAction, QHeaderView
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QFont, QColor, QContextMenuEvent
from .widgets import TableLineEditDelegate, TableListViewDelegate, TableTextEditDelegate
from .widgets import TableView
from .CommandStack import TableRemoveCommand, TableInsertCommand, DataChanged
from RegisterProfileEditor.config import field_contextmenu, new_field, reserve_field

import qtawesome as qta


class FieldView(QWidget):

    keywordHighlight = pyqtSignal(str)
    tableSaved = pyqtSignal()

    def __init__(self, cols: dict, items: [dict], parent=None, undoStack=None):

        super(FieldView, self).__init__(parent)
        self.buffer = None
        self.cols = cols
        self.items = items
        self.table = TableView(self)
        self.model = QStandardItemModel()
        self.undoStack = undoStack
        self.table.setUndoStack(self.undoStack)
        self.table.setModel(self.model)
        # self.table.setWordWrap(True)
        self.entry = QLineEdit(self)
        self.entry.setClearButtonEnabled(True)
        self.entry.setPlaceholderText('Filter table by ...')
        self.entry.setMinimumWidth(300)
        self.entry.setMinimumHeight(35)
        self.caption = QLabel('')
        # self.hidden_rows = []
        # self.valid_index = []
        self.col_resize = []
        self.is_reserve_show = QCheckBox(self)
        self.linting_en = QCheckBox(self)
        self.linting_en.setCheckState(Qt.Checked)

        hbox = QHBoxLayout()
        hbox.addWidget(self.is_reserve_show)
        hbox.addWidget(QLabel("Show RESERVED"))
        hbox.addWidget(self.linting_en)
        hbox.addWidget(QLabel("Linting"))
        hbox.addWidget(self.entry)
        hbox.addStretch(1)
        vbox = QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.caption)
        vbox.addWidget(self.table)
        self.setLayout(vbox)

        self.entry.textChanged.connect(self.tableFilter)
        self.is_reserve_show.stateChanged.connect(self.show_reserved)
        self.create_ui()

    def show_reserved(self):
        self.create_rows()

    def dataBeforeChangedEvent(self, index: QModelIndex, new: str, old: str):
        if not index.isValid():
            return
        row = index.row()
        col = index.column()
        cmd = DataChanged(
            widget=self.model,
            newtext=new,
            oldtext=old,
            index=index,
            description=f'Table Data changed at ({row}, {col})'
        )
        self.undoStack.push(cmd)

    def chgRowHeight(self, index: QModelIndex, size: QSizeF):
        if not index.isValid():
            return
        row = index.row()
        self.table.setRowHeight(row, size.height())

    def create_ui(self, items: list=None):
        self.create_actions()
        self.create_cols()
        self.create_rows(items)

    def create_rows(self, items: list=None, caption=None):
        if items is not None:
            self.items = items
        if caption is not None:
            self.caption.setText(caption)
        self.table.resetMatches()
        self.model.removeRows(0, self.model.rowCount())

        for row, item in enumerate(self.items):
            is_reserved = (item.get('Field', '').lower() == 'reserved') & \
                          (self.is_reserve_show.checkState() == Qt.Unchecked)
            rows = []
            for col in self.cols.keys():
                cell = QStandardItem(str(item[col]))
                if is_reserved:
                    cell.setData('reserved', Qt.UserRole)
                rows.append(cell)
            self.model.appendRow(rows)

            # to adjust row size which is better than resizeRowToContents
            # use self.chgRowHeight to adjust base on QTextEdit height
            # the sizeHint in QStyledItemDelegate cannot get correct height
            # due to text wrap
            for col in self.col_resize:
                self.table.openPersistentEditor(self.model.index(row, col))
                self.table.closePersistentEditor(self.model.index(row, col))

        if self.entry.text().strip() != "":
            self.tableFilter()

    def create_cols(self):
        self.model.setHorizontalHeaderLabels(self.cols.keys())
        # self.model.head
        for col, config in enumerate(self.cols.values()):
            widget = config.get('widget', None)
            width = config.get('width', None)
            resize = config.get('resize', None)
            if width:
                self.table.setColumnWidth(col, width)
            if resize:
                self.table.horizontalHeader().setSectionResizeMode(
                    col,
                    QHeaderView.Stretch
                )
                self.col_resize.append(col)

            if widget == "list":
                items = config.get('items', [])
                delegate = TableListViewDelegate(self.table, items)

            elif widget == 'textEdit':
                delegate = TableTextEditDelegate(self.table)
                delegate.sizeChanged.connect(
                    self.chgRowHeight
                )

            else:
                validator = config.get('type', None)
                items = config.get('items', None)
                delegate = TableLineEditDelegate(
                    self.table,
                    items,
                    validator,
                    minValue=config.get('minValue', 0),
                    maxValue=config.get('maxValue', 31)
                )

            self.table.setItemDelegateForColumn(col, delegate)
            delegate.dataBeforeChanged.connect(
                self.dataBeforeChangedEvent
            )
            self.keywordHighlight.connect(delegate.setKeyword)

    def create_actions(self):
        for config in field_contextmenu:
            sc = config.get('shortcut', None)
            if sc is None:
                continue
            label = config.get('label')
            qaction = QAction(label, self.table)
            # func = actions.pop()
            func = getattr(self, config.get('action'))
            qaction.setShortcut(sc)
            qaction.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            qaction.triggered.connect(func)
            self.addAction(qaction)

    def tableFilter(self):
        text = self.entry.text().strip()
        self.keywordHighlight.emit(text)
        self.table.matches = []
        for row in range(self.model.rowCount()):
            self.table.hideRow(row)
        for col in range(self.model.columnCount()):
            matches = self.model.findItems(
                text, Qt.MatchContains,
                column=col,
            )
            for match in matches:
                self.table.showRow(match.row())
            self.table.matches.extend(matches)

    def contextMenuEvent(self, event: QContextMenuEvent):

        actions = {}
        menu = QMenu(self.table)
        for config in field_contextmenu:
            label = config.get('label')
            buffer = config.get('buffer', False)
            action = menu.addAction(label)
            icon = config.get('icon', None)
            if buffer and self.buffer is None:
                action.setEnabled(False)
            if icon:
                action.setIcon(qta.icon(icon, color='gray'))
            sc = config.get('shortcut', None)
            func = getattr(self, config.get('action'))
            if sc:
                action.setShortcut(sc)
            actions[action] = func

        action = menu.exec_(self.mapToGlobal(event.pos()))
        func = actions.get(action)
        if callable(func):
            func()

    def iterSelectedRows(self):
        indexes = self.table.selectedIndexes()
        for i in range(0, len(indexes), len(self.cols.keys())):
            yield indexes[i].row()

    @property
    def selectedRows(self):
        indexes = self.table.selectedIndexes()
        rows = []
        for i in range(0, len(indexes), len(self.cols.keys())):
            rows.append(indexes[i].row())
        return rows

    def iterRowValues(self):
        # if headers is None:
        headers = self.cols.keys()
        for row in range(self.model.rowCount()):
            yield row, {
                header: self.model.item(row, col).text().strip() for col, header in enumerate(headers)
            }

    def searchAndReplace(self):
        self.table.dialog.show()

    def remove(self):
        if not self.items:
            return
        items = {}
        for row in sorted(self.selectedRows):
            # self.model.removeRow(row)
            rows = []
            for col in range(len(self.cols.keys())):
                rows.append(
                    self.model.item(row, col).text()
                )
            items[row] = rows
        if not items:
            return
        cmd = TableRemoveCommand(
            description='remove command',
            widget=self.table,
            items=items
        )
        # self.table.selectRow(rows[-1])
        self.undoStack.push(cmd)

    def copy(self):
        values = []
        for row in self.iterSelectedRows():
            rows = {}
            for col, header in enumerate(self.cols.keys()):
                rows[header] = self.model.item(row, col).text()
            values.append(rows)
        self.buffer = values

    def cut(self):
        self.copy()
        self.remove()

    def insertRow(self, row, item):

        cmd = TableInsertCommand(
            widget=self.table,
            row=row,
            description='Insert table',
            items=[
                str(item.get(col, config.get('default', ''))) for col, config in self.cols.items()
            ]
        )
        self.undoStack.push(cmd)

    def append_new(self):
        row = self.table.currentRow
        col = list(self.cols.keys()).index('LSB')
        lsb = int(self.model.index(row, col).data()) - 1
        if lsb < 0:
            lsb = 0
        new = {"MSB": lsb, "LSB": lsb}
        self.insertRow(
            row+1,
            item={**new_field, **new}
        )

    def append_copy(self):
        if self.buffer is None:
            return
        row = self.table.currentRow + 1
        for item in reversed(self.buffer):
            self.insertRow(
                row,
                item=copy.deepcopy(item)
            )

    def prepend_new(self):
        row = self.table.currentRow
        col = list(self.cols.keys()).index('MSB')
        msb = int(self.model.index(row, col).data()) + 1
        if msb > 31:
            msb = 31
        new = {"MSB": msb, "LSB": msb}
        self.insertRow(
            row,
            item={**new_field, **new}
        )

    def prepend_copy(self):
        if self.buffer is None:
            return
        row = self.table.currentRow
        for item in reversed(self.buffer):
            self.insertRow(
                row,
                item=copy.deepcopy(item)
            )

    def linting(self) -> (bool, str):
        msg = str()
        if not self.items or (self.linting_en.checkState() == Qt.Unchecked):
            return True, msg
        success = False
        msb = int(self.cols.get('MSB').get('maxValue', 31))
        run = None
        for row, values in self.iterRowValues():
            row += 1
            run = row
            for header, config in self.cols.items():
                require = config.get('require', True)
                value = values.get(header, '')
                if require:
                    if value == '':
                        msg = f'Value Error at Row: {row}, column: {header}\n' \
                              f'This entry cannot be empty'
                        success = False
                        break
                if header == "MSB":
                    value = int(value)
                    lsb = int(values.get('LSB', msb))
                    success = (value == msb) & (msb >= lsb)
                    msb = lsb - 1
                    if self.model.rowCount() == row and success:
                        success = lsb == int(self.cols.get('LSB').get('minValue', 0))
                    if not success:
                        msg = f'Index Error at Row: {row}\n' \
                              f'Please Check MSB or LSB value'
                        break
            if not success:
                break
        if run is None:
            msg = 'Fields cannot be empty.\n'
        return success, msg

    def reserved(self):
        max_value = int(self.cols.get('MSB').get('maxValue', 31))
        min_value = int(self.cols.get('LSB').get('minValue', 0))
        reserves = {}
        for row, values in self.iterRowValues():
            msb = int(values['MSB'])
            lsb = int(values['LSB'])
            if msb != max_value:
                reserves[row] = {**reserve_field, **dict(MSB=max_value, LSB=msb+1)}
            max_value = lsb - 1
        if max_value >= 0:
            reserves[self.model.rowCount()] = {**reserve_field, **dict(MSB=max_value, LSB=min_value)}

        for row in sorted(reserves.keys(), reverse=True):
            self.insertRow(
                row,
                reserves[row]
            )

    def saveTable(self):

        self.items.clear()
        for row, values in self.iterRowValues():
            self.items.append(values)
        self.tableSaved.emit()

    def checkTableChanged(self):
        if len(self.items) != self.model.rowCount():
            return True
        else:
            for row, values in self.iterRowValues():
                old = self.items[row]
                if old != values:
                    return True
            else:
                return False

    def setFocus(self, r=None):
        self.table.setFocus()
