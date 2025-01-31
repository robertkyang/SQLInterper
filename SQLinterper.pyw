import sys, os, openpyxl
from xmlrpc.client import boolean
from PyQt6.QtCore import QSize, Qt
from datetime import datetime
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
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QAbstractScrollArea,
    QCheckBox,
)

class inputStream:

    def __init__(self, stream) -> None:
        self.stream = stream
        self.index = 0 #points to next unread character
    
    def getEnd(self):
        return len(self.stream)
    
    def peekChar(self):
        if self.index < len(self.stream):
            return self.stream[self.index]
        else:
            return ""
    
    def readChar(self):
        if self.index < len(self.stream):
            self.index=self.index+1
            return self.stream[self.index-1]
        else:
            return ""
    
    def unreadChar(self):
        if self.index != 0:
            self.index = self.index - 1
        return

    def getPosition(self):
        return self.index
    
    def setPosition(self, position):
        self.index = position

def skipSpaces(input):
    c=input.readChar()
    while c == ' ' or c == '\n' or c == '\t' or c =='\v' or c=="\r" or c=="\r\n":
        c=input.readChar()

    input.unreadChar()
    return input

def readString(input, str_start):
    sqlString=[]
    sqlString.append(str_start)

    c = input.readChar()
    while c!=str_start:
        sqlString.append(c)
        c=input.readChar()
    sqlString.append(str_start)

    return "".join(sqlString)

def readComment(input):
    comment = ["-"]

    c=input.readChar()
    while c!= '\n' and c!="":
        comment.append(c)
        c=input.readChar()
    
    return "".join(comment)

def readWord(input):
    word = []
    bracket_stop = True

    c=input.readChar()
    while c!= '\n' and c!=' ' and c!='\t' and c!= "" and c!="\r" and c!="\r\n":
        if c == "$":
            bracket_stop = False
        elif (c=="-" and input.peekChar() == "-") or (c=="*" and input.peekChar() == "/") or c=="\'" or c=="\"" or c==",":
            input.unreadChar()
            break
        elif (c=="(" or c==")") and bracket_stop:
            input.unreadChar()
            bracket_continue = False
            break
        elif (c==")"): #basically one $ only skips one closed bracket; to deal with edge case that a variable ends a bracket
            bracket_stop = True
        
        word.append(c)
        c=input.readChar()

    return "".join(word)

def readBracket(input,endLoc):
    bracket_tokens=[]
    token=""

    input = skipSpaces(input)
    c=input.readChar()
    while c!=")":
        if input.getPosition() == endLoc:
            break
        elif c== '\"' or c== "\'":
            token = readString(input, c)
        elif c == "-" and input.peekChar()=="-":
            token = readComment(input)
        elif c=="/" and input.peekChar()=="*":
            token="/*"
            input.readChar()
        elif c=="*" and input.peekChar() == "/":
            token="*/"
            input.readChar()
        elif c==",":
            token=","
        elif c=="(":
            token=readBracket(input,endLoc)
        else:
            input.unreadChar()
            token=readWord(input)

        if token != "":
            bracket_tokens.append(token)
        
        input = skipSpaces(input)
        c=input.readChar()
    
    return bracket_tokens

def tokenizer(input, tokens):
    token = ""
    
    end_loc=input.getEnd()
    
    input = skipSpaces(input)
    c=input.readChar()
    while c!="":
        if input.getPosition() == end_loc:
            break
        elif c== '\"' or c== "\'":
            token = readString(input, c)
        elif c == "-" and input.peekChar()=="-":
            token = readComment(input)
        elif c=="/" and input.peekChar()=="*":
            token="/*"
            input.readChar()
        elif c==",":
            token=","
        elif c=="*" and input.peekChar() == "/":
            token="*/"
            input.readChar()
        elif c=="(":
            token=readBracket(input,end_loc)
        else:
            input.unreadChar()
            token=readWord(input)
            

        if token != "":
            tokens.append(token)
        
        input = skipSpaces(input)
        c=input.readChar()

    return tokens

def dbLookup(token, lookup, db_blacklist):

    #print(lookup)
    token=removeSqBrackets(token)

    #fixes common syntax of just using dbo => workdb.dbo
    if token[0:3].lower() == "dbo":
        token="$(#&USEDB#&)."+token

    #fixes commonly not using dbo at all lol
    elif token[0].casefold() != "$" and not searchtf(token, db_blacklist):
        token="$(#&USEDB#&).dbo."+token
