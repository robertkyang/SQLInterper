# SQLInterper

## Project Description:
While working with SQL scripts during a co-op term, I discovered that editing a whole directory's scripts for a project was a little tiresome - keeping track of different tables being updated and created was very time consuming and inconvenient if all you wanted to do was a quick edit of the script. So, behold the SQL Interpreter that I developed.

![Alt text](images/UI.png?raw=true "Main Program UI")

![Alt text](images/UI2.png?raw=true "DatabaseList")

The basic interpreter, developed in Python and PyQt scans through a directory of SQL scripts, or a directory filled with subdirectories of SQL scripts, to find all changes to database tables made during the script, when ran in alphabetical order. It looks for keywords, like select, update, from, into, join, and stores the input database for them. After scanning, through the program UI, you can display a list with all the tables and changes to those tables, which you can filter and search on. Alternatively, you can also look for only the input databases that are required before running all the scripts.


## How to use
Go to the dist folder to download the .exe file, and run it!
