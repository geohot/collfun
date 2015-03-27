#!/bin/sh
time stdbuf -i0 -o0 -e0 ../minisat/minisat_blbd/binary/minisat_blbd formula_fg | tee out