#    else: 
#        print("NOCHANGE TOKEN: "+token)

    find_val = token.find("$")

    if find_val != -1:
        #replace all variables
        while find_val != -1:
            
            find_val_end = token.find(")")
            search_name=token[find_val+2:find_val_end]
            #print("SEARCHING: "+search_name)
            
            changed = False
            for pair in lookup:
                #print("check4")
                if pair[0].casefold() == search_name.casefold():
                    token=token.replace("$("+search_name+")",(pair[1])[1:len(pair[1])-1])
                    changed = True
            
            if changed == False:
                    token=token.replace("$", "#")

            find_val = token.find("$")
        
        return token

    else: 
        return token

def appendDupCheck(name,array):
    for items in array:
        if items[0].casefold()==name.casefold():
            return False
    
    return True

def reqWordCheck(name,req_words):
    #for filtering words
    for word in req_words:
        if (name.casefold()).find(word.casefold()) == -1:
            return False
    return True

def removeSqBrackets(string):
    string=string.replace("[","")
    string=string.replace("]","")
    if string[len(string)-1] == ";":
        string=string[0:len(string)-1]
    
    return string

def addNewVar(search, replace, lookup, comment_out):
    for index, var_tuple in enumerate(lookup):
        if var_tuple[0].casefold() == search.casefold():
            lookup[index] = (search,replace,comment_out)
            return
        
    lookup.append((search,replace,comment_out))
    return

def searchForDBs(tokens,lookup,required_dbs,db_blacklist,script_name,project, req_words, keyword_db, tokensLen):
    comment_out=False

    for index in range(len(tokens)):
        token=tokens[index]
        if isinstance(token,list):
            searchForDBs(token,lookup,required_dbs,db_blacklist,script_name,project,req_words,keyword_db, tokensLen)
        elif token =="/*":
            comment_out=True
            #print("/*")
        elif token =="*/":
            comment_out=False
            #print("*/")
        elif token.casefold() == ":setvar":
            if comment_out == False:
                addNewVar(tokens[index+1],removeSqBrackets(tokens[index+2]), lookup, comment_out)
                index=index+2
                #print("setvar")
        elif token.casefold() == "use":
            pot_working_db = dbLookup(tokens[index+1],lookup,db_blacklist)
            if pot_working_db != tokens[index+1] and comment_out == False: # if dblookup changed something I think?
                if reqWordCheck(pot_working_db,req_words):
                    #print("?? USE " + pot_working_db)
                    addNewVar("#&USEDB#&","\""+pot_working_db+"\"",lookup,comment_out)
        elif token.casefold() == "from":
            if isinstance(tokens[index+1],list):
                keyword_db.append(("from", tokens[index+1], comment_out, script_name, project))
            else:    
                new_entry=dbLookup(tokens[index+1],lookup,db_blacklist)
                if appendDupCheck(new_entry, required_dbs) and reqWordCheck(new_entry,req_words):
                    #print("!!! from: " + new_entry)
                    required_dbs.append((new_entry, comment_out, script_name, project))
                if reqWordCheck(new_entry,req_words):
                    keyword_db.append(("from", new_entry, comment_out, script_name, project))
                index=index+1
        elif token.casefold() == "join":
            if isinstance(tokens[index+1],list):
                keyword_db.append(("join", tokens[index+1], comment_out, script_name, project))
            else:
                new_entry=dbLookup(tokens[index+1],lookup,db_blacklist)
                if appendDupCheck(new_entry, required_dbs) and reqWordCheck(new_entry,req_words):
                    required_dbs.append((new_entry, comment_out, script_name, project))
                if reqWordCheck(new_entry, req_words):
                    keyword_db.append(("join",new_entry, comment_out, script_name, project))
        elif token.casefold() == "into":
            if isinstance(tokens[index+1],list):
                keyword_db.append(("into", tokens[index+1], comment_out, script_name, project))
            else:            
                new_entry=dbLookup(tokens[index+1],lookup,db_blacklist)
                if appendDupCheck(new_entry,db_blacklist):
                    #print("--- into: "+new_entry)
                    db_blacklist.append((new_entry, comment_out, script_name))
                keyword_db.append(("into",new_entry, comment_out, script_name, project))
                index=index+1
        
        elif token.casefold() == "with":
            print(token, end=" || ")
            print(tokens[index+1], end = " || ")
            print(tokens[index+2])
            if not(isinstance(tokens[index+2],list)) and tokens[index+2].casefold() == "as":
                while index+3 < tokensLen and not(isinstance(tokens[index+2],list)) and tokens[index+2].casefold() == "as":
                    print(tokens[index+1], end= " ")
                    print(tokens[index+2], end= " ")
                    print(tokens[index+3])
                    if appendDupCheck(tokens[index+1],db_blacklist):
                        db_blacklist.append((removeSqBrackets(tokens[index+1]), comment_out, script_name))
                    keyword_db.append(("with",tokens[index+1], comment_out, script_name, project))
                    if isinstance(tokens[index+3], list):
                        searchForDBs(tokens[index+3],lookup,required_dbs,db_blacklist,script_name,project,req_words,keyword_db, tokensLen)
                    index=index+4
                    #print("with")
        elif token.casefold() == "drop":
            if isinstance(tokens[index+1],list):
                continue
            else:
                if tokens[index+1].casefold() == "view" or tokens[index+1].casefold() == "table":
                    if isinstance(tokens[index+2],list) or isinstance(tokens[index+3],list):
                        continue
                    else:
                        if tokens[index+2].casefold() == "if" and tokens[index+3].casefold() == "exists":
                            new_entry=dbLookup(tokens[index+4],lookup,db_blacklist)
                            index=index+2
                        else:
                            new_entry=dbLookup(tokens[index+2],lookup,db_blacklist)
                        if appendDupCheck(new_entry,db_blacklist):
                            #print("+++ drop: "+new_entry)
                            db_blacklist.append((new_entry, comment_out, script_name))
                            index=index+1
                        keyword_db.append(("drop", new_entry, comment_out, script_name, project))
                    index=index+1
        elif token.casefold() == "update":
            if isinstance(tokens[index+1],list):
                keyword_db.append(("update", tokens[index+1], comment_out, script_name, project))
            else:            
                new_entry = dbLookup(tokens[index+1],lookup,db_blacklist)
                if appendDupCheck(new_entry,db_blacklist):
                    db_blacklist.append((new_entry, comment_out, script_name))
                index=index+1
                keyword_db.append(("update", new_entry, comment_out, script_name, project))

