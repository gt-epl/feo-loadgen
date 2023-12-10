#!/bin/bash
lim=$1
file=$2
out=$3

if [ -z $out ]; then
  #go run . -limit $lim -trace $file > /dev/null
  ./loadgen -limit $lim -trace $file > /dev/null
  
else
  go run . -limit $lim -trace $file > $out
fi
