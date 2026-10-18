# Issue

**Title:** QCPSuperimposer returns a wrong rotation when the reference point set is collinear

## Description

When the reference set is collinear and the moving set is the same points after a non-trivial rigidrotation, `QCPSuperimposer` returns `get_rms()` ≈ 0, but returns the identity rotation matrix, so `get_transformed()` is not aligned at all and the true RMSD of the transformed coordinates is large. 

I think this may be the same symptom class as #5004, on an input that #5005 did not cover.

Code for reproduction:

```python
import numpy as np
from Bio.PDB.qcprot import QCPSuperimposer
from Bio.SVDSuperimposer import SVDSuperimposer

# reference: three collinear points
ref = np.array([[0., 0., 0.], [1., 0., 0.], [2., 0., 0.]])

# moving set: the same points after a rigid rotation + translation
theta = 0.9
ax = np.array([1., 2., 3.]); ax /= np.linalg.norm(ax)
K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
R = np.eye(3) + np.sin(theta) * K + (1 - np.cos(theta)) * K @ K
mob = ref @ R.T + np.array([5., -2., 7.])

for name, S in [("QCP", QCPSuperimposer), ("SVD", SVDSuperimposer)]:
    s = S(); s.set(ref, mob); s.run()
    t = s.get_transformed()
    rmsd_true = np.sqrt(((ref - t) ** 2).sum() / 3)
    print(f"{name}: get_rms()={s.get_rms():.3e}   RMSD(transformed)={rmsd_true:.3e}")
```

Output:

```
QCP: get_rms()=0.000e+00   RMSD(transformed)=6.845e-01
SVD: get_rms()=1.125e-15   RMSD(transformed)=1.125e-15
```

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `5bbc6c12c505` and running the modified tests.