def searchtf(string, array):
    for items in array:
        if items[0].casefold()==string.casefold():
            return True
    return False

def remove_bl_dbs(required_dbs,db_blacklist):
    pop_offset=0
    pop_queue = []
    sys=["sys.columns","sys.indexes","sysindexes","sysobjects","INFORMATION_SCHEMA.TABLES"]

    for k in range(len(required_dbs)):    
        if searchtf((required_dbs[k])[0],db_blacklist):
           pop_queue.append(k)
        else:
            #popping selects with sys object
            for entry in sys:
                if (required_dbs[k])[0].find(entry) != -1:
                    pop_queue.append(k)

        #HAVE TO FIND A STRING WHICH IS NEEDED FOR ANY DB ENTRY HERE, I guess by user input?      
        #elif len((required_dbs[k])[0]) < len("BASHAS") or (required_dbs[k])[0].upper().find("BASHAS") == -1:
        #    pop_queue.append(k)
        #UPD: MOVED UP APPENDDUPCHECK FOR EFFICIENCY

    #print(pop_queue)

    #actually pop it
    for to_pop in pop_queue:
        required_dbs.pop(to_pop-pop_offset)
        pop_offset=pop_offset+1

def scriptInterper(file_path, lookup, required_dbs, db_blacklist, project, req_words, keyword_db):
    cont=True
    tokens=[]
    fd=open(file_path)
    inpStream = inputStream(fd.read())
    script_name = os.path.split(file_path)[1]
    #print("\nSCRIPT interper starting on... "+script_name)

    tokenizer(inpStream, tokens)
    searchForDBs(tokens,lookup,required_dbs,db_blacklist,script_name, project, req_words, keyword_db, len(tokens))
    remove_bl_dbs(required_dbs,db_blacklist)
    
    #print("\n\n\n")
    #for token in tokens:
    #    print(token, end=' || ')
    #print("\n")
    #print(len(tokens))

    cont=True

