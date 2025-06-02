##################################################################
# DEPRECATED                                                     #
# The same functionality been mainly added to the web interface. #
##################################################################

from helpers.admin import *
from helpers.admincli.Computer import *
from helpers.admincli.Container import *
from helpers.admincli.HardwareSpec import *
from helpers.admincli.Reservation import *
from helpers.admincli.Role import *
from helpers.admincli.User import *
from helpers.admincli.UserStorage import *
from helpers.admincli.UserWhitelist import *
from helpers.server import *
from helpers.auth import *
from getpass import getpass
from settings import settings
import sys

print("Welcome to AI Reservation Server Admin CLI")

def main():
  breakLoop = False
  default = True
  while breakLoop == False:
    if settings.adminToken == "":
      print("\nWhat would you like to do?")
      print("1) Login")
      print("2) Exit")
      selection = input()
      if selection == "1":
        print("\nLogin menu:")
        if "username" in settings.admincli: # Check whether the default option exists
          print('What is your username? (default username is: "'+ settings.admincli["username"] + '", leave empty to proceed with default.')
        else: 
          default = False
          print("What is your username?")
        username = input()
        #username = "aiserveradmin@samk.fi"
        if username == "" and default == True:
          username = settings.admincli["username"]
        print("What is your password?")
        password = getpass()
        #password = "test"
      
        # Making a get request
        #Login details: username = aiserveradmin@samk.fi and password = test
        login = CallAdminAPI("post", "user/login", data= {"username": username, "password": password}, headers=False)
        settings.adminToken = login["access_token"]
        response = CheckToken(settings.adminToken)
        if response["status"] != True:
          print("\nLogin token invalid. Exiting...")
          sys.exit()
        elif response["data"]["role"] != "admin":
          print("\nUser isn't an admin. Exiting...")
          sys.exit()
        else: print("\nLogged in successfully.")
      elif selection == "2": breakLoop = True
    else:
      if not CheckToken(settings.adminToken)["status"]:
        print("Login token no longer valid. Please login again.")
        settings.adminToken = ""
        continue
      print("\nWhat do you want to do?")
      print("You can type these commands to manage the tables:")
      print("users, userstorages, whitelisting, containers, hardwarespecs, reservations, roles, computers")
      print("1) users")
      print("2) userstorages")
      print("3) whitelisting")
      print("4) containers")
      print("5) hardwarespecs")
      print("6) reservations")
      print("7) roles")
      print("8) computers")
      print("You can also run: stats, exit")
      selection = input()
      if (selection == "users" or selection == "1"): CLIusers()
      if (selection == "userstorages" or selection == "2") : CLIuserstorages()
      elif (selection == "whitelisting" or selection == "3"): CLIuserwhitelisting()
      elif (selection == "containers" or selection == "4"): CLIcontainers()
      elif (selection == "hardwarespecs" or selection == "5"): CLIhardwarespecs()
      elif (selection == "reservations" or selection == "6"): CLIreservations()
      elif (selection == "roles" or selection == "7"): CLIroles()
      elif (selection == "computers" or selection == "8"): CLIcomputers()
      elif (selection == "stats"): stats()
      elif (selection == "exit"): breakLoop = True

def stats():
  # TODO: Print here the count of records in each table
  print("\nAmount of records in each table:")
  print("Users: 3 records")
  print("Containers: 1 records")

main()
