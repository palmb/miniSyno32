#!/usr/bin/env bash

for file in *.py; do
  echo "upload $file to /$file"
  ampy put "$file"
done