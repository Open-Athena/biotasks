"""Recover only idempotent file overwrites, never model or command dispatch."""

import asyncio
import hashlib
import shutil
import tempfile
import time
from pathlib import Path

from daytona.common.errors import DaytonaError
from repo2rlenv.execution.lifecycle import save_record


def freeze_file(source, snapshot):
    shutil.copyfile(source, snapshot)
    snapshot.chmod(0o400)
    with snapshot.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest(), snapshot.stat().st_size


async def upload_same_file(worker, source, target, receipt, deadline):
    """Use one frozen byte sequence and the original SDK/stage time envelope.

    The SDK documents upload_file as an overwrite of the destination. Repeating
    identical bytes is safe even when a 5xx follows delivery. No other mutation
    or ambiguous command acknowledgement is admitted by this helper.
    """
    receipt.parent.mkdir(parents=True)
    record = {
        "source_name": source.name,
        "target": target,
        "started": time.time(),
        "state": "incomplete",
        "attempts": [],
    }
    save_record(receipt, record)
    try:
        # One total envelope, not a fresh 30-minute SDK allowance per retry.
        end = min(deadline - 15, time.time() + 1800)
        with tempfile.TemporaryDirectory(prefix="snapshot-", dir=receipt.parent) as temporary:
            snapshot = Path(temporary) / source.name
            digest, size = await asyncio.to_thread(freeze_file, source, snapshot)
            record.update(sha256=digest, bytes=size, deadline=end)
            save_record(receipt, record)
            async with asyncio.timeout(max(0, end - time.time())):
                for number in range(1, 4):
                    if time.time() >= end:
                        raise TimeoutError("Upload exhausted its existing time envelope")
                    attempt = {"number": number, "started": time.time()}
                    record["attempts"].append(attempt)
                    save_record(receipt, record)
                    try:
                        await asyncio.to_thread(worker.upload, snapshot, target)
                    except BaseException as error:
                        status = getattr(error, "status_code", None)
                        attempt.update(
                            error_type=type(error).__name__,
                            http_status=status if type(status) is int else None,
                        )
                        retry = (
                            isinstance(error, DaytonaError)
                            and type(status) is int
                            and status in {500, 502, 503, 504}
                            and number < 3
                        )
                        attempt["retry_eligible"] = retry
                        if not retry:
                            raise
                    else:
                        if time.time() >= end:
                            raise TimeoutError("Upload returned after its existing deadline")
                        attempt["completed"] = True
                        record["state"] = "uploaded"
                        return
                    finally:
                        attempt["finished"] = time.time()
                        save_record(receipt, record)
                    await asyncio.sleep(0.5 * 2 ** (number - 1))
    except BaseException as error:
        record["error_type"] = type(error).__name__
        raise
    finally:
        record["finished"] = time.time()
        save_record(receipt, record)
