// One VL53L1X on one TCA9548A channel.
// Author: Jessica
#pragma once

#include <Wire.h>

#include "rig_types.h"
#include "tca9548a.h"
#include "vl53l1x_class.h"

class TofChannel {
public:
    TofChannel(TwoWire &wire, Tca9548a &mux, uint8_t muxChannel)
        : dev_(&wire, -1, -1), mux_(mux), channel_(muxChannel) {}

    // Brings the sensor to a known state: stops ranging left over from before
    // an MCU reset (XSHUT is not wired, so the sensor is never power cycled),
    // waits for boot, runs the ULD SensorInit and sets GPIO1 active low.
    // On failure `why` names the step.
    bool init(const char *&why);

    bool readModelId(uint16_t &id);
    bool readBootState(uint8_t &state);
    bool readOpticalCentre(uint8_t &spad);
    // Raw register read for diagnostics (the REG command). Does not change any setting.
    bool readRaw(uint16_t addr, uint8_t *buf, size_t len);

    // Writes the settings (sensor must be stopped) and reads every one back.
    bool apply(const rig::SensorSettings &s, const char *&why);
    bool readBack(rig::SensorSettings &out);

    bool start();
    bool stop();
    bool clearInterrupt();
    bool readResult(rig::Reading &r);   // fills measurement fields and tReadUs

    uint32_t busErrors() const { return dev_.rigBusErrors; }
    bool initialised() const { return initialised_; }
    // Forces a full init on next use. A sensor that lost power keeps answering
    // at 0x29 but has forgotten the ULD configuration, so CFG re-inits.
    void invalidate() { initialised_ = false; }
    uint8_t opticalCentre() const { return opticalCentre_; }
    uint8_t muxChannel() const { return channel_; }

private:
    bool select();
    bool ok(int status, uint32_t errorsBefore);

    VL53L1X dev_;
    Tca9548a &mux_;
    uint8_t channel_;
    bool initialised_ = false;
    uint8_t opticalCentre_ = 199;
};
