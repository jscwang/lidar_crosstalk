// Author: Jessica
#include "tof_channel.h"

#include <esp_timer.h>

#include "uld_decode.h"

namespace {
constexpr uint32_t kBootTimeoutMs = 100;
}

bool TofChannel::select() {
    return mux_.select(channel_);
}

// A ULD call succeeded only if it returned 0 and no I2C transaction inside it
// failed (the ULD often overwrites an early error with a later status).
bool TofChannel::ok(int status, uint32_t errorsBefore) {
    if (status == 0 && dev_.rigBusErrors == errorsBefore) return true;
    mux_.invalidate();   // re-select and verify the mux on the next access
    return false;
}

bool TofChannel::readModelId(uint16_t &id) {
    if (!select()) return false;
    uint32_t e = dev_.rigBusErrors;
    return ok(dev_.VL53L1X_GetSensorId(&id), e);
}

bool TofChannel::readBootState(uint8_t &state) {
    if (!select()) return false;
    uint32_t e = dev_.rigBusErrors;
    return ok(dev_.VL53L1X_BootState(&state), e);
}

bool TofChannel::readOpticalCentre(uint8_t &spad) {
    if (!select()) return false;
    uint32_t e = dev_.rigBusErrors;
    return ok(dev_.RigReadByte(VL53L1_ROI_CONFIG__MODE_ROI_CENTRE_SPAD, &spad), e);
}

bool TofChannel::init(const char *&why) {
    initialised_ = false;
    uint16_t id = 0;
    if (!readModelId(id)) { why = "no answer at 0x29"; return false; }
    if (id != 0xEACC) { why = "model id is not 0xEACC (not a VL53L1X)"; return false; }

    uint32_t e = dev_.rigBusErrors;
    if (!ok(dev_.VL53L1X_StopRanging(), e)) { why = "stop ranging failed"; return false; }
    if (!ok(dev_.VL53L1X_ClearInterrupt(), e)) { why = "clear interrupt failed"; return false; }

    uint8_t state = 0;
    uint32_t t0 = millis();
    while (true) {
        if (!readBootState(state)) { why = "boot state read failed"; return false; }
        if (state) break;
        if (millis() - t0 > kBootTimeoutMs) { why = "sensor did not report booted"; return false; }
        delay(2);
    }

    e = dev_.rigBusErrors;
    if (!ok(dev_.VL53L1X_SensorInit(), e)) { why = "ULD SensorInit failed"; return false; }
    // Active low: data-ready pulls the open-drain GPIO1 low (a fast, driven
    // edge) instead of releasing it to the 47k pull-up (a slow RC edge).
    e = dev_.rigBusErrors;
    if (!ok(dev_.VL53L1X_SetInterruptPolarity(0), e)) { why = "set interrupt polarity failed"; return false; }
    uint8_t pol = 1;
    e = dev_.rigBusErrors;
    if (!ok(dev_.VL53L1X_GetInterruptPolarity(&pol), e) || pol != 0) {
        why = "interrupt polarity did not read back as active low";
        return false;
    }
    if (!readOpticalCentre(opticalCentre_)) { why = "optical centre read failed"; return false; }
    initialised_ = true;
    return true;
}

