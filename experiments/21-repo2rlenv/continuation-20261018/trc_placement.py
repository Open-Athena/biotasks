"""Restrict CPU controller placement to explicitly observed reserved TRC slices."""
from iris.cluster.constraints import Constraint, ConstraintOp


def existing_trc_constraints(observed_reserved_slice_names):
    names = sorted(set(observed_reserved_slice_names))
    if not names or any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError('Explicit observed reserved TRC slice names are required')
    return [
        Constraint.create(key='zone', op=ConstraintOp.EQ, value='us-central2-b'),
        Constraint.create(key='device-type', op=ConstraintOp.EQ, value='tpu'),
        Constraint.create(key='preemptible', op=ConstraintOp.EQ, value='false'),
        Constraint.create(key='tpu-name', op=ConstraintOp.IN, values=names),
    ]
