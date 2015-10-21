# SRDFA_Reporter

This Python3 script was created to answer the question: "How much data was sent over SRDF/A yesterday on a per VMAX, per SG basis?".

This has been tested successfully on a Mac, Windows, Python2.7, Python3.4 and Unisphere for VMAX v8.0.2.6

**Special Thanks** to [Sean Cummins](https://github.com/seancummins) and [Matt Cowger](https://github.com/mcowger)!

## Usage

Script expects to see three environmentals set:
- `SRUNILOCATION` is the IP:Port of where Unisphere is located. Example: 10.20.30.40:8443
- `SRUSER` is the username for Unisphere
- `SRPASS` is the password for Unisphere

The syntax for setting the environmental variables in Windows is `set SRUSER=smc` in the command prompt. For Mac/Linux you use `export SRUSER=smc` in the terminal window.

The script queries Unisphere for all the VMAX's it sees. It will then walk through every Storage Group in each VMAX and check to see SRDF/A_MBSent metric across a 24 hour period (Yesterday's Midnight to Today's Midnight), skipping any Arrays that aren't local. The data is written to a csv file called `SRDFA_Reporter.csv` in the same directory as the script. If the file already exists, then it will append to the file each time the script is ran. This can be ran as a daily cron job. Any errors that occur will be written/appended to a file called `SRDFA_Reporter_Error_Log.csv`, also in the same directory as the script.



## License
No warranty. No support. But free to use and modify. Enjoy.
