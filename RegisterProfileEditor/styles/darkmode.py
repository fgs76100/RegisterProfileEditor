import os

bg = '#373939'
black = '#333333'
light_bg = '#3E3F3F'

item_selected = '#1f4287'

text = '#d9d9d9'

border_color = '#4d4d4d'
dark_border_color = '#262626'
selected_color = '#808080'

here = os.path.abspath(os.path.dirname(__file__))

style = f"""

QWidget , QWidget * {{
    background-color: {light_bg};
    color: {text};
    
}}

QTableView, QTableView * {{
    background-color: {bg};
    color: {text};
    border-color: transparent;
}}

QHeaderView::section {{
    background-color: transparent;
    color: {text};
    border-color: transparent;
}}

QHeaderView::section::checked {{
    background: {border_color};
}}

QTabWidget::pane {{
    border-top: 2px solid {border_color};
}}

/* tab view */

QTabBar::tab {{
    background-color: {bg};
    border: 1px solid {border_color};
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 4px;
}}

QTabBar::tab:selected, QTabBar::tab:hover {{
       background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                stop: 0 #333333, stop: 1.0 {selected_color});
}}

QTabBar::tab:selected {{
    border-color: {bg};
    border-bottom: 2px solid #C2C7CB; /* same as pane color */
}}

QTabBar::tab:!selected {{
    margin-top: 2px; /* make non-selected tabs look smaller */
}}

/* Menu view */

QMenu {{
    background-color: {bg}; /* sets background of the menu */
    border: 1px solid {border_color};
    padding: 4px; /* some spacing around the menu */
}}

QMenu::item {{
    /* sets background of menu item. set this to something non-transparent
        if you want menu color and menu item color to be different */
    background-color: transparent;
}}

QMenu::item:selected {{ /* when user selects item using mouse or keyboard */
    background-color: {item_selected};
}}

/* MenuBar view */

QMenuBar {{
    border-bottom: 1px solid {border_color};
    background: {light_bg};
}}

QMenuBar::item {{
    spacing: 20px; /* spacing between menu bar items */
    padding: 8px;
    background: transparent;
    /* border-radius: 4px; */ 
}}

QMenuBar::item:selected {{ /* when selected using mouse or keyboard */
    background: {item_selected};
}}

/* LineEdit view */

QLineEdit, QTextEdit, QPlainTextEdit {{
    border: 2px solid {border_color};
    border-radius: 8px;
    background: {light_bg}; 
    /* selection-background-color: darkgray; */
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 3px solid {item_selected};
}}



/* Tree view */

QTreeView {{

    background: {light_bg};
    border-color: transparent;
}}

QTreeView::item {{
    border-color: transparent;
}}

QTreeView::item:hover {{
    background: {item_selected};
}}

QTreeView::item:selected {{
    background: {item_selected};
}}

QTreeView::branch:has-children:!has-siblings:closed, QTreeView::branch:closed:has-children:has-siblings {{
        border-image: none;
        image: url(RegisterProfileEditor/styles/right-arrow.png);
        padding: 4px;
}}

QTreeView::branch:open:has-children:!has-siblings, QTreeView::branch:open:has-children:has-siblings  {{
        border-image: none;
        image: url(RegisterProfileEditor/styles/down-arrow.png);
        padding: 4px;
}}


/* Scroll bar */

QScrollBar {{
    border: none;
    background: {bg};
}}

QScrollBar::sub-page {{
    border: none;
    background: {bg};
}}

QScrollBar::sub-line {{
    border: none;
    background: {bg};
}}

QScrollBar::add-page {{
    border: none;
    background: {bg};
}}

QScrollBar::add-line {{
    border: none;
    background: {bg};
}}

QScrollBar::handle {{
    background: {text};
}}

/* table */

QTableView {{
    alternate-background-color: #404242;
    background: {bg};
}}

QTableView QTableCornerButton::section {{
    background: transparent;
}}

QTableView::item:selected {{
    selection-background-color: {item_selected};
}}

QPushButton {{ 
    background-color: {black}; 
    padding: 8px;
}}

QPushButton:flat {{
    border: none; /* no border for a flat push button */
}}

QPushButton:pressed {{
    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 {selected_color}, stop: 1 {light_bg});
}}

QPushButton:disabled {{
    background-color: {light_bg}; 
    border: none;
    color: {light_bg}; 
}}


"""