def folderInterper(folder_path, lookup, required_dbs, db_blacklist, req_words, keyword_db):
    script_queue = []
    project=os.path.split(folder_path)[1]
    
    try:
        folder_contents = os.listdir(folder_path)
    except FileNotFoundError:
            errorMsg = QMessageBox()
            errorMsg.setWindowTitle("SQL Script Analyzer Error")
            errorMsg.setText("Error: Could not find a folder's path")
            errorMsg.setIcon(QMessageBox.Icon.Critical)
            errorMsg.exec()
    else:
        for file in folder_contents:
    #        print(os.path.join(folder_path, file))
    #        print(os.path.splitext(os.path.join(folder_path, file))[1].casefold())
            if os.path.splitext(os.path.join(folder_path, file))[1].casefold() == ".sql".casefold():
                script_queue.append(os.path.join(folder_path,file))
        
        for script in script_queue:
            print("\n"+script)
            scriptInterper(script, lookup, required_dbs, db_blacklist,project,req_words, keyword_db)
        
        #os.path.splitext(filepath)[1]

def getNumber(unsorted_item):
    return int((unsorted_item[0])[0])

def projectInterper(project_path,lookup,required_dbs,db_blacklist,req_words,keyword_db):
    try:
        folder_contents = os.listdir(project_path)
    except FileNotFoundError:
            errorMsg = QMessageBox()
            errorMsg.setWindowTitle("SQL Script Analyzer Error")
            errorMsg.setText("Error: Could not find a folder's path")
            errorMsg.setIcon(QMessageBox.Icon.Critical)
            errorMsg.exec()
    else:        
        folder_queue = []

        for item in folder_contents:
            sub_path = os.path.join(project_path,item)
            if os.path.isdir(sub_path):
                folder_queue.append(((os.path.split(sub_path)[1]).split("_"),sub_path))

        try:
            folder_queue.sort(key=getNumber)
        except ValueError:
            folder_queue.sort()

        #print(folder_queue)

        for queue_item in folder_queue:
            folder=queue_item[1]
            print(folder)
            folderInterper(folder,lookup,required_dbs,db_blacklist,req_words,keyword_db)

def listToString(lst):
    output="("
    for index,entry in enumerate(lst):
        if isinstance(entry, list):
            output= output+listToString(entry)
        else:
            output=output+entry+" "
    if len(output)>1:
        output=output[:len(output)-1] +")"
    else: output=output+")"
    return output


app = QApplication(sys.argv)

