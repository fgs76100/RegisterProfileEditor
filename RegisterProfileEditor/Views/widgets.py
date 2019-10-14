from PyQt5.QtWidgets import QWidget, QTreeView, QTableView, QLineEdit, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QStyledItemDelegate, QTextEdit, QPlainTextEdit, QListWidget, QDialog, QDialogButtonBox
from PyQt5.QtWidgets import QFormLayout, QFileDialog, QMessageBox, QLabel, QPushButton, QCheckBox, QAbstractItemView
from PyQt5.QtWidgets import QUndoStack, QAbstractItemDelegate, QStyleOptionViewItem, QCompleter, QListWidgetItem
from PyQt5.QtWidgets import QTabWidget, QApplication, QStyle
from PyQt5.QtCore import QModelIndex, Qt, QAbstractItemModel, QStringListModel, QSizeF, pyqtSignal, QRunnable
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QValidator, QKeyEvent, QIntValidator, QTextCursor, QTextDocument, QAbstractTextDocumentLayout
from PyQt5.QtGui import QTextCharFormat, QPainter, QFont, QPalette, QColor, QMouseEvent, QTextCursor
import re
from functools import partial
from .CommandStack import ReplaceCommand
import json
from collections import OrderedDict


class HighlightDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super(HighlightDelegate, self).__init__(parent)
        # self.doc = QTextDocument(self)
        self.keyword = str()

    # def sizeHint(self, option, index: QModelIndex):
    #     # sizeHint is crucial for table adjust height
    #     # set text up to detect correct size
    #     self.doc.setTextWidth(option.rect.width())
    #     self.doc.setPlainText(index.data())
    #     # self.doc.width
    #     if index.row() == 0:
    #         print(
    #             self.doc.size().height(), self.doc.size().width(),
    #         )
    #     return QSize(self.doc.idealWidth(), self.doc.size().height()+30)

    def paint(self, painter: QPainter, option, index):
        # reference following link
        # https://stackoverflow.com/questions/53353450/how-to-highlight-a-words-in-qtablewidget-from-a-searchlist
        # https://stackoverflow.com/questions/34623036/implementing-a-delegate-for-wordwrap-in-a-qtreeview-qt-pyside-pyqt
        painter.save()
        doc = QTextDocument(self)
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        doc.setPlainText(options.text)
        # keyword = index.data(Qt.UserRole)
        # if self.keywords:
        self.keywordHighlight(doc)
        options.text = ""
        style = QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)  # for selection highlight

        ctx = QAbstractTextDocumentLayout.PaintContext()
        if index.data(Qt.UserRole) == 'reserved':
            ctx.palette.setColor(QPalette.Text, QColor.fromRgb(204, 204, 204))
            doc.setDefaultFont(QFont(option.font.family(), option.font.pointSize()*2//3))

        else:
            doc.setDefaultFont(option.font)

        textRect = option.rect
        # margin = 4
        # textRect.setTop(textRect.top() + margin)
        textRect.setTop(textRect.top())
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))

        doc.setTextWidth(option.rect.width())
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def keywordHighlight(self, doc):
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        fmt = QTextCharFormat()
        fmt.setBackground(Qt.yellow)

        highlightCursor = QTextCursor(doc)
        while not highlightCursor.isNull() and not highlightCursor.atEnd():
            highlightCursor = doc.find(self.keyword, highlightCursor)
            if not highlightCursor.isNull():
                highlightCursor.mergeCharFormat(fmt)
        cursor.endEditBlock()

    def setKeyword(self, keyword):
        self.keyword = keyword


