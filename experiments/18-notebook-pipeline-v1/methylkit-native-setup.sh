#!/bin/bash
# Operator-prepared replay of successful installation steps in author session 1.
# Run only inside the authorized remote author worker, never on the shared VM.
# Bound the whole script externally: timeout 480 bash methylkit-native-setup.sh.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive MAKEFLAGS=-j1
workspace=$PWD
cache=$(mktemp -d /tmp/biotasks-methylkit-setup.XXXXXX)
exec > >(tee "$workspace/native-setup.log") 2>&1
timeout 30 apt-get update
timeout 240 apt-get install -y --no-install-recommends \
    r-base-core r-base-dev r-bioc-genomicranges r-bioc-iranges \
    r-bioc-s4vectors r-bioc-biocgenerics r-bioc-qvalue r-bioc-rhtslib \
    r-bioc-rsamtools r-bioc-rtracklayer r-bioc-limma r-cran-data.table \
    r-cran-rcpp r-cran-kernsmooth r-cran-gtools r-cran-mclust r-cran-mgcv \
    r-cran-r.utils r-cran-lattice r-cran-mass r-cran-nlme r-cran-survival \
    r-cran-matrix libcurl4-openssl-dev
cd "$cache"
timeout 30 curl --fail --location --output emdbook.tar.gz \
    https://cran.r-project.org/src/contrib/Archive/emdbook/emdbook_1.3.13.tar.gz
timeout 30 curl --fail --location --output methylKit.tar.gz \
    https://github.com/al2na/methylKit/archive/32212a6cc2046e97371eb528533964c1e1a54afa.tar.gz
sha256sum emdbook.tar.gz methylKit.tar.gz > "$workspace/native-source-sha256.txt"
timeout 120 Rscript -e 'options(timeout=30); install.packages(c("coda", "bbmle"), repos="https://cloud.r-project.org", Ncpus=1); install.packages("fastseg", repos="https://bioconductor.org/packages/release/bioc", Ncpus=1)'
tar xzf emdbook.tar.gz
tar xzf methylKit.tar.gz
timeout 90 R CMD INSTALL emdbook
timeout 120 R CMD INSTALL methylKit-32212a6cc2046e97371eb528533964c1e1a54afa
cd "$workspace"
timeout 30 Rscript -e 'library(methylKit); write.csv(installed.packages()[,c("Package","Version")], "native-packages.csv", row.names=FALSE); capture.output(sessionInfo(), file="native-session-info.txt"); stopifnot(as.character(packageVersion("methylKit")) == "1.33.3")'
printf '%s\n' "$cache/methylKit-32212a6cc2046e97371eb528533964c1e1a54afa/R/backbone.R" > native-source-location.txt
echo 'Native methylKit setup completed; biological reference has not yet run.'
