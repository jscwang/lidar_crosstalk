// TCA9548A I2C multiplexer (SparkFun Qwiic Mux).
// Author: Jessica
#pragma once

#include <Wire.h>

class Tca9548a {
public:
    Tca9548a(TwoWire &wire, uint8_t addr) : wire_(wire), addr_(addr) {}

    bool present();                        // ACKs its address
    // Enables exactly one channel (0..7) and reads the control register back.
    // Skips the bus write when that channel is already selected, unless force.
    bool select(uint8_t channel, bool force = false);
    bool disableAll();                     // no channel enabled
    bool readMask(uint8_t &mask);
    uint32_t errors() const { return errors_; }
    uint8_t address() const { return addr_; }
    void invalidate() { current_ = kUnknown; }

private:
    static constexpr int kUnknown = -1;
    bool writeMask(uint8_t mask);

    TwoWire &wire_;
    uint8_t addr_;
    int current_ = kUnknown;
    uint32_t errors_ = 0;
};