class InfoDialog(QDialog):
    def __init__(self, title, parent=None):
        super(InfoDialog, self).__init__(parent)
        self.resize(800, 400)
        self.setWindowTitle(title)
        btn = QDialogButtonBox.Ok
        self.btnbox = QDialogButtonBox(btn, self)
        self.btnbox.setHidden(True)
        self.plainText = QPlainTextEdit(self)

        vbox = QVBoxLayout()
        vbox.addWidget(self.plainText)
        vbox.addWidget(self.btnbox)
        self.btnbox.accepted.connect(self.accept)
        self.done = False
        self.plainText.setReadOnly(True)
        self.thread_cnt = 0
        self.setLayout(vbox)
        # self.plainText.textChanged.connect(self.test)

    def upload_text(self, text):
        self.plainText.appendPlainText(text)
        self.highlihgter()

    def progress_done(self):
        self.btnbox.show()

    def highlihgter(self):
        highlight_rules = [
            ('INFO', Qt.darkBlue),
            ('Warning', Qt.darkYellow),
            ('Error', Qt.darkRed)
        ]

        cursor = self.plainText.textCursor()
        text = self.plainText.toPlainText()
        for keyword, color in highlight_rules:
            regex = QRegExp(keyword)
            index = regex.indexIn(text)
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            while index != -1:
                cursor.setPosition(index)
                cursor.movePosition(QTextCursor.EndOfWord, 1)
                cursor.mergeCharFormat(fmt)
                # Move to the next match
                pos = index + regex.matchedLength()
                index = regex.indexIn(text, pos)

    def accept(self):
        self.plainText.setPlainText('')
        self.btnbox.setHidden(True)
        super(InfoDialog, self).accept()

    def reject(self):
        self.plainText.setPlainText('')
        self.btnbox.setHidden(True)
        super(InfoDialog, self).reject()


class FunctionWorker(QRunnable):
    def __init__(self, callback: callable):
        super(FunctionWorker, self).__init__()
        self.callback = callback

    def run(self):
        self.callback()


class ModuleDialog(QDialog):

    def __init__(self, title, parent=None):
        super(ModuleDialog, self).__init__(parent)
        self.setWindowTitle(title)
        btn = QDialogButtonBox.Save | QDialogButtonBox.Cancel
        btnbox = QDialogButtonBox(btn, self)
        layout = QFormLayout()
        self.moduleName = QLineEdit(self)
        self.baseAddress = QLineEdit(self)
        self.moduleName.setPlaceholderText(
            "Module Name"
        )
        self.baseAddress.setPlaceholderText(
            "Base Address"
        )
        self.baseAddress.setText('0x')
        layout.addRow(
            QLabel("Module Name:"), self.moduleName
        )
        layout.addRow(
            QLabel("Base Address:"), self.baseAddress
        )
        layout.addWidget(btnbox)
        self.setLayout(layout)
        btnbox.accepted.connect(self.accept)
        btnbox.rejected.connect(self.reject)

    def get(self):
        save = False
        if self.exec_():
            save = True

        return {
            "ModuleName": self.moduleName.text(),
            "BaseAddress": self.baseAddress.text()
        }, save


class FileDialog:

    def __init__(self, parent, path=None):
        self.parent = parent
        self.path = path
        self.options = QFileDialog.Options()
        self.options |= QFileDialog.DontUseNativeDialog

    def askopenfile(self):
        filename, _ = QFileDialog.getOpenFileName(
            self.parent,
            "QFileDialog.getOpenFileName()",
            "",
            "Python Files (*.py);;All Files (*);;",
            options=self.options
        )

        return filename

    def askopenfiles(self):
        filenames, _ = QFileDialog.getOpenFileNames(
            self.parent,
            "Chose files",
            "",
            "Excel Files (*.xls);;JSON Files (*.json);;All Files (*);;",
            "Excel Files (*.xls)",
            options=self.options
        )
        return filenames

    def askopendir(self):
        directory = QFileDialog.getExistingDirectory(
            self.parent,
            "Chose a directory",
            "",
            options=self.options
        )
        return directory

    def asksavefile(self, ftypes=None, initial_ftype=None) -> (str, str):
        if ftypes is None:
            ftypes = initial_ftype
        filename, ftype = QFileDialog.getSaveFileName(
            self.parent,
            "Save as",
            "",
            ftypes,
            initial_ftype,
            options=self.options
        )
        return filename, ftype


