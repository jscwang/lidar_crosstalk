// Author: Jessica
#include "hw_bank.h"

#include <Arduino.h>
#include <esp_timer.h>

uint64_t ArduinoClock::nowUs() const { return static_cast<uint64_t>(esp_timer_get_time()); }

void ArduinoClock::delayMs(uint32_t ms) { delay(ms); }
