"""Specialty-regimen overlay that adds FHIR R4B resources (MedicationRequest,
MedicationAdministration, Medication, CarePlan) to a Synthea-generated patient bundle.

Tier assignment is deterministic from the patient id. No real drug names;
only plausible class-level descriptors.
"""
