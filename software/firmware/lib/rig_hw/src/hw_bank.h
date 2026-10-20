// Real-hardware implementations of the run controller's interfaces.
// Author: Jessica
#pragma once

#include "int_capture.h"
#include "run_controller.h"
#include "tof_channel.h"

class HwSensorBank : public rig::SensorBank {
public:
    HwSensorBank(TofChannel &a, TofChannel &b, IntCapture &ints, Tca9548a &mux)
        : tof_{&a, &b}, ints_(ints), mux_(mux) {}

    bool stopRanging(uint8_t s) override { return tof_[s]->stop() && tof_[s]->clearInterrupt(); }
    bool clearInterrupt(uint8_t s) override { return tof_[s]->clearInterrupt(); }
    bool startRanging(uint8_t s) override { return tof_[s]->start(); }
    bool readResult(uint8_t s, rig::Reading &r) override { return tof_[s]->readResult(r); }
    bool interruptIdle(uint8_t s) override { return ints_.level(s) == 1; }   // active low
    uint32_t busErrorCount() const override {
        return tof_[0]->busErrors() + tof_[1]->busErrors() + mux_.errors();
    }

    TofChannel &tof(uint8_t s) { return *tof_[s]; }

private:
    TofChannel *tof_[rig::kNumSensors];
    IntCapture &ints_;
    Tca9548a &mux_;
};

class ArduinoClock : public rig::Clock {
public:
    uint64_t nowUs() const override;
    void delayMs(uint32_t ms) override;
};
