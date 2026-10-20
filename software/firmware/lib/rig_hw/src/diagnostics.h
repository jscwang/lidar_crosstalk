// Bus scan and hardware self-test. Output lines are defined in PROTOCOL.md.
// Author: Jessica
#pragma once

#include <Print.h>
#include <Wire.h>

#include "hw_bank.h"
#include "run_controller.h"

class Diagnostics {
public:
    Diagnostics(TwoWire &wire, Tca9548a &mux, HwSensorBank &bank, IntCapture &ints, rig::Clock &clock, Print &out)
        : wire_(wire), mux_(mux), bank_(bank), ints_(ints), clock_(clock), out_(out) {}

    // "SCAN bus=main addrs=70" then one "SCAN ch=<n> addrs=..." per channel.
    void scan();

    // Runs every check, printing one TEST line each. Returns the number of
    // failed checks. `settings` must already be applied to both sensors.
    int selfTest(const rig::SensorSettings &settings);

private:
    void scanInto(char *list, size_t len, uint8_t skip);   // skip = 0: none
    void report(const char *name, bool pass, const char *detail);
    void info(const char *name, const char *detail);

    TwoWire &wire_;
    Tca9548a &mux_;
    HwSensorBank &bank_;
    IntCapture &ints_;
    rig::Clock &clock_;
    Print &out_;
    int failures_ = 0;
};
