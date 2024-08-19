# -*- coding: utf-8 -*-
"""
DISCLAIMER : 
This code is intended to be used only for troubleshooting purposes.
 - Please DO NOT use it for production applications as 
     - it does not align with the best practices for the Neo4j Driver's usage. 
     - Uses neo4j+ssc connection scheme - encryption with no certificate checks
Also note that 
Please take note that the driver syntax provided is verified as of the publication date. (28th of March 2024)
However, it is crucial to be aware that these examples are provided "as is" and are susceptible to variations due to potential product changes.

We strongly recommend exercising caution. While we strive to maintain accuracy, certain adjustments might be necessary to ensure compatibility with any modifications or updates introduced over time.

Stay vigilant, and kindly verify and validate the code against the latest documentation and resources available.

Check optimal max connection lifetime, to avoid session expired exceptions.
For a list of 'idle times' in seconds:
    1. Create a new Neo4j Driver instance
    2. Create a session from it
    3. Run an implicit transaction that doesn't touch the graph - "RETURN 1 AS n"
    4. Don't close the session. Wait for 'idle time'
    5. Check if it is possible to run another transaction using the same session
    6. Print and log progress throughout

Requirements
    - Python 3.7 or above    
    - Neo4j Python driver (works with both 4.x and 5.x):
        - pip install neo4j==4.4.11
            or
        - pip install neo4j==5.18.0
It is always recommended to install python packages for user space in a separate virtual environment.
This will ensure your current Python packages and in turn applications are not disturbed

IMPORTANT Consideration for Kubernetes:
If you run this code in Kubernetes pods, unexpected sleep() behavior can arise from the scheduler's pod management, potentially causing time jumps.

Addressing this involves:

- Using Guaranteed QoS with equal requests and limits to secure dedicated CPU resources.
- Checking pod events with kubectl describe pod <pod-name> for scheduling actions that might cause time discrepancies.
- Adjusting pod resource allocations to avoid unintended pauses or rescheduling.

These steps help ensure more predictable timing for operations within Kubernetes environments.
"""
import neo4j #pip install neo4j==4.4.11 or pip install neo4j==5.18.0
from time import sleep
from datetime import datetime as dt, date
from getpass import getpass
#from neo4j.debug import watch #Uncomment this and below for debug logs
#import logging
#watch("neo4j")
## from now on, DEBUG logging to stderr is enabled in the driver
## Set up the logger and configure it to write to a file
#logging.basicConfig(level=logging.DEBUG)

RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

def customLogger(txt,noPrint=None): 
    logFile = f'connecCheckLogs_{str(date.today())}.log'
    if len(txt) ==0:
        print()
        with open(logFile,'a') as f:
            f.write('') 
    else:
        if noPrint is None:
            print(dt.now(),txt)
        colourCodes = [RED, GREEN, BLUE, YELLOW, CYAN, RESET]
        for colourCode in colourCodes:
            txt = txt.replace(colourCode, '')
        logMsg = '\n'+str(dt.now())+'    ' + str(txt)
        with open(logFile,'a') as f:
            f.write(logMsg)            

def checkConnLife(NEO4J_URI,NEO4J_USER,NEO4J_PASS,connIdleTime):    
    idlePass = False
    try:
        with neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS),
                                        max_connection_pool_size=1) as driver:
            with driver.session(database="neo4j",default_access_mode=neo4j.READ_ACCESS) as session:
                with session.begin_transaction() as tx:
                    tx.run("RETURN 1 AS n")
                    if connIdleTime > 120:
                        sleepMinsLeft = int(connIdleTime/60)  
                        sleepSecondsLeft = connIdleTime%60
                        customLogger(f'{GREEN}Initial connection Successful. Sleeping for {sleepMinsLeft} minutes ...{RESET}')
                        while sleepMinsLeft>0:
                            sleep(60)#Sleeping for sleepMin x minutes
                            sleepMinsLeft -=1
                            if sleepMinsLeft>0:
                                print(dt.now(),f'Still running. Sleeping for {sleepMinsLeft} more minute(s) ...')
                        sleep(sleepSecondsLeft)
                    else: 
                        customLogger(f'{GREEN}Initial connection Successful. Sleeping for {connIdleTime} seconds ...{RESET}')
                        sleep(connIdleTime)
                    customLogger('Awake now. Checking the connection ...')
                    tx.run("RETURN 1 AS n")
                    idlePass = True
            
    except neo4j.exceptions.SessionExpired:
        customLogger(f'{RED}Session Expired for connection with idle time of {connIdleTime} seconds {RESET}');
        idlePass = False
    #except neo4j.exceptions.SessionError:
    #    customLogger("Session Error for connection with idle time of ");
    #    idlePass = False        
    except Exception as e:
        customLogger(f'{RED}Different Error encountered. Exiting\nError: {e}{RESET}') 
        exit
    finally:
        driver.close()
    return idlePass

