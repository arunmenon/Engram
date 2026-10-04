Sample webhook payloads for the PDLC source adapters (ADR-0018 phase 1).

Hand-written to the documented shapes of GitHub (`pull_request`,
`pull_request_review`, `check_run`, `release`, `deployment_status`,
`issues`) and Jira (`jira:issue_created`, `jira:issue_updated`) webhook
deliveries, trimmed to the fields the adapters read plus a few they
ignore. They are not recorded from a real repository or site.
