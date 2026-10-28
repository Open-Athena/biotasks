# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: nomarker
#       format_version: '1.0'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# # Simulating Deletions

import pandas
from time import time

from cobra.io import load_model
from cobra.flux_analysis import (
    single_gene_deletion, single_reaction_deletion, double_gene_deletion,
    double_reaction_deletion)

cobra_model = load_model("textbook")
ecoli_model = load_model("iJO1366")

# ## Knocking out single genes and reactions

# A commonly asked question when analyzing metabolic models is what will happen if a certain reaction was not allowed to have any flux at all. This can tested using cobrapy by

print('complete model: ', cobra_model.optimize())
with cobra_model:
    cobra_model.reactions.PFK.knock_out()
    print('pfk knocked out: ', cobra_model.optimize())

# For evaluating genetic manipulation strategies, it is more interesting to examine what happens if given genes are knocked out as doing so can affect no reactions in case of redundancy, or more reactions if gene when is participating in more than one reaction.

print('complete model: ', cobra_model.optimize())
with cobra_model:
    cobra_model.genes.b1723.knock_out()
    print('pfkA knocked out: ', cobra_model.optimize())
    cobra_model.genes.b3916.knock_out()
    print('pfkB knocked out: ', cobra_model.optimize())

# ## Single Deletions

# Perform all single gene deletions on a model

deletion_results = single_gene_deletion(cobra_model)

# These can also be done for only a subset of genes

single_gene_deletion(cobra_model, cobra_model.genes[:20])

# This can also be done for reactions

single_reaction_deletion(cobra_model, cobra_model.reactions[:20])

# ## Double Deletions

# Double deletions run in a similar way.

double_gene_deletion(
    cobra_model, cobra_model.genes[-5:]).round(4)

# By default, the double deletion function will automatically use multiprocessing, splitting the task over up to 4 cores if they are available. The number of cores can be manually specified as well. Setting use of a single core will disable use of the multiprocessing library, which often aids debugging.

start = time()  # start timer()
double_gene_deletion(
    ecoli_model, ecoli_model.genes[:25], processes=2)
t1 = time() - start
print("Double gene deletions for 200 genes completed in "
      "%.2f sec with 2 cores" % t1)

start = time()  # start timer()
double_gene_deletion(
    ecoli_model, ecoli_model.genes[:25], processes=1)
t2 = time() - start
print("Double gene deletions for 200 genes completed in "
      "%.2f sec with 1 core" % t2)

print("Speedup of %.2fx" % (t2 / t1))

# Double deletions can also be run for reactions.

double_reaction_deletion(
    cobra_model, cobra_model.reactions[2:7]).round(4)

# ## Accessing individual deletion results
#
# Note that the indices for deletions are python [set](https://docs.python.org/3.8/library/stdtypes.html#set-types-set-frozenset) objects. This is the appropriate type since the order of deletions does not matter. Deleting reaction 1 and reaction 2 will have the same effect as deleting reaction 2 and reaction 1. 
#
# To make it easier to access results all DataFrames returned by COBRAPpy deletion functions have a `knockout` indexer that makes that a bit simpler. Each entry in the indexer is treated as a single deletion entry. So you need to pass sets for double deletions.

single = single_reaction_deletion(cobra_model)
double = double_reaction_deletion(cobra_model)

print(single.knockout["ATPM"])
print(double.knockout[{"ATPM", "TKT1"}])

# This can be used to get several deletions at once and will also work for Reaction or Gene objects (depending on what you deleted) directly.

atpm = cobra_model.reactions.ATPM
tkt1 = cobra_model.reactions.TKT1
pfk = cobra_model.reactions.PFK

print(single.knockout[atpm, tkt1, pfk])
print(double.knockout[{atpm, tkt1}, {atpm, pfk}, {atpm}])



