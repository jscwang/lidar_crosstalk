// Decoding of the VL53L1X result register block.
// Author: Jessica
//
// The firmware reads 17 bytes starting at RESULT__RANGE_STATUS (0x0089) in
// one I2C transaction. Offsets and scaling match the ST ULD accessors
// (VL53L1X_GetRangeStatus, _GetSpadNb, _GetAmbientRate, _GetDistance,
// _GetSignalRate) in the vendored driver:
//
//   offset  register                                           decode
//    0      0x0089 RESULT__RANGE_STATUS                         & 0x1F, then ST table
//    2      0x008B RESULT__STREAM_COUNT                          raw
//    3      0x008C RESULT__DSS_ACTUAL_EFFECTIVE_SPADS_SD0 (hi)  SPAD count
//    7..8   0x0090 RESULT__AMBIENT_COUNT_RATE_MCPS_SD            x 8 = kcps
//   11..12 0x0094 RESULT__PHASE_SD0                              (not used)
//   13..14  0x0096 RESULT__FINAL_CROSSTALK_CORRECTED_RANGE_MM_SD0 mm
//   15..16  0x0098 RESULT__PEAK_SIGNAL_COUNT_RATE_..._MCPS_SD0    x 8 = kcps
#pragma once

#include "rig_types.h"

namespace rig {

constexpr uint16_t kResultBlockStart = 0x0089;
constexpr uint8_t kResultBlockLen = 17;

// Raw hardware status (low 5 bits) to ULD status, as in the driver's
// VL53L1X_GetRangeStatus(). 255 = unknown code.
uint8_t mapRangeStatus(uint8_t raw);

// Fills the measurement fields of `out` (not sensor or timestamps).
void decodeResultBlock(const uint8_t block[kResultBlockLen], Reading &out);

}  // namespace rig
