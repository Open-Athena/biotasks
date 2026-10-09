FROM debian:trixie

# Solver environment for biotasks/methylkit-cpg-group-methylation.
# Mirrors the author-side setup recipe that successfully built native
# methylKit 1.33.3 from pinned source 32212a6cc2046e97371eb528533964c1e1a54afa.
# All solver dependencies are preinstalled; the task runs without internet.
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        r-base-core r-base-dev r-bioc-genomicranges r-bioc-iranges \
        r-bioc-s4vectors r-bioc-biocgenerics r-bioc-qvalue r-bioc-rhtslib \
        r-bioc-rsamtools r-bioc-rtracklayer r-bioc-limma r-cran-data.table \
        r-cran-rcpp r-cran-kernsmooth r-cran-gtools r-cran-mclust r-cran-mgcv \
        r-cran-r.utils r-cran-lattice r-cran-mass r-cran-nlme r-cran-survival \
        r-cran-matrix libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# CRAN/Bioconductor dependencies of methylKit not in Debian.
RUN Rscript -e 'options(timeout=120); install.packages(c("coda", "bbmle"), repos="https://cloud.r-project.org", Ncpus=2); install.packages("fastseg", repos="https://bioconductor.org/packages/release/bioc", Ncpus=2)'

# Pinned sources staged next to this Dockerfile (hashes in environment/versions.txt).
COPY emdbook.tar.gz methylKit.tar.gz /tmp/src/
RUN cd /tmp/src \
    && tar xzf emdbook.tar.gz && tar xzf methylKit.tar.gz \
    && R CMD INSTALL emdbook \
    && R CMD INSTALL methylKit-32212a6cc2046e97371eb528533964c1e1a54afa \
    && rm -rf /tmp/src

COPY inputs /app/inputs
WORKDIR /app