class MainUI(QMainWindow):

    def __init__(self):
        super().__init__()

        self.lookup = []
        self.required_dbs = []
        self.db_blacklist = []
        self.keyword_db = []
        self.req_words = []
        self.layLst = []
        self.dialogLst = []

        self.setWindowTitle('SQL Script Analyzer')
        self.setMaximumHeight(220)
        self.setMaximumWidth(500)
        #self.setFixedSize(435, 235)
        self.generalLayout = QVBoxLayout()
        
        sublayout1 = QHBoxLayout()
        pathlabel = QLabel()
        pathlabel.setText("Project Path: ")
        sublayout1.addWidget(pathlabel)

        self.pathLE = QLineEdit()
        self.pathLE.setReadOnly(True)    
        self.pathLE.setText("C:/")
        sublayout1.addWidget(self.pathLE)
        sublayout1.setSpacing(20)
        self.generalLayout.addLayout(sublayout1)
        self.layLst.append(sublayout1)


        sublayout2 = QHBoxLayout()
        rqWords = QLabel()
        rqWords.setText("Enter required words: ")
        sublayout2.addWidget(rqWords)
        self.requiredWordsLE = QLineEdit()
        sublayout2.addWidget(self.requiredWordsLE)
        self.generalLayout.addLayout(sublayout2)
        self.layLst.append(sublayout2)

        sublayout3 = QHBoxLayout()
        runButton = QPushButton()
        runButton.setText("Run Analysis")
        runButton.clicked.connect(self.__start_anaylsis)
        sublayout3.addWidget(runButton)
        changeButton = QPushButton()
        changeButton.setText("Change Path")
        changeButton.clicked.connect(self.__select_path)
        sublayout3.addWidget(changeButton)

        radioLayout = QVBoxLayout()
        #radioParent = QWidget()
        self.projectSelect = QRadioButton()
        self.projectSelect.setText("Analyze main folder only")
        radioLayout.addWidget(self.projectSelect)
        self.fullProjectSelect = QRadioButton()
        self.fullProjectSelect.setText("Analyze subfolders as projects")
        self.fullProjectSelect.toggle()
        radioLayout.addWidget(self.fullProjectSelect)
        sublayout3.addLayout(radioLayout)
        self.layLst.append(sublayout3)

        self.generalLayout.addLayout(sublayout3)

        self.__generate_options("#$%NONE#$%","")

        self._centralWidget = QWidget() #dummy widget
        self.setCentralWidget(self._centralWidget)
        self._centralWidget.setLayout(self.generalLayout)
    
    def __generate_options(self,name,ranDt):
        panel = QWidget()
        panel.setStyleSheet("background-color: rgb(200, 200, 200);")

        if len(name) > 40:
            name = name[:20] + "..."+ name[-20:]

        if name == "#$%NONE#$%":
            sublayout4 = QVBoxLayout(panel)
            self.layLst.append(sublayout4)
            self.statusTxt = QLabel()
            self.statusTxt.setText("Currently no data stored. Run analysis on a project to see options")
            self.statusTxt.setStyleSheet("font-weight: 600;")
            sublayout4.addWidget(self.statusTxt)
            sublayout4.addSpacing(20)
            self.generalLayout.addWidget(panel)
        elif len(self.layLst) > 4:
            sublayoutOld = self.layLst[3]
            oldStatusTxt = sublayoutOld.itemAt(0)
            oldStatusTxt.widget().close()
            sublayoutOld.removeItem(oldStatusTxt)

            statusTxt = QLabel()
            statusTxt.setText("Current data for: "+name+" ran at "+ranDt)
            sublayoutOld.insertWidget(0,statusTxt)
        else:
            sublayoutOld = self.layLst[3]
            oldStatusTxt = sublayoutOld.itemAt(0)
            oldStatusTxt.widget().close()
            sublayoutOld.removeItem(oldStatusTxt)

            statusTxt = QLabel()
            statusTxt.setText("Current data for: "+name+" ran at "+ranDt)
            sublayoutOld.insertWidget(0, statusTxt)

            sublayout5 = QHBoxLayout()
            excelGenButton = QPushButton()
            excelGenButton.setText("Generate Excel Spreadsheet")
            excelGenButton.clicked.connect(self.__generate_excel)
            sublayout5.addWidget(excelGenButton)
            searchButton = QPushButton()
            searchButton.setText("Search for table history")
            searchButton.clicked.connect(self.__all_tables_history)
            sublayout5.addWidget(searchButton)
            listRqDBButton = QPushButton()
            listRqDBButton.setText("List required dbs")
            listRqDBButton.clicked.connect(self.__list_dbs)
            sublayout5.addWidget(listRqDBButton)
            sublayoutOld.addLayout(sublayout5)
            self.layLst.append(sublayout5)

            self.dbUI = requiredListUI(self.required_dbs)
            self.dialogLst.append(self.dbUI)

            self.historyUI = tableHistoryUI(self.keyword_db)
            self.dialogLst.append(self.historyUI)
    
    def __start_anaylsis(self):

        self.lookup = []
        self.required_dbs = []
        self.db_blacklist = []
        self.keyword_db = []

        path = self.pathLE.displayText()
        arrName = path.split("\\")
        name = arrName[len(arrName)-1]

        self.req_words=(self.requiredWordsLE.displayText()).split(",")

        #maybe add some feedback to say process actually started to the user? lol
        #popup = QMessageBox()
        
        if self.fullProjectSelect.isChecked() == True:
            projectInterper(path,self.lookup,self.required_dbs,self.db_blacklist, self.req_words,self.keyword_db)
        else:
            folderInterper(path,self.lookup,self.required_dbs,self.db_blacklist,self.req_words,self.keyword_db)
        
        #if doesn't quite work; need dbUI to be initialized... maybe move initialization to the #$%NONE#$% case
        #if self.lookup == [] and self.required_dbs == [] and self.db_blacklist == [] and self.keyword_db == []:
        #    self.__generate_options("#$%NONE#$%", datetime.now().strftime("%m-%d %H:%M:%S"))
        #else:
        self.__generate_options(name, datetime.now().strftime("%m-%d %H:%M:%S"))

        self.dbUI.required_dbs = self.required_dbs
        self.historyUI.keyword_db = self.keyword_db

        finMsg = QMessageBox()
        finMsg.setWindowTitle("SQL Script Analyzer")
        finMsg.setText("Finished Analyzing Scripts")
        finMsg.setIcon(QMessageBox.Icon.Information)
        finMsg.exec()

    def __select_path(self):
        file = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.pathLE.setText(file)

    def __list_dbs(self):
        self.dbUI.lst_gen()
        self.dbUI.show()

    def __all_tables_history(self):
        self.historyUI.table_gen()
        self.historyUI.show()

    def __generate_excel(self):
        file_name, _ = QFileDialog.getSaveFileName(self,"Save Results","","Excel Workbook (*.xlsx)")
        
        workbook = openpyxl.Workbook()

        reqsheet= workbook.create_sheet("db required",0)
        for index, entry in enumerate(self.required_dbs):
            cellref=reqsheet.cell(row=index+2, column=3)
            cellref.value=entry[0]

            cellref2=reqsheet.cell(row=index+2, column=4)
            if entry[1] == True:
                cellref2.value="commented out,"
            if entry[0].casefold().find("_w.".casefold()) != -1:
                cellref2.value="potential workingDB,"+ str(cellref2.value or "")
            if isinstance(cellref2.value, str):
                cellref2.value = cellref2.value[:-1]

            cellref3=reqsheet.cell(row=index+2, column=2)
            cellref3.value=entry[2]
            cellref4=reqsheet.cell(row=index+2, column=1)
            cellref4.value=entry[3]
        (reqsheet.cell(row=1,column=1)).value="Project"
        (reqsheet.cell(row=1,column=2)).value="Script Name"
        (reqsheet.cell(row=1,column=3)).value="Database Name"
        (reqsheet.cell(row=1,column=4)).value="Extra info"
        #reqsheet.column_dimensions['A'].width = 20
        reqsheet.column_dimensions['B'].width = 30
        reqsheet.column_dimensions['C'].width = 50

        blsheet=workbook.create_sheet("black list",1)
        for index, entry in enumerate(self.db_blacklist):
            cellref=blsheet.cell(row=index+2,column=2)
            cellref.value=entry[0]
            if entry[1] == True:
                cellref=blsheet.cell(row=index+2, column=3)
                cellref.value="commented out"
            #script name
            cellref4=blsheet.cell(row=index+2, column=1)
            cellref4.value=entry[2]
        (blsheet.cell(row=1,column=1)).value="Script Name"
        (blsheet.cell(row=1,column=2)).value="Database Name"
        (blsheet.cell(row=1,column=3)).value="Extra info"

        setvars=workbook.create_sheet("setvars",2)
        for index, entry in enumerate(self.lookup):
            cellref=setvars.cell(row=index+1,column=1)
            cellref2=setvars.cell(row=index+1,column=2)
            cellref.value=entry[0]
            cellref2.value=entry[1]
            if entry[2] == True:
                cellref=setvars.cell(row=index+1, column=3)
                cellref.value="commented out"

        keywords=workbook.create_sheet("full list",3)
        (keywords.cell(row=1,column=1)).value="Keyword"
        (keywords.cell(row=1,column=2)).value="Database/Input"
        (keywords.cell(row=1,column=3)).value="Comment out T/F"
        (keywords.cell(row=1,column=4)).value="Script"
        (keywords.cell(row=1,column=5)).value="Project"
        keywords.column_dimensions['B'].width = 50
        keywords.column_dimensions['D'].width = 30
        #keywords.column_dimensions['E'].width = 20
        for index, entry in enumerate(self.keyword_db):
            for i in range(5):
                cellref=keywords.cell(row=index+2,column=i+1)
                if isinstance(entry[i],list):
                    
                    cellref.value = listToString(entry[i]) #' '.join(entry[i])
                else:
                    cellref.value=entry[i]

        try:
            workbook.save(filename=file_name)
            finMsg = QMessageBox()
            finMsg.setWindowTitle("SQL Script Analyzer")
            finMsg.setText("File saved successfully.")
            finMsg.setIcon(QMessageBox.Icon.Information)
            finMsg.exec()
        except FileNotFoundError:
            errorMsg = QMessageBox()
            errorMsg.setWindowTitle("SQL Script Analyzer Error")
            errorMsg.setText("Error while saving file: File is being edited or could not be found.")
            errorMsg.setIcon(QMessageBox.Icon.Critical)
            errorMsg.exec()
        except BaseException:
            errorMsg = QMessageBox()
            errorMsg.setWindowTitle("SQL Script Analyzer Error")
            errorMsg.setText("Unexpected Error while saving file.")
            errorMsg.setIcon(QMessageBox.Icon.Critical)
            errorMsg.exec()
        
