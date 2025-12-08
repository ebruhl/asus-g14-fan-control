#!/bin/bash
GPU_STATUS_PATH="/sys/bus/pci/devices/0000:01:00.0/power/runtime_status"
GPU_CONTROL_PATH="/sys/bus/pci/devices/0000:01:00.0/power/control"
THROTTLE_POLICY="/sys/devices/platform/asus-nb-wmi/throttle_thermal_policy"
PLATFORM_PROFILE="/sys/firmware/acpi/platform_profile"
CPU_BOOST="/sys/devices/system/cpu/cpu0/cpufreq/boost"
CHECK_INTERVAL=2
RESET_COUNTER=0
GPU_WAKE_COUNTER=0
DEBUG_LOG="$HOME/g14-nuclear-debug.log"

echo "=== NUCLEAR FAN CONTROL V2 ===" | tee -a $DEBUG_LOG
echo 0 | sudo tee $CPU_BOOST > /dev/null
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "powersave" | sudo tee $cpu > /dev/null 2>&1
done

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    GPU_STATUS=$(cat $GPU_STATUS_PATH)
    GPU_CONTROL=$(cat $GPU_CONTROL_PATH)
    CPU_TEMP=$(sensors | grep "Tctl:" | awk '{print $2}' | sed 's/+//;s/°C//' | cut -d'.' -f1)
    FAN_SPEED=$(sensors | grep "cpu_fan:" | awk '{print $2}')
    THROTTLE_VAL=$(cat $THROTTLE_POLICY)
    PLATFORM_VAL=$(cat $PLATFORM_PROFILE)
    
    if [ "$GPU_CONTROL" != "auto" ]; then
        echo "auto" | sudo tee $GPU_CONTROL_PATH > /dev/null
    fi
    
    if [ "$CPU_TEMP" -lt 60 ]; then
        echo "2" | sudo tee $THROTTLE_POLICY > /dev/null
        echo "quiet" | sudo tee $PLATFORM_PROFILE > /dev/null
    elif [ "$CPU_TEMP" -lt 75 ]; then
        echo "0" | sudo tee $THROTTLE_POLICY > /dev/null
    else
        echo "1" | sudo tee $THROTTLE_POLICY > /dev/null
    fi
    
    sleep $CHECK_INTERVAL
done
