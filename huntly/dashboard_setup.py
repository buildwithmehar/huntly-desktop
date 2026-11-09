"""Read and save the business, AI and mailbox choices made in the dashboard."""

import os
import re
import shutil
import tempfile
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from huntly.config import HuntlyConfig
from huntly.textio import read_user_text


class BusinessProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    company: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=1, max_length=254)
    product: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=3000)
    industries: str = Field(min_length=1, max_length=1500)
    titles: str = Field(min_length=1, max_length=1500)
    geography: str = Field(min_length=1, max_length=1500)
    postal_address: str = Field(default="", max_length=500)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value):
            raise ValueError("Enter a valid sender email address.")
        return value

    @field_validator("company", "product")
    @classmethod
    def real_name(cls, value):
        if value.casefold() in {"your company", "your product"}:
            raise ValueError("Enter your own business and offer names.")
        return value


def read_config(path: Path) -> dict:
    data = yaml.safe_load(read_user_text(path))
    if not isinstance(data, dict):
        raise ValueError("Huntly's configuration must contain settings.")
    return data


def profile_ready(config: HuntlyConfig) -> bool:
    return all(value.strip() for value in (
        config.persona.company, config.product.name, config.product.description,
    )) and config.persona.company != "Your Company" and config.product.name != "Your Product"


def profile_fields(config: HuntlyConfig) -> dict:
    if not profile_ready(config):
        return {}
    return {
        "name": config.persona.name,
        "company": config.persona.company,
        "email": config.persona.email,
        "product": config.product.name,
        "description": config.product.description,
        "industries": "\n".join(config.icp.industries),
        "titles": "\n".join(config.icp.titles),
        "geography": "\n".join(config.icp.geography),
        "postal_address": config.compliance.postal_address,
    }


def update_profile(data: dict, profile: BusinessProfile, *, template: bool) -> None:
    persona, product, icp = (data[key] for key in ("persona", "product", "icp"))
    if template:
        persona.update(linkedin="", role="")
        product.update(pricing="", key_benefits=[], objection_responses={}, offer={"goal": "get_reply"})
        icp.update(company_size="")
    persona.update(name=profile.name, company=profile.company, email=profile.email)
    product.update(name=profile.product, description=profile.description)
    for field in ("industries", "titles", "geography"):
        icp[field] = [line.strip() for line in getattr(profile, field).splitlines() if line.strip()]
    data.setdefault("compliance", {})["postal_address"] = profile.postal_address


def write_config(path: Path, data: dict) -> None:
    # Validate the whole document before changing the config the heartbeat reads.
    HuntlyConfig.model_validate(data)
    target = path.resolve()
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix=".huntly-", suffix=".yaml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=True)
            stream.flush()
            os.fsync(stream.fileno())
        if target.exists():
            shutil.copymode(target, temporary)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
