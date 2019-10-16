from PyQt5.QtWidgets import QWidget, QLineEdit, QCompleter, QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox
from PyQt5.QtWidgets import QScrollArea, QMenu, QHeaderView
from PyQt5.QtCore import Qt, QStringListModel, QModelIndex, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QFont, QColor, QContextMenuEvent
from .widgets import LineEditDelegate, TableView, TextEditDelegate


class MetaHeaderView(QHeaderView):
    # source code, and do some miner changes
    # https://www.qtcentre.org/threads/12835-How-to-edit-Horizontal-Header-Item-in-QTableWidget?p=224376#post224376
    def __init__(self, orientation, parent=None):
        super(MetaHeaderView, self).__init__(orientation, parent)
        # self.setMovable(True)
        # self.setClickable(True)
        self.setSectionsClickable(True)

        # This block sets up the edit line by making setting the parent
        # to the Headers Viewport.
        self.line = QLineEdit(parent=self.viewport())  # Create
        self.line.setAlignment(Qt.AlignTop)  # Set the Alignmnet
        self.line.setHidden(True)  # Hide it till its needed
        # This is needed because I am having a werid issue that I believe has
        # to do with it losing focus after editing is done.
        self.line.blockSignals(True)
        self.sectionedit = 0
        # Connects to double click
        self.sectionDoubleClicked.connect(self.editHeader)
        self.line.editingFinished.connect(self.doneEditing)

    def doneEditing(self):
        # This block signals needs to happen first otherwise I have lose focus
        # problems again when there are no rows
        self.line.blockSignals(True)
        self.line.setHidden(True)
        newname = self.line.text()
        self.model().setHeaderData(self.sectionedit, Qt.Horizontal, newname)
        self.setCurrentIndex(QModelIndex())

    def editHeader(self, section):
        # This block sets up the geometry for the line edit
        edit_geometry = self.line.geometry()
        edit_geometry.setWidth(self.sectionSize(section))
        edit_geometry.moveLeft(self.sectionViewportPosition(section))
        self.line.setGeometry(edit_geometry)
        self.line.setText(str(self.model().headerData(section, Qt.Horizontal)))
        self.line.setHidden(False)  # Make it visiable
        self.line.blockSignals(False)  # Let it send signals
        self.line.setFocus()
        self.line.selectAll()
        self.sectionedit = section



