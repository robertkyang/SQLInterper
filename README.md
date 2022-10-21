# SQLInterper

## Project Description:
While working with SQL scripts during a co-op term, I discovered that editing a whole directory's scripts for a project was a little tiresome - keeping track of different tables being updated and created was very time consuming and inconvenient if all you wanted to do was a quick edit of the script. So, behold the SQL Interpreter that I developed to help make editing SQL sprojects easier.

![Picture of Program UI](images/UI.png?raw=true "Main Program UI")

![List of databases UI](images/UI2.png?raw=true "DatabaseList")

The basic interpreter, developed in Python and PyQt scans through a directory of SQL scripts, or a directory filled with subdirectories of SQL scripts, to find all changes to database tables made during the script, when ran in alphabetical order. It looks for keywords, like select, update, from, into, join, and stores the input database for them. After scanning, through the program UI, you can display a list with all the tables and changes to those tables, which you can filter and search on. Alternatively, you can also look for only the input databases that are required before running all the scripts.

## How to install
Go to the dist folder to download the .exe file, and run it!

## How to use
Select a file directory with the 'Change Path' button.
Analyzing the main folder will only look for SQL scripts in the selected directory, while analyzing subprojects as folder will look at folders within the selected directory, and analyze SQL scripts there.
Required words will filter the input databases to only those containing the words that you input in the box. Separate words with a comma only.
