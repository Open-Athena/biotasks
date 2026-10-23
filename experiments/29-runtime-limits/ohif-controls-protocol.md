# Original OHIF export controls

Run the four frozen OHIF exports (6334, 6339, 6346, 6352) through Harbor 0.6.6 nop/oracle controls, using the successful recorded-action reconstruction image. All 40 task files retain original bytes and modes. No generation, model calls, command repairs, target changes or parser changes.

The executed Scanpy controls supervisor is adapted only for OHIF identities and paths. The common control runner, Docker resource wrapper and setup remain unchanged. Tasks receive 1 CPU and 6 GiB; original verifier timeout is 300 seconds, multiplier 1. Each of eight trials reserves 900 seconds including the original inner retry allowance. Total trial allowance is 7,200 seconds, supervisor work 8,400, Iris job 8,700 (including cleanup). One attempt on the image's existing reserved worker; 4 allocated CPUs, 16 GiB memory and disk. No new capacity or credentials in the remote controller.

Budget: ten terminal jobs used 1.7413044 CPU-hours. Conservatively reserve the full 9.6666667 hours for both Scanpy and OHIF controls, totaling 21.0746378 within 32. Scanpy image cleanup also reserves the full OHIF control bound. Unexpected active campaign jobs block submission.

The controller verifies retained image identity/ownership, creates only a temporary original-image alias, removes owned trial/controller resources and the alias after execution, and archives evidence. The retained reconstruction image is removed separately after verified archive readback. Missing, timed-out or unstarted controls remain failures/incomplete evidence. These are controls of existing exports, not new tasks. Mutable dependency reconstruction may differ from the deleted original image.

Preparation verified the 40 archive member hashes, original file modes, eight commands and 7,200-second aggregate allowance; five Python entrypoints passed syntax checks. Native results remain pending.
