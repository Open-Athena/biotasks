# Independent instruction review

Status: native issue validation passed; independent instruction-quality review failed. This is source inspection, not independent grader execution.

The generated title and explanation claim that the defective numerator is always len(counts), inflating every result. The preserved mutation.diff instead changes `(upper - lower) / denom` to `(upper + lower) / denom`. Its examples happen to have upper + lower equal to the input length; that does not justify the general diagnosis.

A counterexample follows directly from the pinned implementation's index selection: for ten increasing counts with lower_quantile=0 and upper_quantile=1, lower=0 and upper=9. Both the healthy and defective numerators are 9, while len(counts)=10. Thus the claimed universal total-species numerator and universal inflation are false. This calculation is a source-derived check, not a new repository execution.

The source documentation also explicitly defines inward-rounded quantile indices and discusses how ties differ from an alternative literature convention. The generated report's count-of-abundances explanation must not silently replace that implementation contract. Preserve all original model bytes. Any revised instruction must be a separate intervention, retaining verified observable input/output examples and boundary behavior while removing unsupported internal diagnoses. No independent acceptance or solver score is assigned.