class AnalyzerView(QWidget):

    def __init__(self, cols: dict, parent=None, address_space: dict=None):
        super(AnalyzerView, self).__init__(parent)
        self.cols = cols
        self.address_space = address_space
        self.dataformat = {}

        self.entry = QLineEdit(self)
        self.entry.setClearButtonEnabled(True)
        self.entry.setPlaceholderText('Base Address or Register Name')
        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.entry.setCompleter(completer)
        self.entry.setMinimumWidth(500)

        self.close_btn = QPushButton('X', self,)
        self.close_btn.setMaximumWidth(40)
        hbox1 = QHBoxLayout()
        hbox1.addWidget(self.entry)
        hbox1.addStretch(1)
        # hbox1.addWidget()

        ctrl_box = QHBoxLayout()
        self.show_detail = QCheckBox('Show Detail', self)
        self.show_reserved = QCheckBox('Show Reserved', self)
        self.add_col = QPushButton('Add Column', self,)
        self.add_col.setDisabled(True)
        ctrl_box.addWidget(self.show_detail)
        # ctrl_box.addWidget(detail_label)
        ctrl_box.addWidget(self.show_reserved)
        ctrl_box.addWidget(self.add_col)
        ctrl_box.addStretch(1)
        ctrl_box.addWidget(self.close_btn)

        self.string_model = QStringListModel()
        completer.setModel(self.string_model)
        self.string_model.setStringList(self.address_space.keys())

        self.model = QStandardItemModel()
        self.table = TableView(self)
        self.table.setWordWrap(True)
        self.table.setModel(self.model)
        self.table.setHorizontalHeader(MetaHeaderView(Qt.Horizontal, parent=self.table))
        vbox = QVBoxLayout()
        vbox.addLayout(hbox1)
        # vbox.addWidget(self.entry)
        vbox.addLayout(ctrl_box)
        vbox.addWidget(self.table)
        self.setLayout(vbox)
        # self.table.horizontalHeader().setHidden(True)
        self.table.verticalHeader().setHidden(True)
        self.table.setShowGrid(False)

        # self.table.setMinimumHeight(600)
        self.reserved_row = []
        self.add_col.clicked.connect(self.add_column)
        self.close_btn.clicked.connect(self.close)
        self.show_detail.stateChanged.connect(self.detail)
        self.show_reserved.stateChanged.connect(self.hide_reserved)
        self.entry.textChanged.connect(self.create_rows)
        # self.table.dataChangedSignal.connect(self.test)
        self.default_col = list(self.cols.keys()).index('Default')
        self.create_cols()
        self.detail()

    def set_address_space(self, address):
        self.entry.setText(address)

    def dataChangeEvent(self, index_0: QModelIndex, new: str, old: str):
        if not index_0.isValid():
            return
        chg_row = index_0.row()
        chg_col = index_0.column()
        if chg_col < len(self.cols.keys()):
            return
        if chg_row == 0:
            item = self.model.itemFromIndex(index_0)
            item.setText(new)
            return
        last_row = self.model.rowCount()-1
        if chg_row != 0:
            item = self.model.item(0, chg_col)
            total = item.text().strip()
            if total == '':
                total = '0x0'

            total = self.tobinary(total, width=32)[::-1]

            total = list(total)
            # print(len(total), total)
            values = self.dataformat.get(chg_row)
            msb = values[0]
            lsb = values[1]
            width = msb - lsb + 1
            value_chg = new
            value_chg = list(self.tobinary(value_chg, width=width)[::-1])[0:width]
            total[lsb:msb+1] = value_chg
            total = ''.join(total[0:32])
            item.setText(self.binary2hex(total[::-1], width=8))
            item_chg = self.model.itemFromIndex(index_0)
            value_chg = ''.join(value_chg)[::-1]
            item_chg.setText(self.binary2hex(value_chg, width=width//4))
        else:
            total = new
            total = self.tobinary(total, width=32)[::-1]
            for row, values in self.dataformat.items():
                msb = values[0]
                lsb = values[1]
                width = msb - lsb + 1
                item = self.model.item(row, chg_col)
                item.setText(self.binary2hex(total[lsb:msb+1][::-1], width=width//4))

    def create_cols(self):
        rows = []

        for _ in self.cols.keys():
            cell = QStandardItem('')
            cell.setEditable(False)
            rows.append(cell)

        self.model.setHorizontalHeaderLabels(self.cols.keys())
        self.model.appendRow(rows)

    def create_rows(self):
        self.reserved_row = []
        adddress = self.entry.text()
        fields = self.address_space.get(adddress, None)
        if fields:
            self.model.clear()
            self.create_cols()
            # last_row = []
            for row, field in enumerate(fields):
                is_reserved = (field.get('Field', '') == 'RESERVED')
                rows = []
                if is_reserved:
                    self.reserved_row.append(row+1)
                for col in self.cols.keys():
                    cell = QStandardItem(str(field[col]))
                    cell.setEditable(False)
                    rows.append(cell)
                self.model.appendRow(rows)
            self.detail()
            self.dataformatting(fields)
            for _ in range(2):
                self.add_column()
            self.hide_reserved()
            self.table.setMinimumHeight(
                (self.model.rowCount()+1)*self.table.rowHeight(0)
            )
            self.add_col.setDisabled(False)

    def hide_reserved(self):
        # self.table.blockSignals(True)
        hide = self.show_reserved.checkState() == Qt.Unchecked
        for row in self.reserved_row:
            for col in range(self.model.columnCount()):
                # QStandardItem().st
                item = self.model.item(row, col)
                if hide:
                    item.setFont(QFont(self.font().family(), self.font().pointSize()*2//3))
                    item.setForeground(QColor.fromRgb(
                        204, 204, 204
                    ))
                else:
                    self.table.setStyleSheet("")
                    item.setFont(self.font())
                    item.setForeground(QColor.fromRgb(
                        0, 0, 0
                    ))
        # self.table.blockSignals(False)

    def add_column(self):

        self.model.appendColumn(
            [
                QStandardItem(self.dataformat[row][-1]) for row in range(self.model.rowCount())
            ]
        )

        self.table.setColumnWidth(self.model.columnCount()-1, 150)
        delegate = LineEditDelegate(
            self.table,
            validator='hex'
        )
        delegate.dataBeforeChanged.connect(self.dataChangeEvent)
        self.table.setItemDelegateForColumn(
            self.model.columnCount() - 1,
            delegate
        )
        header = self.table.horizontalHeader()
        # QHeaderView.edit
        # header.openPersistentEditor()
        self.hide_reserved()

    def detail(self):
        for col, (header, config) in enumerate(self.cols.items()):
            to_hide = ['Description', 'Testable', 'Public']
            width = config.get('width', None)
            if header in to_hide:
                if self.show_detail.checkState() != Qt.Checked:
                    self.table.hideColumn(col)
                else:
                    self.table.showColumn(col)
            if width:
                self.table.setColumnWidth(col, width)
            # self.table.resizeColumnToContents(col)

        for row in range(self.model.rowCount()):
            self.table.resizeRowToContents(row)
        # self.table.setMinimumHeight(self.table.size().height())

    def reload_address(self, address_space: dict):
        self.address_space = address_space
        self.string_model.setStringList(address_space.keys())

    def dataformatting(self, fields):
        self.dataformat = {}
        total = ''

        for row, field in enumerate(fields):
            row += 1
            msb = int(field.get('MSB'))
            lsb = int(field.get('LSB'))
            bitwidth = msb-lsb+1
            default = field.get('Default')

            try:
                default = self.tobinary(default, bitwidth)
                total += default
                default = self.binary2hex(default, width=bitwidth//4)
                self.dataformat[row] = [msb, lsb, default]
                # default = self.binary2hex(default)
            except Exception as e:
                self.dataformat[row] = [msb, lsb, '0x0']
        self.dataformat[0] = [31, 0, self.binary2hex(total, width=8)]
        self.model.item(0, self.default_col).setText(self.binary2hex(total, width=8))

    @staticmethod
    def binary2hex(binary: str, width: int):
        return f"0x{int(binary, 2):0{width}X}"

    def tobinary(self, value: str, width: int):
        try:
            value = value.lower().strip()
            if value == '' or value == '0x':
                return f"{0:0{width}b}"
            if value.startswith('0x'):
                return f"{int(value, 16):0{width}b}"
            else:
                return f"{int(value):0{width}b}"
        except Exception as e:
            return f"{0:0{width}b}"

    def contextMenuEvent(self, event: QContextMenuEvent):
        col = self.table.columnAt(event.pos().x())
        if col < len(self.cols):
            return
        menu = QMenu(self.table)

        delete = menu.addAction('Delete this column')
        # delete.setShortcut('Ctrl+D')
        # delete.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        action = menu.exec_(self.mapToGlobal(event.pos()))

        if action == delete:
            self.delete_column(col)

    def delete_column(self, col):
        self.model.removeColumn(col)


class AnalyzerWapper(QWidget):

    def __init__(self, cols: dict, parent=None, address_space: dict=None, reload: pyqtSignal=None):
        super(AnalyzerWapper, self).__init__(parent)
        self.add_analyzer_btn = QPushButton('Add Analyzer', self)
        self.cols = cols
        self.address_space = address_space
        self.scrollarea = QScrollArea(self)
        frame = QWidget(self)
        self.scrollarea.setWidget(frame)
        self.scrollarea.setWidgetResizable(True)
        # self.scrollarea.setFixedHeight(400)
        self.vbox = QVBoxLayout(frame)
        self.vbox.addWidget(self.add_analyzer_btn)
        self.reload = reload

        for _ in range(1):
            ana = AnalyzerView(parent=self, cols=self.cols, address_space=self.address_space)
            self.reload.connect(
                ana.reload_address
            )
            self.vbox.addWidget(ana)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.scrollarea)
        # self.setLayout(main_layout)

        self.add_analyzer_btn.clicked.connect(self.add_analyzer)
        self.reload.connect(self.reload_address)

    def add_analyzer(self, address=None):
        ana = AnalyzerView(parent=self, cols=self.cols, address_space=self.address_space)
        self.vbox.addWidget(
            ana
        )
        self.reload.connect(
            ana.reload_address
        )
        if isinstance(address, str):
            ana.set_address_space(address)

    def reload_address(self, address_space: dict):
        self.address_space = address_space
        # self.string_model.setStringList(address_space.keys())












