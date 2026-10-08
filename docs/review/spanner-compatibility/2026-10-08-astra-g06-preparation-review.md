# Astra G06 separate database preparation review

Scoped source review only, prior to provisioning. Original review identified finalizer skipping second handle cleanup/tracking on a close exception, and false successful summaries on preparation failure. Both fixed in e8d4a84; focused recheck cleared remaining blockers. 3956284 additionally unsets emulator routing. No broad unfinished G06-spec review or cloud acceptance implied.

Actual preparation 20261008-cloud-g06-prepare-01 failed before creation at getDdl permission check for engram-g06-target. No creation intent or operation submission exists. G05 fingerprints and owner epoch43 match before and after. The failed preparation check and successful G05 preservation check are retained. Cloud acceptance is blocked on separate-database access; local G06 implementation continues. User was asked to arrange creation/access for engram-g06-target; no access approval inferred from elapsed time.
