#!/bin/bash
# start_rtk_base.sh
# Script to send GNSS data to our NTRIP caster using str2str from RTKLIB

# Set debugging - send output to a log file
LOGFILE="/home/artem/2025_Sem1_Capstone/start_rtk_base.log"
exec > >(tee -i $LOGFILE)
exec 2>&1

echo "Starting RTK Base Station Service - $(date)"

# ===== Configuration Variables =====

# ===== Input Variables =====
# Serial device connected to your GNSS module
SERIAL_PORT="ttyACM0"
# GNSS baud rate
BAUD_RATE="115200"
# Data format settings: data bits, parity, stop bits, flow control
DATA_BITS="8"
PARITY="n"
STOP_BITS="1"
FLOW_CONTROL="off"  # 'off' means no hardware flow control

# ===== Output Variables of NTRIP Caster =====

NTRIP_USER="user1"
NTRIP_PASS="abc123"
NTRIP_CASTER="96.0.77.42"
NTRIP_CASTER_TEST="10.244.77.204"	#IP of a local machine for troubleshooting
NTRIP_PORT="2101"                   # Change if your caster uses a different port
MOUNTPOINT="rpiBase1"             # The mountpoint or channel name on the caster

# ===== Console Command =====
STR2STR_CMD="/home/artem/2025_Sem1_Capstone/RTKLIB/app/str2str/gcc/str2str -in serial://${SERIAL_PORT}:${BAUD_RATE}:${DATA_BITS}:${PARITY}:${STOP_BITS}:${FLOW_CONTROL} -out ntrips://:${NTRIP_PASS}@${NTRIP_CASTER}:${NTRIP_PORT}/${MOUNTPOINT} -msg 1005,1077,1087,1097,1127,1230"

# Added a sleep so that the base station is powered on the GNSS Module can get it's current positional data before the connection is made.
echo "GNSS Module surveying in"
sleep 300
echo "Survey in complete!"

echo "Executing command:"
echo "$STR2STR_CMD"

# ===== Execute the Command =====
# Using eval so that the constructed command is executed.
eval $STR2STR_CMD

echo "RTK Base Station process terminated - $(date)"