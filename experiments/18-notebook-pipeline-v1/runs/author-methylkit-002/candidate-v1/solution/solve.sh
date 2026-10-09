#!/bin/bash
# Reference solution: independent text-table implementation of the instruction.
# Written to be independent of methylKit so it cross-checks the native reference.
set -euo pipefail
INPUT_DIR="${INPUT_DIR:-/app/inputs}"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"
export INPUT_DIR OUTPUT_DIR
mkdir -p "$OUTPUT_DIR"

Rscript - <<'EOF'
library(data.table)

input_dir <- Sys.getenv("INPUT_DIR")
output_dir <- Sys.getenv("OUTPUT_DIR")
files <- c(
    test1 = file.path(input_dir, "test1.myCpG.txt"),
    test2 = file.path(input_dir, "test2.myCpG.txt"),
    ctrl1 = file.path(input_dir, "control1.myCpG.txt"),
    ctrl2 = file.path(input_dir, "control2.myCpG.txt")
)

# Per-sample coverage filter: coverage >= 10 (inclusive), then keep only
# coverage strictly below the sample's 99th percentile (type-7 quantile)
# of the surviving coverages, matching methylKit's filterByCoverage.
filter_sample <- function(path) {
    d <- fread(path)
    d <- d[coverage >= 10]
    q99 <- as.numeric(quantile(d$coverage, probs = 0.99))
    d[coverage < q99]
}

filtered <- lapply(files, filter_sample)

# Rename each sample's count columns, then complete-case join on
# (chr, base, strand) with no destranding.
keycols <- c("chr", "base", "strand")
prep <- function(s) {
    d <- filtered[[s]][, .(chr, base, strand, coverage, freqC)]
    setnames(d, c("coverage", "freqC"), c(paste0("cov_", s), paste0("freq_", s)))
    d
}
joined <- Reduce(function(a, b) merge(a, b, by = keycols), lapply(names(files), prep))

# Percent methylation from reconstructed integer methylated counts
# (round half to even, matching R's round()).
for (s in names(files)) {
    cov <- joined[[paste0("cov_", s)]]
    freq <- joined[[paste0("freq_", s)]]
    num_cs <- round(cov * freq / 100)
    joined[[paste0("pct_", s)]] <- 100 * num_cs / cov
}

joined[, test_mean_pct := (pct_test1 + pct_test2) / 2]
joined[, ctrl_mean_pct := (pct_ctrl1 + pct_ctrl2) / 2]
joined[, diff_pct := test_mean_pct - ctrl_mean_pct]

out <- joined[order(chr, base, strand),
    .(chr, base, strand, pct_test1, pct_test2, pct_ctrl1, pct_ctrl2,
      test_mean_pct, ctrl_mean_pct, diff_pct)]

fwrite(out, file.path(output_dir, "group_methylation.tsv"), sep = "\t", quote = FALSE)
cat(sprintf("wrote %d loci\n", nrow(out)))
EOF
