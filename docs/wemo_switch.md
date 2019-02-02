WeMoSwitch
===========
Actuate a WeMo Switch - turn it on or off. The first device discovered is used if no `device_mac` is specified.

NOTE: Devices may change their port numbers or otherwise need to be re-discovered on the network, which can take a minute, so during device discovery incoming signals are dropped. Signals will also be dropped if another thread is still waiting on results from the target device, which can take a while as the update retries (5 retries, not configurable). Discovery is threaded and begins after `configure`. If discovery fails for any reason, following calls to `process_signals` will restart the discovery process.

Properties
----------
- **device_mac**: Optinally specify the MAC address of the target WeMo.
- **Switch State**: A boolean of what to change the switch state
- **enrich**: Signal Enrichment
  - *exclude_existing*: If checked (true), the attributes of the incoming signal will be excluded from the outgoing signal. If unchecked (false), the attributes of the incoming signal will be included in the outgoing signal.
  - *enrich_field*: (hidden) The attribute on the signal to store the results from this block. If this is empty, the results will be merged onto the incoming signal. This is the default operation. Having this field allows a block to 'save' the results of an operation to a single field on an incoming signal and notify the enriched signal.

Inputs
------
- **default**: Any list of signals.

Outputs
-------
- **default**: The same list of signals, enriched with the current state of the switch

Commands
--------
- **rediscover**: Forget the current device (if applicable) and begin device discovery.