class HexValidator(QValidator):
    def __init__(self, parent=None):
        super(HexValidator, self).__init__(parent)

    def validate(self, p_str, p_int):
        pattern = re.compile('[0-9a-fA-FxX]+$')
        if p_int == 0:
            return QValidator.Intermediate, p_str, p_int
        if not pattern.match(p_str):
            return QValidator.Invalid, p_str, p_int
        pattern = re.compile('^0[xX][0-9a-fA-F]*$')
        if pattern.match(p_str):
            return QValidator.Acceptable, p_str, p_int
        else:
            pattern = re.compile('[0-9a-fA-F]+$')
            if pattern.match(p_str):
                return QValidator.Intermediate, p_str, p_int
            else:
                return QValidator.Invalid, p_str, p_int

    def fixup(self, p_str):
        return '0x'+p_str


class TextEdit(QTextEdit):

    def __init__(self, parent):
        super(TextEdit, self).__init__(parent)
        self.setTabChangesFocus(True)

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.ShiftModifier:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.clearFocus()
                self.focusPreviousChild()
                self.focusNextChild()
                return
        else:
            super(TextEdit, self).keyPressEvent(event)

    def text(self):
        return self.toPlainText()


class ListView(QListWidget):

    def __init__(self, parent=None):
        super(ListView, self).__init__(parent=parent)

    def mouseDoubleClickEvent(self, *args, **kwargs):
        # text = self.currentItem().text()
        self.setCurrentItem(self.currentItem())
        self.clearFocus()
        self.focusPreviousChild()
        self.focusNextChild()


class SearchAndReplace(QDialog):
    def __init__(self, parent=None):
        super(SearchAndReplace, self).__init__(parent)
        self.setWindowTitle('Search and Replace')
        self.nextBotton = QPushButton("Next")
        self.repalceBotton = QPushButton("Replace")
        self.repalceAllButton = QPushButton("Replace all")
        leave = QPushButton("Quit")
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.nextBotton)
        hbox.addWidget(self.repalceBotton)
        hbox.addWidget(self.repalceAllButton)
        # hbox.addWidget(leave)
        self.msg = QLabel("No Match Found")
        self.msg.setHidden(True)
        vbox = QVBoxLayout()
        vbox.addWidget(self.msg)
        self.textToSearch = QLineEdit(self)
        self.textToReplace = QLineEdit(self)
        self.caseSensitive = QCheckBox(self)
        self.caseSensitive.setCheckState(Qt.Checked)
        self.regxp = QCheckBox(self)
        checkbox_layout = QHBoxLayout()
        form = QFormLayout()
        form.addRow(QLabel("Search for:"), self.textToSearch)
        form.addRow(QLabel("Replace with"), self.textToReplace)
        # form.addRow(self.caseSensitive, QLabel("CaseSensitive"))
        checkbox_layout.addStretch(1)
        checkbox_layout.addWidget(self.caseSensitive)
        checkbox_layout.addWidget(QLabel("Case Sensitive"))
        checkbox_layout.addWidget(self.regxp)
        checkbox_layout.addWidget(QLabel('Match Exactly'))
        vbox.addLayout(form)
        vbox.addLayout(checkbox_layout)
        vbox.addLayout(hbox)
        hbox_leave = QHBoxLayout()
        hbox_leave.addStretch(1)
        hbox_leave.addWidget(leave)
        vbox.addLayout(hbox_leave)
        # vbox.addWidget(leave)
        leave.clicked.connect(self.reject)
        self.setLayout(vbox)

    def noMatchFound(self):
        self.msg.setHidden(False)
        # self.textToSearch.setPalette(
        #     QPalette.Background., Qt.red
        # )
        self.textToSearch.setStyleSheet(
            """
            background: red
            """
        )

    def beginToSearch(self):
        self.msg.setHidden(True)
        self.textToSearch.setStyleSheet("")


