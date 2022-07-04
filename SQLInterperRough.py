import os
import openpyxl
from pathlib import Path

lookup = []
required_dbs = []
db_blacklist = []
keyword_db = []

#for case where a comment appears in middle of text
def parseComment(c,tokens,input):
    comment_word = []
    if c =="-":
        comment_word.append("-")
        comment_word.append("-")
        d = input.read(1)
        while d !=" " and d !="\n" and d !="\t" and d!="": #POTENTIAL FOR INFINITELOOP
            if not d:
                print("End of file COMMENT")
                break
            comment_word.append(d)
            d=input.read(1)
        tokens.append("".join(comment_word))
    else:
        close_char = c
        comment_word.append(c)

        c=input.read(1)
        while c!=close_char: #POTENTIAL FOR INFINITELOOP
            if not c:
                print("End of file")
                break
            comment_word.append(c)
            c=input.read(1)

        comment_word.append(c)
        tokens.append("".join(comment_word))

def wordParser(word, input, tokens, end):
    #global cont
    ignore_bracket=False

    c = input.read(1)

    #case where start of potential token is a multiline comment
    if c == "\"" or c == "'":
        parseComment(c,tokens,input)
        return
    #case where start of potential token is a line comment
    elif c=="-":
        word.append(c)
        next_char =input.read(1)
        if next_char =="-":
            while c!="\n" and c!="": #POTENTIAL FOR INFINITELOOP
                word.append(c)
                c=input.read(1)

            return
    elif c=="(":
        print("START BRACKET PARSE")
        lst_tokens=[]
        tokenizer(lst_tokens,input,")")
        word.append(lst_tokens)
    else:
        if c=="$":
            ignore_bracket=True
        #other case, where it isnt a comment
        while c != " " and c != '\n' and c !='\t': #POTENTIAL FOR INFINITELOOP
            word.append(c)
            c=input.read(1)

            #edge case where there is a comment right after a character
            if c=="-":
                d=input.read(1)
                if d=="-":
                    parseComment(d,tokens,input)
                else:
                    word.append(c)
                    word.append(d)
                    c=input.read(1)
            elif c == "\"" or c =="'":
                parseComment(c,tokens,input)
                c=input.read(1)
            elif c == "$":
                ignore_bracket=True
            elif (c=="(" or c==")") and ignore_bracket==False:
                input.seek(input.tell()-1)
                c=" " ## unget c, end loop so that start of next tokenizer loop will be "("
        

    
def tokenizer(tokens, input, end):
    #global cont
    cont = True
    word = []

    while cont:
        wordParser(word, input, tokens, end)

        if(word == []):
            continue

        c=input.read(1)
        #print("c: "+c+" || end: "+end, c==end)
        if c==end or word[len(word)-2]==end:
            cont=False
            print("ENDING CONT LOOP")
        else:
            input.seek(input.tell()-1)

        if isinstance(word[0],list):
            tokens.append(word[0])
            print(word[0])
            word=[]
        else:
            tokens.append("".join(word))
            print("word: "+("".join(word)))
            word=[]
        

        

def removeExtraChars(string):
    #removes brackets and semicolons from end of db entry
    if string[len(string)-1] == ")" or string[len(string)-1] == ";":
        return string[0:len(string)-1]
    else:
        return string

def dbLookup(token, lookup):

    #print(lookup)
    #fixes common syntax of just using dbo => workdb.dbo
    if token[0:3].lower() == "dbo":
        token="$(#&USEDB#&)."+token

    #fixes commonly not using dbo at all lol
    if len(token)>1 and token[1].casefold() == "_":
        token="$(#&USEDB#&).dbo."+token

    token=removeSqBrackets(token)
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
                    token=token.replace("$", "COULDNOTFIND")

            find_val = token.find("$")
        
        return removeExtraChars(token)

    else: 
        return removeExtraChars(token)

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
    return string

def addNewVar(search, replace, lookup, comment_out):
    for index, var_tuple in enumerate(lookup):
        if var_tuple[0].casefold() == search.casefold():
            lookup[index] = (search,replace,comment_out)
            return
        
    lookup.append((search,replace,comment_out))
    return

