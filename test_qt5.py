from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLineEdit,
        QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget)
 
class SortedDict(dict):
    class Iterator(object):
        def __init__(self, sorted_dict):
            self._dict = sorted_dict
            self._keys = sorted(self._dict.keys())
            self._nr_items = len(self._keys)
            self._idx = 0
 
        def __iter__(self):
            return self
 
        def next(self):
            if self._idx >= self._nr_items:
                raise StopIteration
 
            key = self._keys[self._idx]
            value = self._dict[key]
            self._idx += 1
 
            return key, value
 
        __next__ = next
 
    def __iter__(self):
        return SortedDict.Iterator(self)
 
    iterkeys = __iter__
 
class AddressBook(QWidget):
    def __init__(self, parent=None):
        super(AddressBook, self).__init__(parent)
 
        self.contacts = SortedDict()
        self.oldName = ''
        self.oldAddress = ''
 
        nameLabel = QLabel("Name:")
        self.nameLine = QLineEdit()
        self.nameLine.setReadOnly(True)
 
        addressLabel = QLabel("Address:")
        self.addressText = QTextEdit()
        self.addressText.setReadOnly(True)
 
        self.addButton = QPushButton("&Add")
        self.addButton.show()
        self.submitButton = QPushButton("&Submit")
        self.submitButton.hide()
        self.cancelButton = QPushButton("&Cancel")
        self.cancelButton.hide()
        self.nextButton = QPushButton("&Next")
        self.nextButton.setEnabled(False)
        self.previousButton = QPushButton("&Previous")
        self.previousButton.setEnabled(False)
 
        self.addButton.clicked.connect(self.addContact)
        self.submitButton.clicked.connect(self.submitContact)
        self.cancelButton.clicked.connect(self.cancel)
        self.nextButton.clicked.connect(self.next)
        self.previousButton.clicked.connect(self.previous)
 
        buttonLayout1 = QVBoxLayout()
        buttonLayout1.addWidget(self.addButton, Qt.AlignTop)
        buttonLayout1.addWidget(self.submitButton)
        buttonLayout1.addWidget(self.cancelButton)
        buttonLayout1.addStretch()
 
        buttonLayout2 = QHBoxLayout()
        buttonLayout2.addWidget(self.previousButton)
        buttonLayout2.addWidget(self.nextButton)
 
        mainLayout = QGridLayout()
        mainLayout.addWidget(nameLabel, 0, 0)
        mainLayout.addWidget(self.nameLine, 0, 1)
        mainLayout.addWidget(addressLabel, 1, 0, Qt.AlignTop)
        mainLayout.addWidget(self.addressText, 1, 1)
        mainLayout.addLayout(buttonLayout1, 1, 2)
        mainLayout.addLayout(buttonLayout2, 3, 1)
 
        self.setLayout(mainLayout)
        self.setWindowTitle("Simple Address Book")
 
    def addContact(self):
        self.oldName = self.nameLine.text()
        self.oldAddress = self.addressText.toPlainText()
 
        self.nameLine.clear()
        self.addressText.clear()
 
        self.nameLine.setReadOnly(False)
        self.nameLine.setFocus(Qt.OtherFocusReason)
        self.addressText.setReadOnly(False)
 
        self.addButton.setEnabled(False)
        self.nextButton.setEnabled(False)
        self.previousButton.setEnabled(False)
        self.submitButton.show()
        self.cancelButton.show()
 
    def submitContact(self):
        name = self.nameLine.text()
        address = self.addressText.toPlainText()
 
        if name == "" or address == "":
            QMessageBox.information(self, "Empty Field",
                    "Please enter a name and address.")
            return
 
        if name not in self.contacts:
            self.contacts[name] = address
            QMessageBox.information(self, "Add Successful",
                    "\"%s\" has been added to your address book." % name)
        else:
            QMessageBox.information(self, "Add Unsuccessful",
                    "Sorry, \"%s\" is already in your address book." % name)
            return
 
        if not self.contacts:
            self.nameLine.clear()
            self.addressText.clear()
 
        self.nameLine.setReadOnly(True)
        self.addressText.setReadOnly(True)
        self.addButton.setEnabled(True)
 
        number = len(self.contacts)
        self.nextButton.setEnabled(number > 1)
        self.previousButton.setEnabled(number > 1)
 
        self.submitButton.hide()
        self.cancelButton.hide()
 
    def cancel(self):
        self.nameLine.setText(self.oldName)
        self.addressText.setText(self.oldAddress)
 
        if not self.contacts:
            self.nameLine.clear()
            self.addressText.clear()
 
        self.nameLine.setReadOnly(True)
        self.addressText.setReadOnly(True)
        self.addButton.setEnabled(True)
 
        number = len(self.contacts)
        self.nextButton.setEnabled(number > 1)
        self.previousButton.setEnabled(number > 1)
 
        self.submitButton.hide()
        self.cancelButton.hide()
 
    def next(self):
        name = self.nameLine.text()
        it = iter(self.contacts)
 
        try:
            while True:
                this_name, _ = it.next()
 
                if this_name == name:
                    next_name, next_address = it.next()
                    break
        except StopIteration:
            next_name, next_address = iter(self.contacts).next()
 
        self.nameLine.setText(next_name)
        self.addressText.setText(next_address)
 
    def previous(self):
        name = self.nameLine.text()
 
        prev_name = prev_address = None
        for this_name, this_address in self.contacts:
            if this_name == name:
                break
 
            prev_name = this_name
            prev_address = this_address
        else:
            self.nameLine.clear()
            self.addressText.clear()
            return
 
        if prev_name is None:
            for prev_name, prev_address in self.contacts:
                pass
 
        self.nameLine.setText(prev_name)
        self.addressText.setText(prev_address)
 
if __name__ == '__main__':
    import sys
 
    from PyQt5.QtWidgets import QApplication
 
    app = QApplication(sys.argv)
 
    addressBook = AddressBook()
    addressBook.show()
 
    sys.exit(app.exec_())
