// Author: Jessica
#include "uld_decode.h"

namespace rig {

uint8_t mapRangeStatus(uint8_t raw) {
    switch (raw & 0x1F) {
        case 9: return 0;     // range valid
        case 6: return 1;     // sigma fail
        case 4: return 2;     // signal fail
        case 8: return 3;     // below minimum range
        case 5: return 4;     // phase out of valid limits
        case 3: return 5;     // hardware fail
        case 19: return 6;    // valid, no wrap check
        case 7: return 7;     // wrapped target
        case 12: return 9;    // processing fail
        case 18: return 10;   // crosstalk signal fail
        case 22: return 11;   // interrupt error
        case 23: return 12;   // merged target
        case 13: return 13;   // too-low signal
        default: return 255;
    }
}

void decodeResultBlock(const uint8_t b[kResultBlockLen], Reading &out) {
    out.status = mapRangeStatus(b[0]);
    out.spads = b[3];
    out.ambientKcps = static_cast<uint32_t>((b[7] << 8) | b[8]) * 8u;
    out.stream = b[2];
    out.rangeMm = static_cast<uint16_t>((b[13] << 8) | b[14]);
    out.signalKcps = static_cast<uint32_t>((b[15] << 8) | b[16]) * 8u;
}

}  // namespace rig
