#!/bin/bash

LOGFILE="input_voltage.log"

while true; do
    timestamp=$(date "+%Y-%m-%d %H:%M:%S")

    int_part_hex=$(i2cget -y 1 0x08 1)
    dec_part_hex=$(i2cget -y 1 0x08 2)

    int_part=$((16#${int_part_hex#0x}))
    dec_part=$((16#${dec_part_hex#0x}))

    # Scale decimal part by 10 to handle tenths correctly
    voltage=$(printf "%.2f" "$(bc <<< "scale=2; $int_part + $dec_part/100")")

    echo "$timestamp - Voltage: $voltage V" >> "$LOGFILE"
    sleep 10
done
