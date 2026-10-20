// Shared types for the two-sensor crosstalk rig.
// Pure C++ (no Arduino headers) so the logic can be unit tested on a PC.
// Author: Jessica
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace rig {

constexpr uint8_t kNumSensors = 2;   // A = 0 (mux ch 0), B = 1 (mux ch 1)
constexpr uint8_t kSensorA = 0;
constexpr uint8_t kSensorB = 1;

inline char sensorName(uint8_t s) { return s == kSensorA ? 'A' : 'B'; }

enum class DistanceMode : uint8_t { Short = 1, Long = 2 };   // ULD encoding

// Settings applied identically to both sensors.
struct SensorSettings {
    uint8_t roi = 16;                        // ROI width = height in SPADs, 4..16
    uint16_t timingBudgetMs = 33;
    uint16_t interMeasurementMs = 40;
    DistanceMode mode = DistanceMode::Short;
};

// Which sensors range during a run.
enum class Condition : uint8_t { ASolo, BSolo, Both };

inline bool participates(Condition c, uint8_t sensor) {
    if (c == Condition::Both) return true;
    return (c == Condition::ASolo) == (sensor == kSensorA);
}

const char *conditionName(Condition c);   // "A", "B", "AB"

// One decoded ranging result.
struct Reading {
    uint8_t sensor = 0;
    uint64_t tIntUs = 0;        // GPIO1 edge, captured in the ISR
    uint64_t tReadUs = 0;       // when the I2C read of the result finished
    uint16_t rangeMm = 0;
    uint8_t status = 255;       // ULD range status, 0 = valid
    // Rates are 32-bit: the register is 16-bit and x8 overflows 16 bits above
    // about 64 Mcps, where the ULD's own uint16_t accessors would wrap.
    uint32_t signalKcps = 0;    // total peak signal rate, all SPADs
    uint32_t ambientKcps = 0;   // total ambient rate, all SPADs
    uint8_t spads = 0;          // effective SPADs used
    uint8_t stream = 0;         // RESULT__STREAM_COUNT, for missed-frame detection
};

constexpr size_t kRunIdMax = 24;

}  // namespace rig
