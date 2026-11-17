# Northstar Payments: incident visibility pilot
Synthetic customer exercise; all names, identifiers and events are invented.

## Purpose and boundaries
Northstar operates checkout services in US and EU accounts. Operators need to see which incidents affect a service and preserve an incident's title when resolution notifications omit it. Exclude on-call scheduling, alert deduplication, postmortems, natural-language extraction and automated remediation.

## Vocabulary and identity
An Incident is identified by the ordered pair account and id. Incident numbers can repeat across accounts. Incident INC-1042 in us is different from INC-1042 in eu.
A Service is identified by the ordered pair account and name. The checkout service exists independently in both accounts.
Account is an identity field, not a separate graph node in this pilot.
An Incident AFFECTS exactly one Service. Both implement source provenance; Incident also has a lifecycle.

## Lifecycle and updates
New incidents start open. Only an open incident may transition to resolved. Reopening is out of scope.
Resolution events still upsert the incident for provenance, then apply the guarded transition.
A missing title on an update preserves the stored title. Null titles are invalid under the interface contract.
The service association is established by the opened event and never changed by resolution.

## Source authority
The sole producer in this pilot is northstar-monitor. It is trusted for these synthetic events. This is a sandbox identity; it is not a production credential grant.

## Event handling
incident.opened creates or updates Incident and Service and the AFFECTS relationship.
incident.resolved records provenance and resolves the Incident; it must not invent a new service.
incident.comment is ledger-only: keep the event but do not write domain nodes or relationships.
A missing account is invalid and must be rejected before graph projection.

## Questions and test oracle
For Service:us|checkout, which incidents affect it? Expected exactly Incident:us|INC-1042 and Incident:us|INC-1043.
For Service:eu|checkout, which incidents affect it? Expected exactly Incident:eu|INC-1042.
These are graph retrieval questions, not free-form narrative answer generation. Use intent incidents_for_service, traversing AFFECTS from the given Service seed and returning Incident nodes only. The two questions and answers are fixed before execution. Do not broaden expected answers to make a failing run pass.
