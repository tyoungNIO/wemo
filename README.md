WeMoInsight
===========
Read data from a WeMo Insight device. NOTE: The first device discovered is used.

Properties
----------
- **enrich**: Signal Enrichment
  - *exclude_existing*: If checked (true), the attributes of the incoming signal will be excluded from the outgoing signal. If unchecked (false), the attributes of the incoming signal will be included in the outgoing signal.
  - *enrich_field*: (hidden) The attribute on the signal to store the results from this block. If this is empty, the results will be merged onto the incoming signal. This is the default operation. Having this field allows a block to 'save' the results of an operation to a single field on an incoming signal and notify the enriched signal.

Inputs
------
- **default**: Any list of signals.

Outputs
-------
- **default**: The same list of signals, enriched with the device parameters.

Commands
--------
None

