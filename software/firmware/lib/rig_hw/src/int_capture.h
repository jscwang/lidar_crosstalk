// GPIO1 data-ready interrupts from both sensors, timestamped in the ISR (both edges, counted when the pin reads low).
// Author: Jessica
#pragma once

#include <stdint.h>

#include "run_controller.h"

class IntCapture : public rig::EdgeSource {
public:
    // Pins are inputs without internal pull-ups: each Pololu carrier already
    // pulls its GPIO1 up to its own 2.8 V rail, and an ESP32 pull-up to
    // 3.3 V would back-feed that rail.
    void begin(const int pins[rig::kNumSensors]);

    bool takeEdge(uint8_t s, uint64_t &tUs) override;
    uint32_t edgeCount(uint8_t s) const override;
    uint32_t overrunCount(uint8_t s) const override;
    void reset() override;

    int level(uint8_t s) const;   // current pin level, for idle checks
    int pin(uint8_t s) const { return pins_[s]; }

    // Diagnostic trace (the TRACE command): records every edge of one pin, rising and falling, with the pin
    // level and a microsecond timestamp, so the waveform of a data-ready line can be seen as the chip drives it.
    // The normal capture is detached while tracing and restored by endTrace().
    static constexpr int kTraceMax = 256;
    // With `alsoCapture` the pin still feeds the normal capture on every low level, so a real run can be started
    // while the pin's waveform is recorded: the line and the run's own interrupt timestamps can then be compared.
    void beginTrace(uint8_t s, bool alsoCapture = false);
    void endTrace();
    int traceCount() const;
    bool traceAt(int i, int &level, uint64_t &tUs) const;
    bool traceOverflowed() const;

private:
    int pins_[rig::kNumSensors] = {-1, -1};
};
