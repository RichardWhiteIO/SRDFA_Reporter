#! /usr/bin/env python

import requests
import json
import time
import os
import logging
import sys
import csv
from datetime import datetime, date, timedelta
from datetime import time as dt_time

# Get logging level from env var SRLOGGINGLEVEL.
# If it doesn't exist, default to "INFO"
# Ensure that the value is capitalized
user_level = os.getenv('SRLOGGINGLEVEL', "INFO").upper()
valid_response = ["DEBUG", "INFO", "WARNING", "CRITICAL"]
wrong = False

if user_level not in valid_response:
    # If the user put incorrect response, report the error and set the value back to default.
    user_level = "INFO"
    wrong = True

logging.basicConfig(
        level=logging.getLevelName(user_level),
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        filename='SRDFA_Reporter_Error_Log.csv')
console_write = logging.StreamHandler()
console_write.setLevel(logging.getLevelName(user_level))
logger = logging.getLogger()
logger.addHandler(console_write)

if wrong:
    logger.warning("SRLOGGINGLEVEL contains an invalid value. Valid values are: DEBUG, INFO, WARNING, and CRITICAL")

def generate_payload(symmetrix_id, storage_group_id):
    return {
        "startDate": unix_ym,
        "endDate": unix_midnight,
        "symmetrixId": symmetrix_id,
        "storageGroupId": storage_group_id,
        "metrics": ["SRDFA_MBSent"]
    }


# Disable warnings from untrusted server certificates
try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning

    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except Exception as e:
    logging.info("Ignore messages related to insecure SSL certificates. Error: {}".format(e))

# Date
timestamp = date.today() - timedelta(days=1)

# Get the URL from environmentals. Example: "10.241.209.162:8443"
try:
    LOCATION = os.environ['SRUNILOCATION']
except KeyError:
    logger.critical('Need an IP:Port. Please set the environment variable SRUNILOCATION to IP:Port of Unisphere \
    using either "export SRUNILOCATION=IP:PORT" (linux command) or "set SRUINLOCATION=IP:PORT" (Windows command)')
    sys.exit(1)

# Get credentials for Unisphere login from environmentals
try:
    USER = os.environ['SRUSER']
except KeyError:
    logger.critical('Need a username. Please set the environment variable SRUSER to the username of Unisphere using \
    either "export SRUSER=username" (linux command) or "set SRUSER=username" (Windows command)')
    sys.exit(1)

try:
    PASS = os.environ['SRPASS']
except KeyError:
    logger.critical('Need a password. Please set the environment variable SRPASS to the password of Unisphere using \
    either "export SRUSER=password" (linux command) or "set SRUSER=password" (Windows command)')
    sys.exit(1)

# Get current directory the script is running in

if not os.path.isfile('SRDFA_Reporter.csv'):

    with open('SRDFA_Reporter.csv', 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            ['24h Period', 'Array', 'Storage Group', 'Total MB Sent by SRDFA'])


# Get today's midnight
midnight = datetime.combine(date.today(), dt_time.min)
# Convert to unix epoch time
unix_midnight = time.mktime(midnight.timetuple())
# Convert to milliseconds
unix_midnight *= 1000
# Remove trailing .0 float from the time
unix_midnight = str(unix_midnight).replace(".0", "")

# Get yesterday's midnight
yesterday_midnight = midnight - timedelta(days=1)
# Convert to unix epoch time
unix_ym = time.mktime(yesterday_midnight.timetuple())
# Convert to milliseconds
unix_ym *= 1000
# Remove trailing .0 float from the time
unix_ym = str(unix_ym).replace(".0", "")

# Get all VMAXs for a given Unisphere Instance
vURL = "https://" + LOCATION + "/univmax/restapi/provisioning/symmetrix"

try:
    symmetrix_list_response = requests.get(vURL, auth=(
        USER, PASS), verify=False).json()

    if 'message' in symmetrix_list_response:
        # I've seen an issue where Unisphere returns a message of "No Symmetrix's found.
        message = symmetrix_list_response.get('message')
        logger.critical(message)
        sys.exit(1)

    else:
        # Assuming no messages, store the list of VMAX's into symmetrix_list
        symmetrix_list = symmetrix_list_response["symmetrixId"]
        print("VMAXs found: " + symmetrix_list)

except ValueError:
    logger.critical(
        "Login failure. $SRUSER and $SRPASS credentials failed. Please confirm the environmental variables are \
        properly set with correct username/password")
    sys.exit(1)
except Exception as e:

    logger.critical(
        "Unisphere couldn't be reached. Please confirm SRUNILOCATION environment variable is properly set and \
             Unisphere is up and running.. Details: {}".format(e))
    sys.exit(1)

# For each VMAX in Unisphere, get the storage Groups
for symmetrix_id in symmetrix_list:
    sURL = "https://" + LOCATION + "/univmax/restapi/provisioning/symmetrix/" + \
           symmetrix_id + "/storagegroup"

    sr = requests.get(sURL, auth=(USER, PASS), verify=False)
    sresponse = sr.json()

    # Check if a message was returned. If there is a message, report the
    # message and then skip to the next VMAX.

    if 'message' in sresponse:
        logger.warn(sresponse.get('message') + ". " + symmetrix_id + " array is being skipped.")
        continue

    else:
        storage_group_list = sresponse["storageGroupId"]

    for storage_group_id in storage_group_list:
        # For each SG in a given VMAX, get SRDFA_MBSent metric, sum it up
        # across yesterday and write it out to csv file.
        data = generate_payload(symmetrix_id, storage_group_id)
        headers = {
            'content-type': 'application/json',
            'accept': 'application/json'
        }
        ss_url = "https://" + LOCATION + "/univmax/restapi/performance/StorageGroup/metrics"
        ssr = requests.post(ss_url, data=json.dumps(data, sort_keys=True, indent=4),
                            auth=(USER, PASS), headers=headers, verify=False)
        ssresponse = ssr.json()

        # If response back includes a message instead of expected output, then
        # chances are the VMAX isn't local. Skip to next VMAX but report up
        # error.
        if 'message' in ssresponse:
            message = ssresponse.get('message') + ". " + symmetrix_id + " array is being skipped."
            logger.warn(message)
            break

        result = ssresponse["resultList"]["result"]

        total = 0

        # Grab Total MB Sent for a given SG
        for item in result:
            total += item['SRDFA_MBSent']

        print("Writing to file: {0}, {1}, {2}, {3}".format(
            timestamp, symmetrix_id, storage_group_id, total))

        with open('SRDFA_Reporter.csv', 'a') as csvfile:
            writer = csv.writer(csvfile, delimiter=',',
                                quotechar=',', quoting=csv.QUOTE_MINIMAL)
            writer.writerow([str(timestamp), symmetrix_id,
                             storage_group_id, str(total)])
