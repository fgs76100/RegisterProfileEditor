import sys
import traceback
import os
from PyQt5.QtCore import QThreadPool, Qt, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QUndoStack, QHBoxLayout, QSplitter, QWidget, QDesktopWidget, QMenuBar
from PyQt5.QtWidgets import QAction, QApplication, QTreeView, QFontDialog, QMenu
from PyQt5.QtGui import QFont

from .Views.BaseClass import Block

from .Views.widgets import FileDialog, MessageBox, InfoDialog, TabLayout, BackUpFile, InputDialog
from .config import register_columns, field_columns, menubar_configs, GUI_NAME, block_columns
from .IOHandle.ExcelParser import ExcelParser, JsonLoad
from .IOHandle.RegisterProfileWriter import JsonWriter, ExcelWriter
from .IOHandle.HTMLWriter import HTMLWriter
import qtawesome as qta

from .Views.AnalyzerView import AnalyzerWapper
from .Views.FieldView import FieldView
from .Views.BlockView import BlockView
from datetime import date



class App(QMainWindow):

    reload_address = pyqtSignal(dict)

    def __init__(self, filename=None):
        super(App, self).__init__()
        self.is_write = False
        self.backup_file = os.path.join(os.getcwd(), '.tmp.json')
        self.setWindowTitle(GUI_NAME)
        self.filedialog = FileDialog(self)
        # self.table = Table(self)
        self.address_space = {}
        self.info = InfoDialog(title=GUI_NAME, parent=self)
        self.threadpool = QThreadPool()
        self.data = {
            'project': '',
            'top_module': '',
            'blocks': []
        }
        self.undoStack = QUndoStack()
        self.treeUndoStack = QUndoStack()
        self.treeUndoStack.setUndoLimit(50)

        self.tree = BlockView(
            parent=self,
            cols=register_columns,
            blocks=self.data['blocks'],
            undoStack=self.treeUndoStack
        )
        self.table = FieldView(
            parent=self,
            cols=field_columns,
            items=[],
            undoStack=self.undoStack
        )
        self.tree.selectionChanged.connect(
            self.createTable
        )

        self.hbox = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        self.hbox.addWidget(splitter)
        self.setCentralWidget(QWidget(self))
        self.tabs = TabLayout(self)
        tab1 = QWidget(self)
        tab1.setLayout(self.hbox)
        self.analyzer = AnalyzerWapper(
            parent=self, cols=field_columns, address_space=self.address_space,
            reload=self.reload_address
        )
        self.tabs.setTab(tab1, title='RegisterProfile')
        self.tabs.setTab(self.analyzer, title='RegisterAnalyzer')

        self.setCentralWidget(self.tabs)
        self.menubar = self.menuBar()
        self.create_ui()
        if self.check_backup():
            self.loadFiles([self.backup_file])
        else:
            if filename:
                self.loadFiles([filename])

        self.table.tableSaved.connect(self.backUpFile)
        self.tree.addAnalyzerTrigger.connect(
            self.analyzer.add_analyzer
        )

    def create_ui(self):
        self.resize(1200, 600)
        self.center()
        self.createMenuBar(self.menubar)
        self.show()

    def center(self):
        rect = self.frameGeometry()
        rect.moveCenter(QDesktopWidget().availableGeometry().center())
        self.move(rect.topLeft())

    def createTable(self, block_index, row, block_name):
        success, msg = self.table.linting()
        self.tree.blockSignals(True)

        if success:
            # print(row)
            self.undoStack.clear()
            self.tree.blockSignals(False)

            if self.table.checkTableChanged():
                yes = MessageBox.askyesno(
                    self, GUI_NAME,
                    f'{self.table.caption.text()}\n'
                    f'The Table had been modified\n'
                    'Do you want to save changes?'
                )

                if yes:
                    self.table.saveTable()
                    self.backUpFile()

            register = self.data['blocks'][block_index].get_register(row)
            if register is None:
                MessageBox.showError(
                    self,
                    "Fields is missing. cannot create table\n",
                    GUI_NAME
                )
                return
            self.table.create_rows(
                register.fields,
                caption=block_name
            )
        else:
            self.table.setFocus()
            MessageBox.showWarning(
                self,
                msg,
                GUI_NAME,
            )

        self.tree.blockSignals(False)

    def createMenuBar(self, menubar: QMenuBar):
        menubar.addSeparator()
        for config in menubar_configs:
            for label, items in config.items():
                menu = menubar.addMenu(label)
                for item in items:
                    text = item.get('text')
                    sc = item.get('shortcut', '')
                    icon = item.get('icon', None)
                    sub = item.get('sub', None)
                    if sub:
                        submenu = QMenu(text, self)
                        for each_sub in sub:
                            text = each_sub.get('text')
                            icon = each_sub.get('icon', None)
                            action = QAction(text, self)
                            action.triggered.connect(
                                getattr(self, each_sub.get('action'))
                            )
                            if icon:
                                action.setIcon(qta.icon(icon))
                            submenu.addAction(action)
                        menu.addMenu(submenu)
                        continue
                    action = QAction(text, self)
                    action.setShortcut(sc)
                    if icon:
                        action.setIcon(qta.icon(icon))
                    action.triggered.connect(
                        getattr(self, item.get('action'))
                        # self.actions.get()
                    )
                    menu.addAction(action)

        self.more_actions()

    def undo(self):
        if isinstance(self.focusWidget(), QTreeView):
            self.treeUndoStack.undo()
        else:
            self.undoStack.undo()

    def redo(self):
        if isinstance(self.focusWidget(), QTreeView):
            self.treeUndoStack.redo()
        else:
            self.undoStack.redo()

    def selectFont(self):
        font, ok = QFontDialog.getFont(
            self.font(), self,
        )
        if ok:
            self.setFont(font)

    def openFiles(self, ):
        filenames = self.filedialog.askopenfiles()
        self.loadFiles(filenames)

    def openDir(self):
        folder = self.filedialog.askopendir()
        if not folder:
            return
        filenames = []
        for filename in os.listdir(folder):
            filename = os.path.join(folder, filename)
            if os.path.isfile(filename):
                filenames.append(filename)
        self.loadFiles(filenames)

    def loadFiles(self, filenames):
        if filenames:
            self.info.show()
            self.tree.saveChanges()
        try:
            for filename in filenames:
                if filename.endswith('.xlsx') or filename.endswith('.xls'):
                    parser = ExcelParser(
                        filename=filename,
                        blocks=self.data['blocks'],
                        # callback=self.create_tree
                    )
                elif filename.endswith('json'):
                    parser = JsonLoad(
                        filename=filename,
                        blocks=self.data['blocks'],
                    )
                else:
                    self.info.upload_text(
                        f'# [Error] This {filename} type of file not support'
                    )
                    continue
                parser.signal.progress.connect(
                    self.info.upload_text
                )
                parser.signal.done.connect(
                    self.thread_done
                )
                self.info.thread_cnt += 1
                self.threadpool.start(parser)

        except Exception:
            MessageBox.showError(
                self,
                "Oops! Parsing File failed...\n"+traceback.format_exc(),
                GUI_NAME
            )

    def thread_done(self):
        self.info.thread_cnt -= 1
        if self.info.thread_cnt == 0:
            self.info.progress_done()
            if not self.is_write:
                self.get_address_space()
                self.create_tree()
                self.reload_address.emit(self.address_space)
            else:
                self.remove_backup()
            self.is_write = False
            # self.info.upload_text(
            #     '# [INFO] Program Ends.'
            # )

    def newModule(self):
        new = InputDialog(
            title="New Module", parent=self, inputs=block_columns
        )
        info, yes = new.get()
        if yes:
            self.data['blocks'].append(
                Block(info)
            )
            self.create_tree()

    def more_actions(self):
        focus_next = QAction('nextChild', self)
        focus_next.setShortcut('Ctrl+W')
        focus_next.triggered.connect(self.nextChild)
        self.addAction(focus_next)

    def nextChild(self):
        if isinstance(self.focusWidget(), QTreeView):
            self.table.setFocus()
        else:
            self.tree.setFocus()

    def create_tree(self):
        self.data['blocks'].sort(
                key=lambda x: x.base_address
        )
        self.tree.create_rows(self.data['blocks'])

    def closeEvent(self, event):
        yes = MessageBox.askyesno(
            self,
            GUI_NAME,
            "Are you sure want to leave?"
        )
        if yes:
            self.info.destroy()
            self.remove_backup()
            event.accept()
        else:
            event.ignore()

    def saveAsOne(self):
        filename, ftype = self.filedialog.asksavefile(
            ftypes="Excel Files (*.xls);;JSON Files (*.json);;All Files (*);;",
            initial_ftype="Excel Files (*.xls)"
        )
        self.save(filename=filename, ftype=ftype)

    def saveExcelSeparately(self):
        folder = self.filedialog.askopendir()
        self.save(filename=folder, separately=True, ftype='Excel Files (*.xls)')

    def saveJsonSeparately(self):
        folder = self.filedialog.askopendir()
        self.save(filename=folder, separately=True, ftype='JSON Files (*.json)')

    def save(self, separately=False, filename=None, ftype='xls'):
        if filename:
            self.tree.clearSelection()
            self.is_write = True
            self.info.show()
            self.tree.saveChanges()
            if not self.data['blocks']:
                self.info.upload_text(
                    "# [Warning] There is no module exist."
                )
                return
            if 'json' in ftype:
                if not filename.endswith('.json') and not separately:
                    filename += '.json'
                writer = JsonWriter(
                    filename=filename,
                    blocks=self.data['blocks'],
                    separately=separately
                )
            elif 'xls' in ftype:
                if not filename.endswith('.xls') and not separately:
                    filename += '.xls'
                if not separately:
                    dialog = InputDialog(
                        title=GUI_NAME,
                        parent=self,
                        inputs={
                            "HEADPAGE": {},
                            "PREFIX": {},
                            "DATE": {'default': date.today().strftime("%Y/%m/%d")},
                            "AUTHOR": {},
                            "DESCRIPTION": {}
                        }
                    )
                    index_info, yes = dialog.get()
                    if not yes:
                        return
                else:
                    index_info = {}
                writer = ExcelWriter(
                    filename=filename,
                    blocks=self.data['blocks'],
                    separately=separately,
                    index_info=index_info
                )
            else:
                self.info.upload_text(
                    f"# [Error] This {filename} type of file not support"
                )
                return
            writer.signal.progress.connect(
                self.info.upload_text
            )
            writer.signal.done.connect(
                self.thread_done
            )
            self.info.thread_cnt += 1
            self.threadpool.start(writer)

    def get_address_space(self):

        self.address_space.clear()
        for block in self.data['blocks']:
            # self.info.upload_text(
            #     f"# [INFO] loading {block} ..."
            # )
            for address_space, fields in block.address_space():
                if address_space in self.address_space:
                    self.info.upload_text(
                        f"# [Warning] The address {address_space} is duplicated."
                    )
                self.address_space[address_space] = fields

    def remove_backup(self):
        if os.path.exists(self.backup_file):
            os.remove(self.backup_file)

    def check_backup(self):
        yes = False
        if os.path.exists(self.backup_file):
            yes = MessageBox.askyesno(
                self,
                GUI_NAME,
                "Maybe crash before.\n"
                "Do you want to reload previous file?"
            )
        return yes

    def backUpFile(self):
        thread = BackUpFile(blocks=self.data['blocks'], filename=self.backup_file)
        self.threadpool.start(thread)

    def saveAsHTML(self):
        filename, _ = self.filedialog.asksavefile(
            initial_ftype="HTML (*.html)"
        )
        if not filename:
            return
        if not filename.endswith('.html'):
            filename = filename.split('.')[0]+'.html'
        dialog = InputDialog(
            title=GUI_NAME,
            parent=self,
            inputs={
                "Project": {},
                "Module": {}
            }
        )
        project, save = dialog.get()
        if not save:
            return
        self.is_write = True
        self.info.show()
        self.tree.saveChanges()
        path = os.path.abspath(os.path.dirname(__file__))
        template = os.path.join(path, 'templates/template.html')

        writer = HTMLWriter(
            filename=filename,
            blocks=self.data['blocks'],
            template=template,
            project=project
        )
        writer.signal.progress.connect(
            self.info.upload_text
        )
        writer.signal.done.connect(
            self.thread_done
        )
        self.info.thread_cnt += 1
        self.threadpool.start(writer)

    def doNothing(self):
        pass


def trap_exc_during_debug(*args):
    # when app raises uncaught exception, print info
    log_file = os.path.join(os.getcwd(), 'log.txt')
    if not os.path.exists(log_file):
        with open(log_file, 'w') as f:
            f.write(log_file)
    else:
        with open(log_file, 'a') as f:
            f.writelines(args)


def main():
    # sys.excepthook = trap_exc_during_debug
    app = QApplication(sys.argv)

    font = QFont("Verdana", 12)
    app.setFont(font)
    # window = App(sys.argv[1])
    window = App()
    sys.exit(app.exec())


if __name__ == '__main__':

    main()
