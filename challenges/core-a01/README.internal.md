# core-a01 internal

The public workflow is deliberately discoverable from `/`, `/me`, and `/workspace`.
The security defect is missing object ownership validation on the profile detail endpoint.
Tests must obtain the dynamic flag through the workflow and never hard-code it.
