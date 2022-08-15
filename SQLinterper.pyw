import sys
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QMainWindow,
    QGridLayout,
    QMessageBox,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QRadioButton
)

app = QApplication(sys.argv)

class MainUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('SQL Table Analyzer')
        #self.setFixedSize(435, 235)
        self.generalLayout =  QVBoxLayout()
        
        sublayout1 = QHBoxLayout()
        pathlabel = QLabel()
        pathlabel.setText("Project Path: ")
        sublayout1.addWidget(pathlabel)

        self.pathLE = QLineEdit()
        self.pathLE.isReadOnly=False    
        self.pathLE.setText("HELLO")
        sublayout1.addWidget(self.pathLE)
        sublayout1.setSpacing(20)
        self.generalLayout.addLayout(sublayout1)


        sublayout2 = QHBoxLayout()
        rqWords = QLabel()
        rqWords.setText("Enter required words: ")
        sublayout2.addWidget(rqWords)
        self.requiredWordsLE = QLineEdit()
        sublayout2.addWidget(self.requiredWordsLE)
        self.generalLayout.addLayout(sublayout2)

        sublayout3 = QHBoxLayout()
        runButton = QPushButton()
        runButton.setText("Run Analysis")
        sublayout3.addWidget(runButton)
        changeButton = QPushButton()
        changeButton.setText("Change Path")
        sublayout3.addWidget(changeButton)

        radioLayout = QVBoxLayout()
        #radioParent = QWidget()
        self.projectSelect = QRadioButton()
        self.projectSelect.setText("Analyze main folder only")
        radioLayout.addWidget(self.projectSelect)
        self.fullProjectSelect = QRadioButton()
        self.fullProjectSelect.setText("Analyze subfolders as projects")
        radioLayout.addWidget(self.fullProjectSelect)
        sublayout3.addLayout(radioLayout)

        self.generalLayout.addLayout(sublayout3)

        self._generate_options("#$%NONE#$%","")

        self.printtext()

        self._centralWidget = QWidget() #dummy widget
        self.setCentralWidget(self._centralWidget)
        self._centralWidget.setLayout(self.generalLayout)
    
    def _generate_options(self,name,ranDt):
        panel = QWidget()
        panel.setStyleSheet("background-color: rgb(200, 200, 200);")
        sublayout4 = QVBoxLayout(panel)
        self.statusTxt = QLabel()
        if name == "#$%NONE#$%":
            self.statusTxt.setText("Currently no data stored. Run analysis on a project to see options")
            self.statusTxt.setStyleSheet("font-weight: 600;")
            sublayout4.addWidget(self.statusTxt)
            sublayout4.addSpacing(50)
        else:
            self.statusTxt.setText("Current data for: "+name+ranDt)
            sublayout4.addWidget(self.statusTxt)

        self.generalLayout.addWidget(panel)
    
    def printtext(self):
        print(self.pathLE.displayText())

        
        

window = MainUI()
#window.setGeometry(100, 100, 280, 80)
#window.move(60, 15)

window.show()


sys.exit(app.exec())