def main():
    workingVal = 0
    idlesToCheck = [30,60,90,120,180,240,300,600,900,1200,1800,2400,2700,3010]
    customLogger('')
    customLogger(f'{GREEN}This script will check if connections idle after the following lifetime values are still usable(seconds):{RESET}\n\
                 {", ".join(str(x) for x in idlesToCheck)}')
    
    connExample = f"\nIf you see a {YELLOW}'Private URI'{RESET},for the instance in the Aura Console, please enter that as Public Traffic has likely been disabled for your instance."
    connExample = connExample +f"\n\n{YELLOW}Examples for expected conenction URI:{RESET}\nneo4j+s://a1b2c3d4.databases.neo4j.io\nneo4j+s://a1b2c3d4.production-orch-0001.neo4j.io"
    print(connExample)
    NEO4J_URI_in = input(f"\n{YELLOW}Please enter the Connection URI for the instance as seen in the Aura Console:{RESET}\n\n")
    #Logging the actual URI the user entered. Not printing it
    customLogger(f'URI entered by the user : {NEO4J_URI_in}',False)
    #Removing neo4j+s:// as we'lll be using neo4j+ssc://. This is to avoid running into potential certificate issues
    #The Conenction URI in the console includes the connection scheme neo4j+s:// and 
    #doesn't include the port number.
    #Removing both of them in case the user adds it. We'll be including them later.
    #This way the script will work irrespective of whether the user includes the conenction scheme and port number or not.
    NEO4J_URI = NEO4J_URI_in.strip().lower()
    NEO4J_URI = NEO4J_URI.replace("neo4j+s://",'').replace(":7687",'').replace("neo4j+ssc://",'')
    AURA_DBID = NEO4J_URI.split('.')[0]
    customLogger(f'DBID : {AURA_DBID}',False)
    NEO4J_USER = input(f"{YELLOW}Please enter your username for {AURA_DBID}:{RESET}\n").strip()
    NEO4J_PASS = getpass(f"{YELLOW}Please enter the password for user {NEO4J_USER} for {AURA_DBID} (Hidden):{RESET}\n").strip()
    #Adding connection scheme and port number
    NEO4J_URI = f'neo4j+ssc://{NEO4J_URI}:7687'
    customLogger('')
    customLogger(f'Attempting to connect to {NEO4J_URI}')
    customLogger('')
    for connIdleTime in idlesToCheck:
        customLogger(f'Checking connection lifetime of {connIdleTime} seconds')
        connectSuccess = checkConnLife(NEO4J_URI,NEO4J_USER,NEO4J_PASS,connIdleTime)
        if connectSuccess:
            customLogger(f'{GREEN}The connection was valid after {connIdleTime} seconds of idle time...{RESET}')
            workingVal = max(workingVal,connIdleTime)
        else:
            customLogger(f'{RED}The connection FAILED after {connIdleTime} seconds of idle time...{RESET}')
            break            
        customLogger('')
    customLogger(f'{GREEN}Recommended Connection lifetime : {workingVal-10} seconds or lesser{RESET}')
    customLogger(f'{GREEN}The longest running valid connection was {workingVal} seconds old.{RESET}')
    customLogger(f'{GREEN}The recommended value is 10 seconds lesser than this {RESET}')     

if __name__ == '__main__':
    main()