class TableView(QTableView):
    def __init__(self, parent):
        super(TableView, self).__init__(parent=parent)

        self.setShowGrid(False)
        self.setAlternatingRowColors(True)

        # self.setDragEnabled(True)
        # self.setDropIndicatorShown(True)
        # self.setDragDropOverwriteMode(False)
        # self.setAcceptDrops(True)
        # self.viewport().setAcceptDrops(True)

        # self.setDragDropMode(QAbstractItemView.InternalMove)

        # self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # self.verticalHeader().setMinimumWidth(40)
        # self.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # QHeaderView.setsize
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked
        )
        self.matches = []
        self.undoStack = QUndoStack()
        self.dialog = SearchAndReplace(self)
        self.dialog.nextBotton.clicked.connect(self.nextMatch)
        self.dialog.caseSensitive.stateChanged.connect(self.resetMatches)
        self.dialog.regxp.stateChanged.connect(self.resetMatches)
        self.dialog.textToSearch.textChanged.connect(self.resetMatches)
        self.dialog.repalceBotton.clicked.connect(self.replace)
        self.dialog.repalceAllButton.clicked.connect(self.replaceAll)
        self.current_match = None

    @property
    def currentRow(self):
        return self.currentIndex().row()

    def resetMatches(self):
        self.matches = []
        self.current_match = None

    def setUndoStack(self, stack: QUndoStack):
        self.undoStack = stack

    def searchTable(self, text):
        if self.dialog.isVisible():
            self.dialog.beginToSearch()
            model = self.model()
            if self.dialog.regxp.checkState() == Qt.Checked:
                option = Qt.MatchExactly
            else:
                option = Qt.MatchContains
            if self.dialog.caseSensitive.checkState() == Qt.Checked:
                option |= Qt.MatchCaseSensitive

            for col in range(model.columnCount()):
                matches = model.findItems(
                    text, option,
                    column=col,
                )
                self.matches.extend(matches)
            if not self.matches:
                # self.dialog.msg.setHidden(False)
                self.dialog.noMatchFound()
                return False
        return True

    def focusInEvent(self, *args, **kwargs):
        # if not self.model().hasChildren():
        #     self.focusPreviousChild()
        if not self.selectedIndexes():
            self.selectRow(0)
        # print(self.model())
        # print()
        super(TableView, self).focusInEvent(*args, **kwargs)

    def nextMatch(self):
        if self.dialog.isVisible():
            if self.current_match is not None:
                self.matches.append(self.current_match)
            textToSearch = self.dialog.textToSearch.text()
            if textToSearch != '':
                found = True
                if not self.matches:
                    found = self.searchTable(textToSearch)
                if not found:
                    return
                # self.dialog.msg.setHidden(True)
                self.current_match = self.matches.pop(0)
                index = self.model().indexFromItem(self.current_match)
                self.selectionModel().clearSelection()
                self.setCurrentIndex(index)
        self.raise_()
        self.activateWindow()

    def replaceAll(self):
        # self.nextMatch()
        while True:
            if self.replace():
                break

    def replace(self):
        if self.current_match is not None:
            textToSearch = self.dialog.textToSearch.text()
            textToReplace = self.dialog.textToReplace.text()
            index = self.currentIndex()
            model = self.model()
            item = model.itemFromIndex(index)
            old = item.text()
            if self.dialog.caseSensitive.checkState() == Qt.Checked:
                pattern = re.compile(textToSearch)
            else:
                pattern = re.compile(textToSearch, re.IGNORECASE)
            new = pattern.sub(textToReplace, old)
            self.undoStack.push(ReplaceCommand(
                widget=self,
                new=new,
                old=old,
                index=index,
                description='table replace command'
            ))
            self.current_match = None
            if not self.matches:
                # found = self.searchTable(textToSearch)
                # if not found:
                self.dialog.raise_()
                self.dialog.activateWindow()
                return True
            else:
                self.nextMatch()
        else:
            self.nextMatch()
        return False

    def keyPressEvent(self, e: QKeyEvent):
        # table state
        # https://doc.qt.io/archives/qt-4.8/qabstractitemview.html#State-enum
        state = self.state()
        key = e.key()
        index = self.currentIndex()
        if key == Qt.Key_N:
            self.nextMatch()
            return
        # if e.modifiers() == Qt.ControlModifier and key == Qt.Key_R:
        #     self.dialog.show()
        elif key == Qt.Key_R:
            if self.dialog.isVisible():
                self.replace()
                return

        if isinstance(self.focusWidget(), QTextEdit):
            if key == Qt.Key_Tab:
                if state == QAbstractItemView.EditingState:
                    self.closeEditor(None, QAbstractItemDelegate.EditNextItem)
                    return

            if key == Qt.Key_Backtab:  # shift + tab
                if state == QAbstractItemView.EditingState:
                    self.closeEditor(None, QAbstractItemDelegate.EditPreviousItem)
                    return
        if state == QAbstractItemView.NoEditTriggers:
            if key in (Qt.Key_I, Qt.Key_S):
                self.edit(index)
                return

            if key == Qt.Key_G:  # press shift+g go to bottom of row
                if e.modifiers() == Qt.ShiftModifier:
                    row_cnt = self.model().rowCount() - 1
                    sibling = index.sibling(row_cnt, index.column())

                else:  # press g go to top of row
                    sibling = index.sibling(0, index.column())
                self.setCurrentIndex(sibling)
                return

        pre_index = index

        super(TableView, self).keyPressEvent(e)

        index = self.currentIndex()

        if pre_index == index:
            return
        if state == QAbstractItemView.EditingState:
            if e.key() in (Qt.Key_Up, Qt.Key_Down):
                self.edit(index)


