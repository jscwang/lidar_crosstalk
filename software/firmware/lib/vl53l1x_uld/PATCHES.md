# Vendored VL53L1X ULD driver

Source: SparkFun VL53L1X 4m Laser Distance Sensor library 1.2.12
(`src/st_src/`), which carries STMicroelectronics' VL53L1X ultra lite
driver as an Arduino class. ST's BSD-3-Clause licence is in
`LICENSE-ST.md` and in the file headers; SparkFun's wrapper (not vendored)
is MIT.

Only the ST class is used. The SparkFun wrapper class is not needed.

## Why it is vendored rather than used from the registry

In the upstream code `VL53L1_I2CWrite` always returns 0, and
`VL53L1_I2CRead` returns 0 even when the sensor NACKs or returns fewer
bytes than requested, leaving stale data in the caller's buffer. On a rig
whose purpose is measuring small changes in range noise, a silent bus
fault would look like data. The patch makes those faults visible.

## Changes (all marked `RIG PATCH`)

1. `VL53L1_I2CWrite` returns `VL53L1_ERROR_CONTROL_INTERFACE` when
   `endTransmission` fails or the Wire buffer did not accept every byte.
2. `VL53L1_I2CRead` returns `VL53L1_ERROR_CONTROL_INTERFACE` when the index
   write still fails after 5 attempts, or when `requestFrom` returns fewer
   bytes than requested. The retry loop itself is unchanged.
3. Added `rigBusErrors` / `rigLastBusError`, incremented on every failed
   transaction. Many ULD functions overwrite `status` with the result of
   the last write, so the counter is how callers detect an earlier failure.
4. Added public `RigReadBlock()` and `RigReadByte()`, thin wrappers over the
   protected `VL53L1_ReadMulti()` / `VL53L1_RdByte()`, so a whole result
   block is read in one transaction.
5. `RangeSensor.h` include path flattened (`st_src/` prefix removed).

No register values, tables or sequencing were changed.
