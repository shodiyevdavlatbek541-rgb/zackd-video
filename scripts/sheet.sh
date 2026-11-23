#!/bin/bash
# sheet.sh out.png files...
o=$1; shift; a=(); f=""; i=0
for p in "$@"; do a+=(-i "$p"); f+="[$i]scale=360:640[v$i];"; i=$((i+1)); done
l=""; c=$(( (i+1)/2 )); [ $i -lt 8 ] && c=$i
for ((j=0;j<i;j++)); do l+="[v$j]"; x=$(( j%c*360 )); y=$(( j/c*640 )); L+="${L:+|}${x}_${y}"; done
ffmpeg -v error -y "${a[@]}" -filter_complex "${f}${l}xstack=inputs=$i:layout=$L:fill=black" -frames:v 1 "$o"