def searchForDBs(tokens,lookup,required_dbs,script_name,project, req_words, keyword_db):
    comment_out=False

    for index in range(len(tokens)):
        token=tokens[index]
        if isinstance(token,list):
            searchForDBs(token,lookup,required_dbs,script_name,project,req_words,keyword_db)
        elif token =="/*":
            comment_out=True
            #print("/*")
        elif token =="*/":
            comment_out=False
            #print("*/")
        elif token.casefold() == ":setvar":
            addNewVar(tokens[index+1],tokens[index+2], lookup, comment_out)
            index=index+2
            #print("setvar")
        elif token.casefold() == "use":
            pot_working_db = dbLookup(tokens[index+1],lookup)
            if pot_working_db != tokens[index+1]:
                if reqWordCheck(pot_working_db,req_words):
                    #print("?? USE " + pot_working_db)
                    addNewVar("#&USEDB#&","\""+pot_working_db+"\"",lookup,comment_out)
        elif token.casefold() == "from":
            if isinstance(tokens[index+1],list):
                keyword_db.append(("from", tokens[index+1], comment_out, script_name, project))
            else:    
                new_entry=dbLookup(tokens[index+1],lookup)
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
                new_entry=dbLookup(tokens[index+1],lookup)
                if appendDupCheck(new_entry, required_dbs) and reqWordCheck(new_entry,req_words):
                    required_dbs.append((new_entry, comment_out, script_name, project))
                if reqWordCheck(new_entry, req_words):
                    keyword_db.append(("join",new_entry, comment_out, script_name, project))
        elif token.casefold() == "into":
            if isinstance(tokens[index+1],list):
                keyword_db.append(("into", tokens[index+1], comment_out, script_name, project))
            else:            
                new_entry=dbLookup(tokens[index+1],lookup)
                if appendDupCheck(new_entry,db_blacklist):
                    #print("--- into: "+new_entry)
                    db_blacklist.append((new_entry, comment_out, script_name))
                keyword_db.append(("into",new_entry, comment_out, script_name, project))
                index=index+1
        
        elif token.casefold() == "with":
            if isinstance(tokens[index+1],list):
                keyword_db.append(("with", tokens[index+1], comment_out, script_name, project))
            else:
                if appendDupCheck(tokens[index+1],db_blacklist):
                    db_blacklist.append((removeSqBrackets(tokens[index+1]), comment_out, script_name))
                index=index+1
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
                            new_entry=dbLookup(tokens[index+4],lookup)
                            index=index+2
                        else:
                            new_entry=dbLookup(tokens[index+2],lookup)
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
                new_entry = dbLookup(tokens[index+1],lookup)
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

    for k in range(len(required_dbs)):    
        if searchtf((required_dbs[k])[0],db_blacklist):
           pop_queue.append(k)

        #HAVE TO FIND A STRING WHICH IS NEEDED FOR ANY DB ENTRY HERE, I guess by user input?      
        #elif len((required_dbs[k])[0]) < len("BASHAS") or (required_dbs[k])[0].upper().find("BASHAS") == -1:
        #    pop_queue.append(k)
        #UPD: MOVED UP APPENDDUPCHECK FOR EFFICIENCY

    #print(pop_queue)

    for to_pop in pop_queue:
        required_dbs.pop(to_pop-pop_offset)
        pop_offset=pop_offset+1

def scriptInterper(file_path, lookup, required_dbs, db_blacklist, project, req_words, keyword_db):
    cont=True
    tokens=[]
    fd=open(file_path)
    script_name = os.path.split(file_path)[1]
    #print("\nSCRIPT interper starting on... "+script_name)

    tokenizer(tokens, fd, '')
    searchForDBs(tokens,lookup,required_dbs,script_name, project, req_words, keyword_db)
    remove_bl_dbs(required_dbs,db_blacklist)
    
    # print("\n\n\n")
    # for token in tokens:
    #     print(token, end=' || ')
    # print("\n")
    # print(len(tokens))

    cont=True

def folderInterper(folder_path, lookup, required_dbs, db_blacklist, req_words, keyword_db):
    script_queue = []
    project=os.path.split(folder_path)[1]
    
    folder_contents = os.listdir(folder_path) 
    
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
    folder_contents = os.listdir(project_path)
    folder_queue = []

    for item in folder_contents:
        sub_path = os.path.join(project_path,item)
        if os.path.isdir(sub_path):
            folder_queue.append(((os.path.split(sub_path)[1]).split("_"),sub_path))

    folder_queue.sort(key=getNumber)

    #print(folder_queue)

    for queue_item in folder_queue:
        folder=queue_item[1]
        print(folder)
        folderInterper(folder,lookup,required_dbs,db_blacklist,req_words,keyword_db)


projectInterper(r"C:\Users\rober\Documents\Coding\Work_Projects\PRGX\2020", lookup, required_dbs, db_blacklist, [], keyword_db)

#folderInterper(r"C:\Users\rober\Documents\Coding\Work_Projects\PRGX\2020\1_AP" lookup, required_dbs, db_blacklist,["Bashas"])

#scriptInterper(r"C:\Users\rober\Documents\Coding\Work_Projects\PRGX\2020\3_CMAH\3_BAS_CMAH_setup.sql", lookup, required_dbs,db_blacklist,"5_DLS",["Bashas"], keyword_db)

# testpath=Path(r"C:\Users\rober\Documents\Coding\Work_Projects\PRGX\BASHAS 1_AP")
# lst=os.listdir(testpath)
# print(lst)
# print(type(os.path.splitext(os.path.join(testpath, lst[1]))[1]))

# tokenizer(tokens)
# searchForDBs(tokens,lookup,required_dbs)
# remove_bl_dbs(required_dbs,db_blacklist)
print("\n\n\n")
print(required_dbs)
#print("\n\n\n")
#print(db_blacklist)
#print("\n\n\n")
#print(lookup)

workbook = openpyxl.Workbook()

reqsheet= workbook.create_sheet("db required",0)
for index, entry in enumerate(required_dbs):
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
for index, entry in enumerate(db_blacklist):
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
for index, entry in enumerate(lookup):
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
for index, entry in enumerate(keyword_db):
    for i in range(5):
        cellref=keywords.cell(row=index+2,column=i+1)
        cellref.value=entry[i]


workbook.save(filename=r'C:\Users\rober\Documents\Coding\Work_Projects\PRGX\SQLInterper\sqlinterperROUGHResults.xlsx')

