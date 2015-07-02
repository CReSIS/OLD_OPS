# =========================================================================================
# SCRIPT FOR STARTING A LINE-BY-LINE DEBUGGING OF A DJANGO VIEW.
#
# Used to call a django view for debugging in an IDE (Eclipse).  
# The user should fill in the 'USER INPUT' fields below and debug this script with 
# breakpoint(s) placed in the view. The IDE should halt exectuion at breakpoint(s) and 
# allow the user to inspect variables and step through the code. See the IDE's specific 
# documention on debugging to learn more.
#
# Inputs required:
#	viewName: (string) the name of the view being debugged
#	app: (string) the name of the app for which the view will be debugged with
#	jsonStr: (string) the json string containing the properties used by the view.
#
# =========================================================================================

## USER INPUT 

#------------------------------------------------------------------------------------------
# viewName: the name of the view to be debugged
viewName = 'getSystemInfo'

#------------------------------------------------------------------------------------------
# app: the app for which the view will be debugged for ('rds','snow','kuband','accum')
app = ''

#------------------------------------------------------------------------------------------
#jsonStr: the json string containing the properties used by the view being debugged.
jsonStr = '{ "properties": { "userName": "paden", "isAuthenticated": true, "mat": true } }'

#f = open('/users/paden/jsonStr.txt')
#jsonStr = f.read()

#------------------------------------------------------------------------------------------

## AUTOMATED SECTION ##

#Import necessary modules
from django.test.client import RequestFactory
import ops.views
import django

#When Django starts, django.setup() is responsible for populating the application registry.
#This function must be called in plain python script above Django 1.6
django.setup()

#Create the RequestFactory object and form the request
rf = RequestFactory()
request = rf.post('',{'app': app, 'data': jsonStr})
#Send the request to views.
response = eval('ops.views.' + viewName + '(request)')

#SET A BREAKPOINT AFTER THIS LINE TO INSPECT THE RESPONSE:
# (use response.content to examine json return)
print 'SERVER RESPONSE STATUS: ' + str(response.status_code)