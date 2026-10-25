#!/bin/sh
set -eu
mkdir -p /inputs
install -m 0644 /work/setup/original-inputs/ENCFF401MQL.bed.gz /inputs/ENCFF401MQL.bed.gz
install -m 0644 /work/setup/original-inputs/MA0139.1.tsv.gz /inputs/MA0139.1.tsv.gz
install -m 0644 /work/setup/original-inputs/ENCFF356LFX.bed.gz /inputs/ENCFF356LFX.bed.gz
