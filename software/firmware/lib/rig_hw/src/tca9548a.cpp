// Author: Jessica
#include "tca9548a.h"

bool Tca9548a::present() {
    wire_.beginTransmission(addr_);
    return wire_.endTransmission() == 0;
}

bool Tca9548a::readMask(uint8_t &mask) {
    if (wire_.requestFrom(addr_, static_cast<uint8_t>(1)) != 1) {
        errors_++;
        return false;
    }
    mask = static_cast<uint8_t>(wire_.read());
    return true;
}

bool Tca9548a::writeMask(uint8_t mask) {
    wire_.beginTransmission(addr_);
    wire_.write(mask);
    if (wire_.endTransmission() != 0) {
        errors_++;
        current_ = kUnknown;
        return false;
    }
    uint8_t back = 0;
    if (!readMask(back) || back != mask) {
        // A mismatch means another master, a reset mux or a bad bus:
        // never guess which sensor is on the bus.
        if (back != mask) errors_++;
        current_ = kUnknown;
        return false;
    }
    return true;
}

bool Tca9548a::select(uint8_t channel, bool force) {
    if (channel > 7) return false;
    if (!force && current_ == channel) return true;
    if (!writeMask(static_cast<uint8_t>(1u << channel))) return false;
    current_ = channel;
    return true;
}

bool Tca9548a::disableAll() {
    if (!writeMask(0)) return false;
    current_ = kUnknown;
    return true;
}
