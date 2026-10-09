import assert from "node:assert/strict";
import { mapRemotePath } from "./remote_paths.mjs";

assert.equal(mapRemotePath("/host/work", "/host/work", "/workspace"), "/workspace");
assert.equal(mapRemotePath("/host/work/result.json", "/host/work", "/workspace"), "/workspace/result.json");
assert.equal(mapRemotePath("/output/result.json", "/host/work", "/workspace"), "/output/result.json");
assert.equal(mapRemotePath("/host/work-other/x", "/host/work", "/workspace"), "/host/work-other/x");
assert.equal(mapRemotePath("/host/work/x", "/host/work", "/"), "/x");
console.log("Five remote path mapping checks passed");
