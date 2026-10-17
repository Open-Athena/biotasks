`Bio.PDB.qcprot.QCPSuperimposer` silently fails on coordinate sets whose reference is collinear. When the reference points all lie on a line and the moving coordinates are those same points after a non-trivial rigid rotation plus translation, `run()` leaves the rotation matrix at the identity: `get_rms()` reports ≈ 0 (which is the true optimum, since a perfect alignment exists) but `get_transformed()` is not aligned at all. `Bio.SVDSuperimposer.SVDSuperimposer` handles the same input correctly.

Reproduction:

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

Current (buggy) output:

```
QCP: get_rms()=0.000e+00   RMSD(transformed)=6.845e-01
SVD: get_rms()=1.125e-15   RMSD(transformed)=1.125e-15
```

Diagnosis: with a collinear reference, every 4x4 cofactor quaternion built inside the QCP routine has a squared norm below the eigenvalue-precision threshold, so the routine falls into its degenerate branch and never derives a rotation — `rot` remains the identity and the translation is consequently wrong as well.

Required behavior after the fix:

- For the input above, `sup.rot` must not be (close to) the identity matrix — `np.allclose(sup.rot, np.eye(3))` must be False.
- `sup.get_transformed()` must reproduce `ref` within 1e-12, i.e. `np.allclose(fitted, ref, atol=1e-12)` must be True, and the RMSD computed as `np.sqrt(((ref - fitted) ** 2).sum() / n_points)` must be 0 to within 1e-12.
- The returned rotation and translation must be mutually consistent, so the transform realized by `get_transformed()` actually achieves the fit.
- The fix must be general: any collinear reference set aligned against a rigidly moved copy of itself (rotation about an arbitrary axis, arbitrary translation) must come out aligned, not only this exact example.
- Non-degenerate inputs must be completely unaffected: for ordinary, non-collinear coordinate sets `QCPSuperimposer` must keep returning the same optimal rotation, translation, and RMSD as before, continuing to agree with `SVDSuperimposer` to roughly 1e-15.
- `Bio.SVDSuperimposer` must keep its current behavior; the correction belongs in the QCP implementation.

Note that `get_rms()` ≈ 0 is the correct optimum for a collinear input, so a near-zero `get_rms()` is not itself the defect — the defect is that the returned rotation/translation do not realize that fit.

Work in `/workspace`. Submit your fix in the existing Python source files under `Bio/PDB/qcprot.py`. Preserve the other public behavior. The environment is offline; dependencies are preinstalled. Grading runs the relevant repository tests in a fresh environment, using your submitted source files.
