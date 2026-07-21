# core-a01 internal

The public workflow is the employee ticket platform. The intended defect is missing
object ownership validation in `GET /api/tickets/<ticket_no>`.

The foreign ticket number is discoverable from a service announcement, while the
diagnostic report is a random per-instance capability URL returned only after the
foreign ticket detail is accessed. The report contains the dynamic instance flag.