class requiredListUI(QMainWindow):
    
    def __init__(self, required_dbs, parent=None):
        super(requiredListUI, self).__init__(parent)
        self.required_dbs = required_dbs
        self.setWindowTitle("SQL Analyzer: Required Tables")

        self.generalLayout = QVBoxLayout()
        sublayout = QHBoxLayout()
        self.showCommentsBox = QCheckBox()
        self.showCommentsBox.setText("Show commented out tables")
        sublayout.addWidget(self.showCommentsBox)
        self.showWorkDBBox = QCheckBox()
        self.showWorkDBBox.setText("Show potential working database")
        self.showWorkDBBox.setChecked(True)
        sublayout.addWidget(self.showWorkDBBox)
        regenButton = QPushButton()
        regenButton.setText("Regenerate List")
        regenButton.clicked.connect(self.lst_gen)
        sublayout.addWidget(regenButton)

        self.generalLayout.addLayout(sublayout)
        
        self.showcaseTable = QTableWidget()
        self.showcaseTable.setRowCount(1)
        self.showcaseTable.setColumnCount(4)
        self.showcaseTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.showcaseTable.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.generalLayout.addWidget(self.showcaseTable)

        self.lst_gen()

        self._centralWidget = QWidget() #dummy widget
        self.setCentralWidget(self._centralWidget)
        self._centralWidget.setLayout(self.generalLayout)

    def lst_gen(self):
        self.showcaseTable.clearContents()
        self.showcaseTable.setRowCount(len(self.required_dbs)+1)
        self.showcaseTable.setHorizontalHeaderItem(0,QTableWidgetItem("Project"))
        self.showcaseTable.setHorizontalHeaderItem(1,QTableWidgetItem("Script Name"))
        self.showcaseTable.setHorizontalHeaderItem(2,QTableWidgetItem("Database Name"))
        self.showcaseTable.setHorizontalHeaderItem(3,QTableWidgetItem("Extra Info"))
        
        nextRow = 0
        for index, entry in enumerate(self.required_dbs):
            extraInfostr=""
            if entry[1] == True:
                if self.showCommentsBox.isChecked() == False:
                    continue
                extraInfostr="commented out,"
            if entry[0].casefold().find("_w.".casefold()) != -1:
                if self.showWorkDBBox.isChecked() == False:
                    continue
                extraInfostr="potential workingDB,"+ extraInfostr
            if extraInfostr != "":
                extraInfostr = extraInfostr[:-1]
            extraInfo = QTableWidgetItem(extraInfostr)
            self.showcaseTable.setItem(nextRow,3,extraInfo)

            projectName = QTableWidgetItem(entry[3])
            self.showcaseTable.setItem(nextRow,0,projectName)
            scriptName = QTableWidgetItem(entry[2])
            self.showcaseTable.setItem(nextRow,1,scriptName)
            tableName = QTableWidgetItem(entry[0])
            self.showcaseTable.setItem(nextRow,2,tableName)
            nextRow = nextRow + 1
        self.showcaseTable.resizeColumnsToContents()
        self.showcaseTable.setRowCount(nextRow)

        
