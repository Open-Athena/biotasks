# Specification with read-only package inspection

The source notebook, preparation exports, executed reference, output audit and
task policy are unchanged from specification 005/006. This input adds a catalog
derived programmatically from the hash-verified reference lock and recorded
installed versions. The worker chooses which packages and functions to inspect.
There are no notebook-specific symbol lists or manually supplied scientific answers.

The three tools list distribution members, search literal text and read file line
ranges. They download only catalogued PyPI distributions, verify locked hashes and
sizes, and never extract, install, import or execute package code. Universal wheels
provide distributed Python source. Other packages use their locked source archive;
that does not prove the installed native binary's implementation or build options.
Unsupported or unavailable distributions remain evidence gaps. Searches paginate
at 100 matches with an explicit continuation offset; reads identify full file
hashes and total line counts.

One GLM-5.3 medium specification session may use multiple inspection turns and
submit through Repo2RLEnv's native artifact tools. Local schema validation remains
mandatory; invalid submissions receive feedback within the same session. There
is no automatic new session or transport retry. No server-side `response_format`
constraint is requested, and this is not a claim that the provider's tool-argument
generation is unconstrained or guaranteed correct.

The existing two-hour campaign deadline and 600-second per-request timeout remain.
As with the tool-enabled setup worker, there is no additional request-count or
token/byte cap; all calls are counted and original traces retained. This uses the
approved free endpoint and reserved CPU host, with no Daytona sandbox or GPU.
Only specification runs: no scientific execution, construction, solver or viewer
update. A schema-valid submission still requires content review.
