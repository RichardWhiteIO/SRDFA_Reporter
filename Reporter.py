#! /usr/bin/env python

import requests, json, time, logging, os, sys, csv
from datetime import datetime, date, timedelta
from datetime import time as goofytime


# Disable warnings from untrusted server certificates
try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except Exception:
    logging.info("Ignore messages related to insecure SSL certificates")

#Date
TIMESTAMP = date.today() - timedelta(days=1)

# Get the URL from environmentals. Example: "10.241.209.162:8443"
try:
    LOCATION = os.environ['SRUNILOCATION']
except KeyError:
    logging.critical('Please set the environment variable SRUNILOCATION to IP:Port of Unisphere using "export SRUNILOCATION=IP:PORT" command')
    sys.exit(1)

# Get credentials for Unisphere login from environmentals
try:
    USER = os.environ['SRUSER']
except KeyError:
    logging.critical('Please set the environment variable SRUSER to a valid username for Unisphere using "export SRUSER=user" command')
    sys.exit(1)

try:
    PASS = os.environ['SRPASS']
except KeyError:
    logging.critical('Please set the environment variable SRPASS to the password for the username for Unisphere using "export SRPASS=password" command')
    sys.exit(1)

# Get current directory the script is running in

if os.path.isfile('SRDFA_Reporter.csv') == False:

    with open('SRDFA_Reporter.csv','w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                                quotechar=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['24h Period','Array','Storage Group','Total MB Sent by SRDFA'])

def payload(SYM, SG):
    PAYLOAD = {
        "startDate" : unix_ym,
        "endDate" : unix_midnight,
        "symmetrixId" : SYM,
        "storageGroupId" : SG,
        "metrics" : ["SRDFA_MBSent"]
    }
    return (PAYLOAD)


#Get today's midnight
midnight = datetime.combine(date.today(), goofytime.min)
#Convert to unix epoch time
unix_midnight = time.mktime(midnight.timetuple())
#Convert to milliseconds
unix_midnight *= 1000
#Remove trailing .0 float from the time
unix_midnight = ('%f' % unix_midnight).rstrip('0').rstrip('.')

#Get yesterday's midnight
yesterday_midnight = midnight - timedelta(days=1)
#Convert to unix epoch time
unix_ym = time.mktime(yesterday_midnight.timetuple())
#Convert to milliseconds
unix_ym *= 1000
#Remove trailing .0 float from the time
unix_ym = ('%f' % unix_ym).rstrip('0').rstrip('.')

# Get all VMAXs for a given Unisphere Instance
vURL = "https://" + LOCATION + "/univmax/restapi/provisioning/symmetrix"
try:
    vr = requests.get(vURL, auth=(USER,PASS), verify = False)
    DATA=vr.json()
    SYML = (DATA["symmetrixId"])
except ValueError:
    logging.critical('Login failure. SRUSER and SRPASS credentials failed. Please confirm the environmental variables are properly set.')
    sys.exit(1)
except Exception as e:
    logging.critical('IP:Port information is incorrect. Please confirm SRUNILOCATION environment variable is properly set. Detailed Error: {0}'.format(e))
    sys.exit(1)

# For each VMAX in Unisphere, get the storage Groups
for SYM in SYML:
    sURL = "https://" + LOCATION + "/univmax/restapi/provisioning/symmetrix" + SYM + "/storagegroup"
    sr = requests.get(sURL, auth=(USER,PASS), verify = False)
    sresponse = sr.json()
    SGL = sresponse["storageGroupId"]
    for SG in SGL:
        #For each SG in a given VMAX, get SRDFA_MBSent metric, sum it up across yesterday and write it out to csv file.
        DATA = payload(SYM,SG)
        HEADERS = {'content-type': 'application/json','accept':'application/json'}
        ssURL = "https://" + LOCATION + "/univmax/restapi/performance/StorageGroup/metrics"
        ssr = requests.post(ssURL, data=json.dumps(DATA, sort_keys=True, indent=4), auth=(USER, PASS), headers=HEADERS, verify = False)
        ssresponse = ssr.json()
        #print(ssresponse)

        # If response back includes a message instead of expected output, then it should be because the VMAX isn't local or isn't licensed for SMC
        # So skip the VMAX and move onto the next.
        test = ssresponse.get('message')
        if test != None:
            logging.warning(ssresponse.get('message') + " This Array is being skipped.")
            break

        RESULT = ssresponse["resultList"]["result"]

        total = 0

        #Grab Total MB Sent for a given SG
        for item in RESULT:
           total +=item['SRDFA_MBSent']

        with open('SRDFA_Reporter.csv', 'a') as csvfile:
            writer = csv.writer(csvfile, delimiter=',',
                                    quotechar=',', quoting=csv.QUOTE_MINIMAL)
            writer.writerow([str(TIMESTAMP), SYM, SG, str(total)])

