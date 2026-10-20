// Hardware configuration of the two-sensor crosstalk rig.
// Source of truth: deliverables/Wiring diagram - two-sensor test setup.pdf
// Author: Jessica
#pragma once

#include <stdint.h>

namespace cfg {

constexpr const char *kFirmwareVersion = "1.0.2";

// Which module this build is for (set per environment in platformio.ini).
#ifndef RIG_BOARD
#define RIG_BOARD "unknown"
#endif
constexpr const char *kBoard = RIG_BOARD;

// USB-UART bridge on the port marked "UART" (UART0).
constexpr uint32_t kSerialBaud = 921600;

// I2C: ESP32-S3-DevKitC-1 J1 pin 12 (GPIO8) and pin 15 (GPIO9), via the
// Qwiic cable into the mux "Main" port.
constexpr int kPinSda = 8;
constexpr int kPinScl = 9;
// 400 kHz by default; a rig whose wiring is too slow for that (long jumpers,
// weak pull-ups) sets RIG_I2C_HZ in its platformio.ini environment.
#ifndef RIG_I2C_HZ
#define RIG_I2C_HZ 400000
#endif
constexpr uint32_t kI2cHz = RIG_I2C_HZ;
constexpr uint16_t kI2cTimeoutMs = 20;

// SparkFun Qwiic Mux BOB-16784 (TCA9548A), address jumpers open.
constexpr uint8_t kMuxAddr = 0x70;
// Mux channel of each sensor; a rig overrides them in platformio.ini if a
// channel is faulty (the local rig moved sensor A to channel 2).
#ifndef RIG_CH_A
#define RIG_CH_A 0
#endif
#ifndef RIG_CH_B
#define RIG_CH_B 1
#endif
constexpr uint8_t kMuxChannel[2] = {RIG_CH_A, RIG_CH_B};   // sensor A, sensor B

// Pololu 3415 VL53L1X carriers, factory address.
constexpr uint8_t kTofAddr7 = 0x29;
constexpr uint16_t kTofModelId = 0xEACC;

// Each sensor's GPIO1 straight to the ESP32, not through the mux.
// The carrier pulls GPIO1 up to its 2.8 V VDD (47k); GPIO1 is open drain.
#ifndef RIG_INT_B
#define RIG_INT_B 5
#endif
constexpr int kPinInt[2] = {4, RIG_INT_B};   // J1 pin 4 (A), J1 pin 5 (B) unless the build moves it

// Status lights for the person moving the target (optional). Each is an LED in series with about 330 ohm
// to GND: green on J1 pin 7 (GPIO7) lights when the setting is right, red on J1 pin 8 (GPIO15) when it is not.
// Both idle off. Nothing needs to be fitted for the rig to work.
#ifndef RIG_LED_OK
#define RIG_LED_OK 7
#endif
#ifndef RIG_LED_BAD
#define RIG_LED_BAD 15
#endif
constexpr int kPinLedOk = RIG_LED_OK;
constexpr int kPinLedBad = RIG_LED_BAD;

// Default ranging settings from the procedure; the host sends CFG anyway.
constexpr uint8_t kDefaultRoi = 16;
constexpr uint16_t kDefaultTimingBudgetMs = 33;
constexpr uint16_t kDefaultInterMeasurementMs = 40;

}  // namespace cfg