class TreeView(QTreeView):

    def __init__(self, parent):
        super(TreeView, self).__init__(parent=parent)

        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.setEditTriggers(
            # QAbstractItemView.AnyKeyPressed | QAbstractItemView.DoubleClicked
            QAbstractItemView.DoubleClicked
        )

    @property
    def currentRow(self):
        return self.currentIndex().row()

    @property
    def currentColum(self):
        return self.currentIndex().column()

    def keyPressEvent(self, e: QKeyEvent):
        # table state
        # https://doc.qt.io/archives/qt-4.8/qabstractitemview.html#State-enum
        state = self.state()
        key = e.key()
        index = self.currentIndex()
        item = self.model().itemFromIndex(index)
        if state == QAbstractItemView.NoEditTriggers:
            if key == Qt.Key_E:
                self.expandAll()
                return
            if key == Qt.Key_C:
                self.collapseAll()
                return
            if key in (Qt.Key_S, Qt.Key_I):
                # item.setData(
                #     's', Qt.UserRole
                # )
                self.edit(index)
                return

            if key == Qt.Key_G:  # press shift+g go to bottom of row
                if e.modifiers() == Qt.ShiftModifier:
                    model = self.model().itemFromIndex(index.parent())
                    if model is None:
                        model = self.model()
                    row_cnt = model.rowCount() - 1
                    sibling = index.sibling(row_cnt, index.column())

                else:  # press g go to top of row
                    sibling = index.sibling(0, index.column())
                self.setCurrentIndex(sibling)
                return

        pre_index = index

        super(TreeView, self).keyPressEvent(e)

        index = self.currentIndex()

        if pre_index == index:
            return
        if e.key() in (Qt.Key_Up, Qt.Key_Down):
            if state == QAbstractItemView.EditingState:
                self.edit(index)
                # QStandardItemModel.row

    def moveCursor(self, action, modifiers):
        if action == QAbstractItemView.MoveNext:
            index = self.currentIndex()
            if index.isValid():
                if index.column() + 1 < self.model().columnCount():
                    return index.sibling(index.row(), index.column() + 1)
                elif index.row() + 1 < self.model().rowCount(index.parent()):
                    return index.sibling(index.row() + 1, 0)
                else:
                    return QModelIndex()

        elif action == QAbstractItemView.MovePrevious:
            index = self.currentIndex()
            if index.isValid():
                if index.column() >= 1:
                    return index.sibling(index.row(), index.column() - 1)
                elif index.row() >= 1:
                    return index.sibling(index.row() - 1, self.model().columnCount() - 1)
                else:
                    return QModelIndex()
        return super(TreeView, self).moveCursor(action, modifiers)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        index = self.currentIndex()
        item = self.model().itemFromIndex(index)
        if item.data(Qt.UserRole) == 'dialog':
            self.doubleClicked.emit(index)
            return
        super(TreeView, self).mouseDoubleClickEvent(event)

    # def closeEditor(self, editor: QWidget, hint):
    #     if isinstance(editor, TextEdit):
    #         return super(TreeView, self).closeEditor(editor, QAbstractItemDelegate.EditNextItem)
    #     return super(TreeView, self).closeEditor(editor, hint)


