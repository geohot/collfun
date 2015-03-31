#!/bin/sh
#time stdbuf -i0 -o0 -e0 ../minisat_blbd/minisat_blbd/code/simp/minisat_release formula_fg | tee out
time stdbuf -i0 -o0 -e0 ../minisat/core/minisat_release formula_fg | tee out

