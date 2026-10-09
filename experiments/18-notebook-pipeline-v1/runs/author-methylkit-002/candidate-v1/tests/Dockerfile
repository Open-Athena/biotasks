FROM debian:trixie

# Verifier environment for biotasks/methylkit-cpg-group-methylation.
# Contains the deterministic grader and its expected-value asset only;
# no reference sources, seed material or solver inputs.
RUN apt-get update && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

COPY test.sh /tests/test.sh
COPY grader.py /tests/grader.py
COPY expected/ /tests/expected/
RUN chmod +x /tests/test.sh /tests/grader.py
