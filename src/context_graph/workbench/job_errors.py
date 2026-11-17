"""Useful failure categories without copying provider responses or customer inputs."""

from __future__ import annotations

from pydantic import ValidationError


class AuthoringValidationError(ValueError):
    """Contains a fixed diagnostic, never model output or uploaded text."""


def proposal_failure_reason(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        codes = {error["type"] for error in exc.errors(include_input=False)}
        if "json_invalid" in codes:
            return "The assistant did not return complete valid JSON. Try a smaller proposal."
        return "The assistant returned fields that do not match the required proposal format."
    message = str(exc).lower()
    if "instruction quote needs" in message:
        return "The agent supplied an instruction quote too short to support review. Retry."
    if "instruction quote" in message:
        return "The proposal quotes an earlier revision request. Update its evidence and retry."
    if "trust evidence" in message:
        return (
            "Trust evidence differs from the reviewed producer settings. Regenerate the proposal."
        )
    if "citation" in message or "cite relevant input" in message:
        return (
            "The assistant's source quotations did not match the uploaded material exactly. "
            "Ask it to use short verbatim excerpts from the supplied sources."
        )
    if "property type" in message:
        return (
            "The assistant used an unsupported property type. "
            "Supported scalar types are text, string, int, float, bool, datetime and json. "
            "Lists use list<scalar>; enums use {enum: [values]}. "
            "Use int, float or bool rather than integer, number or boolean."
        )
    if "engine checks" in message:
        return (
            "The proposed pack did not pass engine checks after repair attempts. "
            "Review its contracts and mappings."
        )
    return "The proposal failed evidence or format validation after repair attempts."


def job_failure_reason(exc: Exception) -> str:
    # Do not log str(exc) or exc_info: either may embed prompts, URLs or credentials.
    name = type(exc).__name__.lower()
    if name == "slotunavailableerror":
        return (
            "No sandbox database is available. Wait for a run to finish "
            "or ask an operator to check pool capacity."
        )
    if name == "sandboxcleanuperror":
        return (
            "Sandbox cleanup could not be verified. The database is unavailable for reuse; "
            "ask an engineer to inspect it."
        )
    if isinstance(exc, AuthoringValidationError):
        return str(exc)
    if isinstance(exc, TimeoutError) or "timeout" in name:
        return (
            "The task exceeded its time limit. Your saved inputs are retained; "
            "retry or reduce the examples."
        )
    if "authentication" in name or "permission" in name:
        return (
            "The model provider refused access. "
            "Ask an engineer to check the configured provider credentials."
        )
    if "ratelimit" in name:
        return "The model provider is limiting requests. Wait before trying again."
    if "connection" in name:
        return "The model provider could not be reached. Check connectivity before retrying."
    if name == "journeyproposalerror" and "violates its payload contract" in str(exc):
        return (
            "A generated event does not match the pack contract and is not marked as a "
            "negative test at the correct event position. Ask the assistant to fix the "
            "event fields or the zero-based checkpoint, keeping the intended outcome."
        )
    if isinstance(exc, ValueError) and any(
        key in str(exc).lower() for key in ("instruction quote", "trust evidence")
    ):
        return proposal_failure_reason(exc)
    if isinstance(exc, (ValidationError, ValueError)):
        return (
            "The returned proposal did not meet the required format or pack checks. "
            "Review the inputs and retry; an engineer can inspect the validation path."
        )
    return (
        "The task stopped unexpectedly. Your saved inputs are retained; "
        "share the error reference with an engineer."
    )
