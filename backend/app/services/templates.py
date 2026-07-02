"""Legal form/letter templates.

Each template declares the fields the AI must collect. The architecture is
data-driven so new categories can be added without code changes elsewhere.
These are generic, publicly-available form structures — NOT legal advice.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FormField:
    key: str
    label: str
    required: bool = True


@dataclass(frozen=True)
class FormTemplate:
    id: str
    category: str
    title: str
    description: str
    fields: list[FormField] = field(default_factory=list)


def _f(key: str, label: str, required: bool = True) -> FormField:
    return FormField(key=key, label=label, required=required)


TEMPLATES: dict[str, FormTemplate] = {
    "employment_termination_response": FormTemplate(
        id="employment_termination_response",
        category="Employment",
        title="Response to Termination (factual letter)",
        description="A factual letter acknowledging a termination and requesting documents.",
        fields=[
            _f("full_name", "Your full name"),
            _f("employer_name", "Employer name"),
            _f("employment_start", "Employment start date"),
            _f("termination_date", "Termination date"),
            _f("contract_type", "Contract type"),
            _f("monthly_salary", "Monthly salary", required=False),
            _f("desired_outcome", "Desired outcome"),
        ],
    ),
    "immigration_general": FormTemplate(
        id="immigration_general",
        category="Immigration",
        title="Immigration matter intake",
        description="General intake for immigration / residence matters.",
        fields=[
            _f("full_name", "Your full name"),
            _f("nationality", "Nationality"),
            _f("current_status", "Current residence status"),
            _f("permit_type", "Permit/visa type"),
            _f("relevant_dates", "Relevant dates"),
            _f("desired_outcome", "Desired outcome"),
        ],
    ),
    "rental_defect_notice": FormTemplate(
        id="rental_defect_notice",
        category="Rental",
        title="Rental defect notice (Mängelanzeige)",
        description="Factual notice to a landlord describing a defect.",
        fields=[
            _f("tenant_name", "Tenant name"),
            _f("landlord_name", "Landlord name"),
            _f("property_address", "Property address"),
            _f("defect_description", "Description of the defect"),
            _f("defect_noticed_date", "Date defect was noticed"),
            _f("requested_remedy", "Requested remedy"),
        ],
    ),
    "consumer_complaint": FormTemplate(
        id="consumer_complaint",
        category="Consumer",
        title="Consumer complaint letter",
        description="Factual complaint about a product or service.",
        fields=[
            _f("full_name", "Your full name"),
            _f("company_name", "Company name"),
            _f("order_reference", "Order/invoice reference"),
            _f("purchase_date", "Purchase date"),
            _f("issue_description", "Description of the issue"),
            _f("requested_remedy", "Requested remedy"),
        ],
    ),
}

CATEGORIES = sorted({t.category for t in TEMPLATES.values()})


def get_template(template_id: str) -> FormTemplate | None:
    return TEMPLATES.get(template_id)


def templates_for_category(category: str) -> list[FormTemplate]:
    return [t for t in TEMPLATES.values() if t.category.lower() == category.lower()]
