/**
 * @file qemu_selftest.h
 * @brief QEMU-only self-test battery (built only with PROMOBEACON_QEMU=1)
 */
#ifndef QEMU_SELFTEST_H
#define QEMU_SELFTEST_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Run the full QEMU self-test battery.
 *
 * Exercises config manager, client tracker, portal content, status
 * collector and OTA subsystem logic paths with assertions. Results are
 * logged; the summary line is "SELFTEST RESULT: <pass> passed, <fail> failed".
 */
void qemu_selftest_run(void);

#ifdef __cplusplus
}
#endif

#endif /* QEMU_SELFTEST_H */