class ListViewDelegate(QStyledItemDelegate):

    dataBeforeChanged = pyqtSignal(QModelIndex, str, str)

    def __init__(self, parent=None, items: list=None):
        super(ListViewDelegate, self).__init__(parent=parent)
        self.items = items

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex):

        editor = ListView(parent)
        return editor

    def setEditorData(self, editor: QListWidget, index: QModelIndex):

        for item in self.items:
            editor.addItem(QListWidgetItem(item))
        data = index.data()
        if data in self.items:
            editor.setCurrentRow(self.items.index(data))

    def setModelData(self, editor: QListWidget, model: QAbstractItemModel, index: QModelIndex):
        editor_text = editor.currentItem().text()
        index_text = index.data()
        if index_text != editor_text:
            self.dataBeforeChanged.emit(index, editor_text, index_text)

    def updateEditorGeometry(self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex):
        editor.setGeometry(
            option.rect
        )
        editor.setMinimumHeight(len(self.items)*25)


class TextEditDelegate(QStyledItemDelegate):

    sizeChanged = pyqtSignal(QModelIndex, QSizeF)
    dataBeforeChanged = pyqtSignal(QModelIndex, str, str)

    def __init__(self, parent=None):
        super(TextEditDelegate, self).__init__(parent=parent)

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex):
        editor = TextEdit(parent)
        editor.document().documentLayout().documentSizeChanged.connect(
            partial(self.sizeChangedEvent, index)
        )
        return editor

    def setEditorData(self, editor: TextEdit, index: QModelIndex):
        text = index.data()
        if text is None:
            text = ''
        editor.setText(text+'\n')
        # editor.setPlainText(text+'\n')
        editor.moveCursor(QTextCursor.End)

    def setModelData(self, editor: TextEdit, model: QAbstractItemModel, index: QModelIndex):
        editor_text = editor.toPlainText().strip()
        index_text = index.data()

        if index_text != editor_text:
            self.dataBeforeChanged.emit(index, editor_text, index_text)

    def updateEditorGeometry(self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex):
        editor.setGeometry(
            option.rect
        )

    def sizeChangedEvent(self, row, size: QSizeF):
        self.sizeChanged.emit(row, size)


class LineEditDelegate(QStyledItemDelegate):

    dataBeforeChanged = pyqtSignal(QModelIndex, str, str)

    def __init__(self, parent=None, items: list=None, validator: str=None, minValue=0, maxValue=31):
        super(LineEditDelegate, self).__init__(parent=parent)
        self.items = items
        if validator == 'int':
            self.validator = QIntValidator(int(minValue), int(maxValue))
        elif validator == 'hex':
            self.validator = HexValidator()
        else:
            self.validator = None

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex):
        editor = QLineEdit(parent)

        if self.items:
            completer = QCompleter()
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            editor.setCompleter(completer)
            model = QStringListModel()
            completer.setModel(model)
            model.setStringList(self.items)

        if self.validator is not None:
            editor.setValidator(self.validator)

        return editor

    def setEditorData(self, editor: QLineEdit, index: QModelIndex):
        editor.setText(
            index.data()
        )

    def setModelData(self, editor: QLineEdit, model: QAbstractItemModel, index: QModelIndex):
        editor_text = editor.text()
        index_text = index.data()
        if index_text != editor_text:
            self.dataBeforeChanged.emit(index, editor_text, index_text)

    def updateEditorGeometry(self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex):
        editor.setGeometry(
            option.rect
        )

    def addItem(self, item):
        if item not in self.items:
            self.items.append(item)


class TableLineEditDelegate(LineEditDelegate, HighlightDelegate):
    def __init__(self, *args, **kwargs):
        super(TableLineEditDelegate, self).__init__(*args, **kwargs)


class TableListViewDelegate(ListViewDelegate, HighlightDelegate):
    def __init__(self, *args, **kwargs):
        super(TableListViewDelegate, self).__init__(*args, **kwargs)


