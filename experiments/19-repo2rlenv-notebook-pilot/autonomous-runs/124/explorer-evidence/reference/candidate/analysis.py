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

# # Build an HMM from a multiple sequence alignment

import pyhmmer
pyhmmer.__version__

alphabet = pyhmmer.easel.Alphabet.amino()

# ## Loading the alignment

# A new HMM can be built from a single sequence, or from a multiple sequence alignment. Let's load an alignment in digital mode so that we can build our HMM. We can use a `MSAFile` to read an alignment from a file in one of the supported formats (such as [Stockholm](https://www.tbi.univie.ac.at/RNA/ViennaRNA/doc/html/file_formats.html#msa-formats-stockholm), [Clustal](https://www.tbi.univie.ac.at/RNA/ViennaRNA/doc/html/file_formats.html#msa-formats-clustal), [aligned FASTA](https://www.tbi.univie.ac.at/RNA/ViennaRNA/doc/html/file_formats.html#msa-formats-fasta), *etc*; see the `MSAFile` documentation for the complete list):

with pyhmmer.easel.MSAFile("/inputs/msa/LuxC.sto", digital=True, alphabet=alphabet) as msa_file:
    msa = msa_file.read()

# <div class="alert alert-info">
#
# Note
#     
# In this example, we load a multiple sequence alignment from a file, but if your program produces alignment and you wish to make an HMM out of them, you can instantiate a `TextMSA` object yourself, e.g.:
#     
# ```python
# seq1 = pyhmmer.easel.TextSequence(name="seq1", sequence="WVPKQDFT")
# seq2 = pyhmmer.easel.TextSequence(name="seq2", sequence="WL--PQGE")
# msa  = pyhmmer.easel.TextMSA(name="msa", sequences=[seq1, seq2])
# ```
#
# Because we need a `DigitalMSA` to build the HMM, you will have to convert it first:
#     
# ```python
# msa_d = msa.digitize(alphabet) 
# ```
# </div>

# ## Building an HMM
#
# Now that we have a multiple alignment loaded in memory, we can build a pHMM using a `pyhmmer.plan7.Builder`. This also requires a Plan7 background model to compute the transition probabilities.

builder = pyhmmer.plan7.Builder(alphabet)
background = pyhmmer.plan7.Background(alphabet)
hmm, _, _ = builder.build_msa(msa, background)

# <div class="alert alert-warning">
#
# Warning
#     
# HMMs must always have a name. The `Builder` will attempt to use the `MSA` name, but in the event your alignment file does not contain a name for the whole alignment (for instance, a `#=GF ID` line in a [Stockholm file](https://en.wikipedia.org/wiki/Stockholm_format)), this method will fail:
#     
# ```python
# >>> anonymous_msa = pyhmmer.easel.TextMSA(sequences=[seq1, seq2])
# >>> builder.build_msa(anonymous_msa)
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# ValueError: Could not build HMM: Unable to name the HMM.
# ```    
#
# If your alignment is missing a name, you can assign one manually by setting the `MSA.name` property, e.g.:
#
# ```python
# msa.name = "protein_family_01"
# ```
#     
# </div>

# We can have a look at the consensus sequence of the HMM with the `consensus` property:

hmm.consensus

# ## Saving the resulting HMM

# Now that we have an HMM, we can save it to a file to avoid having to rebuild it every time. Using the `HMM.write` method lets us write the HMM in ASCII or binary format to an arbitrary file. The resulting file will also be compatible with the `hmmsearch` binary if you wish to use that one instead of PyHMMER.

with open("LuxC.hmm", "wb") as output_file:
    hmm.write(output_file)

# ## Applying the HMM to a sequence database

# Once a pHMM has been obtained, it can be applied to a sequence database with the `pyhmmer.plan7.Pipeline` object. Let's iterate over the protein sequences in a FASTA to see if our new HMM gets any hits:

pipeline = pyhmmer.plan7.Pipeline(alphabet, background=background)
with pyhmmer.easel.SequenceFile("/inputs/seqs/LuxC.faa", digital=True, alphabet=alphabet) as seq_file:
    hits = pipeline.search_hmm(hmm, seq_file)

# We can then query the `TopHits` object to access the domain hits in the sequences:

ali = hits[0].domains[0].alignment
print(ali)

# Finally, we can save the results in tabular format similar to what `hmmsearch` would have produced:

with open("LuxC.domtbl", "wb") as f:
    hits.write(f, format="domains")
