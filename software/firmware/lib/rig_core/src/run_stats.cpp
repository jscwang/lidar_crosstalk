// Author: Jessica
#include "run_stats.h"

#include <string.h>

namespace rig {

void RunStatsAccumulator::add(const Reading &r) {
    if (s_.n == 0) {
        firstUs_ = r.tIntUs;
    } else {
        double p = static_cast<double>(r.tIntUs - lastUs_) / 1000.0;
        if (p > s_.maxPeriodMs) s_.maxPeriodMs = p;
    }
    lastUs_ = r.tIntUs;
    s_.n++;
    if (r.status == 0) s_.valid++;
    if (nRanges_ < kMedianCap) ranges_[nRanges_++] = r.rangeMm;
}

RunStats RunStatsAccumulator::result() const {
    RunStats out = s_;
    if (s_.n > 1) out.meanPeriodMs = static_cast<double>(lastUs_ - firstUs_) / 1000.0 / (s_.n - 1);
    if (nRanges_) {
        uint16_t v[kMedianCap];
        memcpy(v, ranges_, nRanges_ * sizeof(uint16_t));
        for (size_t i = 1; i < nRanges_; ++i)   // insertion sort, n <= 64
            for (size_t j = i; j > 0 && v[j - 1] > v[j]; --j) {
                uint16_t t = v[j];
                v[j] = v[j - 1];
                v[j - 1] = t;
            }
        out.medianRangeMm = v[nRanges_ / 2];
    }
    return out;
}

const char *checkTiming(const RunStats &s, uint32_t durMs, uint16_t tbMs, uint16_t impMs) {
    if (durMs <= tbMs) return "run shorter than one timing budget";
    uint32_t expected = (durMs - tbMs) / impMs + 1;
    uint32_t tol = expected / 10 > 2 ? expected / 10 : 2;
    if (s.n + tol < expected) return "too few readings";
    if (s.n > expected + tol) return "too many readings";
    if (s.n > 1) {
        double lo = impMs * 0.9, hi = impMs * 1.1;
        if (s.meanPeriodMs < lo || s.meanPeriodMs > hi) return "mean period more than 10% off imp";
        if (s.maxPeriodMs > impMs * 1.9) return "a reading was missed (gap near 2 x imp)";
    }
    return nullptr;
}

}  // namespace rig
