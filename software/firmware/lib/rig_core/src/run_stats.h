// Per-sensor statistics over a short run, used by the firmware self-test to
// decide whether the interrupt timing looks healthy.
//
// Missed readings are found from gaps in the interrupt timestamps. The
// VL53L1X's RESULT__STREAM_COUNT cannot be used: on the bench it stays at 1
// in the ULD's timed ranging mode.
// Author: Jessica
#pragma once

#include "rig_types.h"

namespace rig {

struct RunStats {
    uint32_t n = 0;
    uint32_t valid = 0;              // range status 0
    double meanPeriodMs = 0;         // between consecutive interrupt edges
    double maxPeriodMs = 0;
    uint16_t medianRangeMm = 0;      // of up to the first kMedianCap readings
};

class RunStatsAccumulator {
public:
    static constexpr size_t kMedianCap = 64;
    void add(const Reading &r);
    RunStats result() const;

private:
    RunStats s_;
    uint64_t firstUs_ = 0, lastUs_ = 0;
    uint16_t ranges_[kMedianCap] = {0};
    size_t nRanges_ = 0;
};

// Checks a run's timing against the configured settings. Expected readings in
// a run of `durMs`: the first after about one timing budget, then one per
// inter-measurement period. Returns nullptr when healthy, else the problem.
const char *checkTiming(const RunStats &s, uint32_t durMs, uint16_t tbMs, uint16_t impMs);

}  // namespace rig