class TableTextEditDelegate(TextEditDelegate, HighlightDelegate):
    def __init__(self, *args, **kwargs):
        super(TableTextEditDelegate, self).__init__(*args, **kwargs)


class MessageBox:
    # def __int__(self):
    @staticmethod
    def askyesno(parent: QWidget, title: str, msg: str):
        yes = QMessageBox.question(
            parent,
            title,
            msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        return yes == QMessageBox.Yes

    @staticmethod
    def askyesnocancel(parent: QWidget, title: str, msg: str):
        return QMessageBox.question(
            parent,
            title,
            msg,
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel
        )

    @staticmethod
    def showError(parent, msg: str, title: str=None, ):
        error = QMessageBox(parent)
        error.setIcon(QMessageBox.Critical)
        error.setText(msg)
        error.setWindowTitle(title)
        error.exec_()

    @staticmethod
    def showWarning(parent, msg: str, title: str=None, ):
        error = QMessageBox(parent)
        error.setIcon(QMessageBox.Warning)
        error.setText(msg)
        error.setWindowTitle(title)
        error.exec_()


class TabLayout(QWidget):
    def __init__(self, parent=None):
        super(TabLayout, self).__init__(parent)
        self.tabs = QTabWidget()
        vbox = QVBoxLayout()
        vbox.addWidget(self.tabs)
        self.setLayout(vbox)

    def setTab(self, widget, title):
        self.tabs.addTab(widget, title)


class BackUpFile(QRunnable):
    def __init__(self, blocks, filename):
        super(BackUpFile, self).__init__()
        self.blocks = blocks
        self.filename = filename

    def run(self):
        try:
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
        except Exception as e:
            print('# [Warning] Backup file failed...')


# class InputDialog(QDialog):
#
#     def __init__(self, title: str, inputs: dict, parent=None, ):
#         super(InputDialog, self).__init__(parent)
#         self.setWindowTitle(title)
#         btn = QDialogButtonBox.Save | QDialogButtonBox.Cancel
#         btnbox = QDialogButtonBox(btn, self)
#         layout = QFormLayout()
#         self.widgets = OrderedDict()
#         for key, value in inputs.items():
#             widget = QLineEdit(self)
#             widget.setText(value)
#             layout.addRow(
#                 QLabel(key), widget
#             )
#             self.widgets[key] = widget
#
#         layout.addWidget(btnbox)
#         self.setLayout(layout)
#         btnbox.accepted.connect(self.accept)
#         btnbox.rejected.connect(self.reject)
#
#     def get(self):
#         save = False
#         if self.exec_():
#             save = True
#
#         return {
#             key: widget.text() for key, widget in self.widgets.items()
#         }, save


class LineEdit(QLineEdit):

    def __init__(self, validator=None, parent=None):
        super(LineEdit, self).__init__(parent)
        if validator == 'int':
            self.setValidator(QIntValidator())
        elif validator == 'hex':
            self.setValidator(HexValidator())


class InputDialog(QDialog):

    def __init__(self, title: str, inputs: dict, parent=None, values: dict=None):
        super(InputDialog, self).__init__(parent)
        self.setWindowTitle(title)
        btn = QDialogButtonBox.Save | QDialogButtonBox.Cancel
        btnbox = QDialogButtonBox(btn, self)
        layout = QFormLayout()
        self.widgets = OrderedDict()
        if values is None:
            values = {}
        for key, config in inputs.items():
            text = values.get(key, config.get('default', ''))
            validator = config.get('type', None)
            widget = config.get('widget', None)
            if widget == 'textEdit':
                widget = TextEdit(parent=self)
                widget.setText(text)
            else:
                widget = LineEdit(parent=self, validator=validator)
                widget.setText(text)
            layout.addRow(
                QLabel(key), widget
            )
            widget.setText(text)
            self.widgets[key] = widget

        layout.addWidget(btnbox)
        self.setLayout(layout)
        btnbox.accepted.connect(self.accept)
        btnbox.rejected.connect(self.reject)

    def get(self):
        save = False
        if self.exec_():
            save = True

        return {
            key: widget.text() for key, widget in self.widgets.items()
        }, save
