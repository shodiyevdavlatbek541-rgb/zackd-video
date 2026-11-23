#!/bin/bash
# part A: 0-17.767 s full-res shots; part B: the blurred question plate
set -e
ffmpeg -v error -y -framerate 30 -start_number 0 -i frames/f_%04d.jpg -frames:v 533 \
  -vf "scale=1080:1920,eq=saturation=1.06:contrast=1.03,format=yuv420p" -r 30 -c:v libx264 -preset fast -crf 14 part_a.mp4
mkdir -p plate; n=0
for ((f=533;f<780;f+=2)); do cp "frames/f_$(printf %04d $f).jpg" "plate/p_$(printf %04d $n).jpg"; n=$((n+1)); done
ffmpeg -v error -y -framerate 15 -i plate/p_%04d.jpg -filter_complex "
[0:v]scale=1080:1920:flags=bicubic,eq=saturation=1.06:contrast=1.03,fps=30,format=yuv420p,split=3[s][m][h];
[m]gblur=sigma=7,format=yuva420p,fade=t=in:st=0.05:d=0.3:alpha=1[m1];
[h]gblur=sigma=17,eq=brightness=-0.09,format=yuva420p,fade=t=in:st=0.22:d=0.42:alpha=1[h1];
[s][m1]overlay=format=auto[o1];[o1][h1]overlay=format=auto,tpad=stop_mode=clone:stop_duration=1,format=yuv420p[v]" \
  -map "[v]" -frames:v 247 -r 30 -c:v libx264 -preset fast -crf 14 part_b.mp4
ffmpeg -v error -y -i part_a.mp4 -i part_b.mp4 -i mix.wav -filter_complex \
 "[0:v]setsar=1[a];[1:v]setsar=1[b];[a][b]concat=n=2:v=1:a=0,fps=30,ass=titles.ass,format=yuv420p[v]" \
 -map "[v]" -map 2:a -c:v libx264 -preset slow -crf 18 -maxrate 20M -bufsize 40M -c:a aac -b:a 320k -movflags +faststart -t 26 Insult_case_v3.mp4