class tableHistoryUI(QMainWindow):
    
    def __init__(self, keywords_db, parent=None):
        super(tableHistoryUI, self).__init__(parent)
        self.keyword_db = keywords_db
        self.generalLayout = QVBoxLayout()

        sublayout = QHBoxLayout()
        searchLabel = QLabel()
        searchLabel.setText("Search: ")
        sublayout.addWidget(searchLabel)
        self.searchbox = QLineEdit()
        sublayout.addWidget(self.searchbox)
        searchButton = QPushButton()
        searchButton.setText("🔍")
        searchButton.clicked.connect(self.table_gen)
        sublayout.addWidget(searchButton)
        self.generalLayout.addLayout(sublayout)

        filtertxt = QLabel()
        filtertxt.setText("Filter out: ")
        self.generalLayout.addWidget(filtertxt)

        optionSublayout = QHBoxLayout()
        self.commentOutBox = QCheckBox()
        self.commentOutBox.setText("Commented Out")
        optionSublayout.addWidget(self.commentOutBox)
        self.dropBox = QCheckBox()
        self.dropBox.setText("drop")
        optionSublayout.addWidget(self.dropBox)
        self.fromBox = QCheckBox()
        self.fromBox.setText("from")
        optionSublayout.addWidget(self.fromBox)
        self.intoBox = QCheckBox()
        self.intoBox.setText("into")
        optionSublayout.addWidget(self.intoBox)
        self.generalLayout.addLayout(optionSublayout)

        optionSubLayout2 = QHBoxLayout()
        self.joinBox = QCheckBox()
        self.joinBox.setText("join")
        optionSubLayout2.addWidget(self.joinBox)
        self.updateBox = QCheckBox()
        self.updateBox.setText("update")
        optionSubLayout2.addWidget(self.updateBox)
        self.withBox = QCheckBox()
        self.withBox.setText("with")
        optionSubLayout2.addWidget(self.withBox)
        filterAll = QPushButton()
        filterAll.setText("Filter all")
        filterAll.clicked.connect(self.filter_all)
        optionSubLayout2.addWidget(filterAll)
        self.generalLayout.addLayout(optionSubLayout2)

        self.showcaseTable = QTableWidget()
        self.showcaseTable.setRowCount(1)
        self.showcaseTable.setColumnCount(5)
        self.showcaseTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.showcaseTable.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.generalLayout.addWidget(self.showcaseTable)

        self.table_gen()

        self._centralWidget = QWidget() #dummy widget
        self.setCentralWidget(self._centralWidget)
        self._centralWidget.setLayout(self.generalLayout)
    
    def table_gen(self):
        self.showcaseTable.clearContents()
        self.showcaseTable.setRowCount(len(self.keyword_db)+1)
        self.showcaseTable.setHorizontalHeaderItem(0,QTableWidgetItem("Keyword"))
        self.showcaseTable.setHorizontalHeaderItem(1,QTableWidgetItem("Table Name"))
        self.showcaseTable.setHorizontalHeaderItem(2,QTableWidgetItem("Commented Out T/F"))
        self.showcaseTable.setHorizontalHeaderItem(3,QTableWidgetItem("Script"))
        self.showcaseTable.setHorizontalHeaderItem(4,QTableWidgetItem("Project"))

        nextRow = 0
        maxNameLen = 0
        for entry in self.keyword_db:
            for i in range(5):
                if i == 0:
                    if entry[i] == "drop" and self.dropBox.isChecked():
                        nextRow = nextRow-1
                        break
                    elif entry[i] == "from" and self.fromBox.isChecked():
                        nextRow = nextRow-1
                        break
                    elif entry[i] == "into" and self.intoBox.isChecked():
                        nextRow = nextRow-1
                        break
                    elif entry[i] == "join" and self.joinBox.isChecked():
                        nextRow = nextRow-1
                        break
                    elif entry[i] == "update" and self.updateBox.isChecked():
                        nextRow = nextRow-1
                        break
                    elif entry[i] == "with" and self.withBox.isChecked():
                        nextRow = nextRow-1
                        break
                
                if i == 1:
                    if not isinstance(entry[i],list):                    
                        if entry[i].casefold().find(self.searchbox.displayText().casefold()) == -1:
                            clearCell = QTableWidgetItem("")
                            self.showcaseTable.setItem(nextRow,0,clearCell)
                            nextRow = nextRow - 1
                            break

                        if len(entry[i])>maxNameLen:
                            maxNameLen = len(entry[i])
                    else:
                        if self.searchbox.displayText() != "":
                            clearCell = QTableWidgetItem("")
                            self.showcaseTable.setItem(nextRow,0,clearCell)
                            nextRow = nextRow - 1
                            break
                
                if i == 2:
                    if entry[i] and self.commentOutBox.isChecked():
                        for i in range(2):
                            clearCell = QTableWidgetItem("")
                            self.showcaseTable.setItem(nextRow,i,clearCell)
                        nextRow = nextRow - 1
                        break

                #cellref=keywords.cell(row=index+2,column=i+1)
                outputStr=""
                if isinstance(entry[i],list):
                    outputStr = listToString(entry[i]) #' '.join(entry[i])
                elif isinstance(entry[i],bool):
                    if entry[i]:
                        outputStr = "TRUE"
                    else:
                        outputStr = "FALSE"
                else:
                    outputStr=entry[i]

                outputCell = QTableWidgetItem(outputStr)
                self.showcaseTable.setItem(nextRow,i,outputCell)

            nextRow = nextRow+1
        
        self.showcaseTable.setRowCount(nextRow+1)
        self.showcaseTable.resizeColumnsToContents()
        #if maxNameLen !=0:
        #    self.showcaseTable.setColumnWidth(1,maxNameLen)

    def filter_all(self):
        self.commentOutBox.setChecked(True)
        self.dropBox.setChecked(True)
        self.fromBox.setChecked(True)
        self.intoBox.setChecked(True)
        self.joinBox.setChecked(True)
        self.updateBox.setChecked(True)
        self.withBox.setChecked(True)


window = MainUI()
#window.setGeometry(100, 100, 280, 80)
#window.move(60, 15)

window.show()


sys.exit(app.exec())