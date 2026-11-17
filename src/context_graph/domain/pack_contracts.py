"""Bounded payload-contract prototype for packs; ingress wiring is a later slice.

Validation is strict and observational: it never supplies defaults, coerces source
identities, clears fields or returns a rewritten payload. Omission and explicit
null remain distinct for the projector's separately specified update policy.
"""

from __future__ import annotations

from types import GenericAlias
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictBool,
    StrictInt,
    StrictStr,
    create_model,
    field_validator,
    model_validator,
)

MAX_DEPTH = 16
MAX_FIELDS = 256


class PayloadField(BaseModel):
    """Deliberately small supported syntax; unknown keywords fail at pack load."""

    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["string", "integer", "number", "boolean", "object", "array"]
    required: bool = False
    nullable: bool = False
    properties: dict[str, PayloadField] = Field(default_factory=dict)
    items: PayloadField | None = None
    additional_fields: Literal["preserve", "forbid"] = "preserve"
    enum: list[str] | None = Field(default=None, min_length=1)
    minimum: int | float | None = Field(default=None, allow_inf_nan=False)
    maximum: int | float | None = Field(default=None, allow_inf_nan=False)
    min_length: int | None = Field(default=None, ge=0)
    max_length: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _shape(self) -> PayloadField:
        if self.enum is not None and self.type != "string":
            raise ValueError("enum is supported only for strings")
        if self.type not in {"integer", "number"} and (
            self.minimum is not None or self.maximum is not None
        ):
            raise ValueError("numeric bounds require integer or number")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")
        if self.type == "array" and self.items is None:
            raise ValueError("array requires an items declaration")
        if self.type != "array" and self.items is not None:
            raise ValueError("items is only supported for arrays")
        if self.type != "object" and (self.properties or self.additional_fields != "preserve"):
            raise ValueError("properties/additional_fields require an object")
        if self.type not in {"string", "array"} and (
            self.min_length is not None or self.max_length is not None
        ):
            raise ValueError("length constraints require string or array")
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            raise ValueError("min_length must not exceed max_length")
        return self


def _object_model(properties: dict[str, PayloadField], additional_fields: str) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for index, (name, spec) in enumerate(properties.items()):
        # Internal names avoid collisions with Pydantic methods and private fields;
        # source names remain aliases, including punctuation and model_* names.
        fields[f"field_{index}"] = (
            _field_type(spec),
            Field(default=... if spec.required else None, alias=name),
        )
    return create_model(
        "PackPayload",
        __config__=ConfigDict(
            strict=True,
            extra="allow" if additional_fields == "preserve" else "forbid",
            loc_by_alias=True,
        ),
        **fields,
    )


def _field_type(spec: PayloadField) -> Any:
    result: Any
    if spec.type == "object":
        result = _object_model(spec.properties, spec.additional_fields)
    elif spec.type == "array":
        assert spec.items is not None
        result = GenericAlias(list, _field_type(spec.items))
    else:
        result = {
            "string": StrictStr,
            "integer": StrictInt,
            "number": Annotated[FiniteFloat, Field(strict=True)],
            "boolean": StrictBool,
        }[spec.type]
    if spec.enum is not None:
        result = Literal[tuple(spec.enum)]
    if spec.minimum is not None or spec.maximum is not None:
        result = Annotated[result, Field(ge=spec.minimum, le=spec.maximum)]
    if spec.min_length is not None or spec.max_length is not None:
        result = Annotated[result, Field(min_length=spec.min_length, max_length=spec.max_length)]
    return result | None if spec.nullable else result


class PayloadContract(BaseModel):
    """Version1 prototype. No defaults, remote refs, regex or executable validators."""

    model_config = ConfigDict(extra="forbid", strict=True)

    version: Literal[1] = 1
    properties: dict[str, PayloadField] = Field(default_factory=dict)
    additional_fields: Literal["preserve", "forbid"] = "preserve"

    @field_validator("version", mode="before")
    @classmethod
    def _integer_version(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("contract version must be an integer")
        return value

    @model_validator(mode="after")
    def _bounded(self) -> PayloadContract:
        count = 0
        stack = [(spec, 1) for spec in self.properties.values()]
        while stack:
            spec, depth = stack.pop()
            count += 1
            if depth > MAX_DEPTH:
                raise ValueError(f"payload contract exceeds depth {MAX_DEPTH}")
            if count > MAX_FIELDS:
                raise ValueError(f"payload contract exceeds {MAX_FIELDS} field declarations")
            stack.extend((child, depth + 1) for child in spec.properties.values())
            if spec.items is not None:
                stack.append((spec.items, depth + 1))
        # Fail unsupported model/alias construction at declaration time.
        _object_model(self.properties, self.additional_fields)
        return self

    def declares_path(self, steps: tuple[str, ...]) -> bool:
        """Extra fields are preserved but cannot silently supply rule inputs."""
        properties = self.properties
        spec = None
        for step in steps:
            if step == "[*]":
                if spec is None or spec.type != "array" or spec.items is None:
                    return False
                spec = spec.items
            else:
                if spec is not None:
                    if spec.type != "object":
                        return False
                    properties = spec.properties
                spec = properties.get(step)
                if spec is None:
                    return False
        return spec is not None

    def validate_payload(self, payload: Any) -> None:
        """Raise structured Pydantic errors; caller must not expose input values."""
        self.compile_validator().model_validate(payload)

    def compile_validator(self) -> type[BaseModel]:
        """Compile once per pinned policy; validation must not rewrite the payload."""
        return _object_model(self.properties, self.additional_fields)