bool TofChannel::apply(const rig::SensorSettings &s, const char *&why) {
    if (!select()) { why = "mux select failed"; return false; }
    uint32_t e = dev_.rigBusErrors;
    // Order matters in the ULD: the timing budget table depends on the mode,
    // and SetDistanceMode re-applies the current budget. Straight after
    // SensorInit that budget reads back as 0 (not in the ULD's table), so a
    // first SetDistanceMode returns an error. Preloading 33 ms, valid in both
    // modes, avoids it (found on the bench: the first CFG after boot failed).
    int st = dev_.VL53L1X_SetTimingBudgetInMs(33);
    st |= dev_.VL53L1X_SetDistanceMode(static_cast<uint16_t>(s.mode));
    st |= dev_.VL53L1X_SetTimingBudgetInMs(s.timingBudgetMs);
    st |= dev_.VL53L1X_SetInterMeasurementInMs(s.interMeasurementMs);
    // Centre the ROI on the factory-calibrated optical centre, as ST's own
    // ULD does; the ULD forces 199 for ROIs wider than 10.
    st |= dev_.VL53L1X_SetROI(s.roi, s.roi, opticalCentre_);
    bool busFault = dev_.rigBusErrors != e;
    if (!ok(st, e)) {
        why = busFault ? "I2C error while writing settings" : "driver rejected a setting";
        return false;
    }

    rig::SensorSettings back;
    if (!readBack(back)) { why = "I2C error while reading settings back"; return false; }
    if (back.mode != s.mode || back.timingBudgetMs != s.timingBudgetMs || back.roi != s.roi) {
        why = "settings did not read back as written";
        return false;
    }
    // The period register is in oscillator ticks; allow 1 ms for rounding.
    int d = static_cast<int>(back.interMeasurementMs) - static_cast<int>(s.interMeasurementMs);
    if (d < -1 || d > 1) { why = "inter-measurement period did not read back"; return false; }
    return true;
}

bool TofChannel::readBack(rig::SensorSettings &out) {
    if (!select()) return false;
    uint32_t e = dev_.rigBusErrors;
    uint16_t dm = 0, tb = 0, rx = 0, ry = 0;
    int st = dev_.VL53L1X_GetDistanceMode(&dm);
    st |= dev_.VL53L1X_GetTimingBudgetInMs(&tb);
    st |= dev_.VL53L1X_GetROI_XY(&rx, &ry);
    // The ULD's GetInterMeasurementInMs truncates the 32-bit period register
    // to 16 bits before scaling, so decode it here with full-width maths.
    uint8_t per[4] = {0}, osc[2] = {0};
    st |= dev_.RigReadBlock(VL53L1_SYSTEM__INTERMEASUREMENT_PERIOD, per, 4);
    st |= dev_.RigReadBlock(VL53L1_RESULT__OSC_CALIBRATE_VAL, osc, 2);
    if (!ok(st, e)) return false;

    uint32_t period = (uint32_t(per[0]) << 24) | (uint32_t(per[1]) << 16) | (uint32_t(per[2]) << 8) | per[3];
    uint32_t pll = ((uint32_t(osc[0]) << 8) | osc[1]) & 0x3FF;
    if (pll == 0 || rx != ry) return false;
    out.mode = dm == 1 ? rig::DistanceMode::Short : rig::DistanceMode::Long;
    out.timingBudgetMs = tb;
    out.roi = static_cast<uint8_t>(rx);
    out.interMeasurementMs = static_cast<uint16_t>((period / (pll * 1.075)) + 0.5);
    return dm == 1 || dm == 2;
}

bool TofChannel::readRaw(uint16_t addr, uint8_t *buf, size_t len) {
    if (!select()) return false;
    uint32_t e = dev_.rigBusErrors;
    return ok(dev_.RigReadBlock(addr, buf, len), e);
}

bool TofChannel::start() {
    if (!select()) return false;
    uint32_t e = dev_.rigBusErrors;
    int st = dev_.VL53L1X_ClearInterrupt();
    st |= dev_.VL53L1X_StartRanging();
    return ok(st, e);
}

bool TofChannel::stop() {
    if (!select()) return false;
    uint32_t e = dev_.rigBusErrors;
    return ok(dev_.VL53L1X_StopRanging(), e);
}

bool TofChannel::clearInterrupt() {
    if (!select()) return false;
    uint32_t e = dev_.rigBusErrors;
    return ok(dev_.VL53L1X_ClearInterrupt(), e);
}

bool TofChannel::readResult(rig::Reading &r) {
    if (!select()) return false;
    uint8_t block[rig::kResultBlockLen];
    uint32_t e = dev_.rigBusErrors;
    if (!ok(dev_.RigReadBlock(rig::kResultBlockStart, block, rig::kResultBlockLen), e)) return false;
    r.tReadUs = static_cast<uint64_t>(esp_timer_get_time());
    rig::decodeResultBlock(block, r);
    e = dev_.rigBusErrors;
    return ok(dev_.VL53L1X_ClearInterrupt(), e);
}
