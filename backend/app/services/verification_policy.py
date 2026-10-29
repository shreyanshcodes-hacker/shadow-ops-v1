from typing import List, Dict, Any, Tuple
from app.schemas.verification import (
    VerificationPolicyVerdict,
    VulnerabilityVerificationStatus,
    ScannerVerificationStatus,
    RegressionCheckStatus,
)


class VerificationPolicyEngine:
    """
    Deterministic Verification Policy Engine (verification-policy-v1).
    Enforces the core rule:
    'No sufficient evidence means no verified fix.'
    """

    POLICY_VERSION = "verification-policy-v1"

    @classmethod
    def evaluate(
        cls,
        vulnerability_status: str,
        scanner_status: str,
        regression_checks: List[Dict[str, Any]],
        test_status: str = "PASS",
    ) -> Tuple[str, List[str], str]:
        """
        Evaluates verification evidence according to verification-policy-v1.

        Returns:
            verdict: VerificationPolicyVerdict string
            reasons: list of detailed explanation strings
            overall_regression_status: 'PASS', 'FAIL', 'BLOCKED', or 'SKIPPED'
        """
        reasons = []

        # 1. Evaluate regression check results
        has_failed_check = False
        has_blocked_check = False
        all_passed = True

        for check in regression_checks:
            c_status = check.get("status")
            c_name = check.get("check_name", "unknown")
            if c_status in (RegressionCheckStatus.FAIL.value, RegressionCheckStatus.ERROR.value):
                has_failed_check = True
                all_passed = False
                reasons.append(f"Regression check '{c_name}' failed: {check.get('output_summary')}")
            elif c_status == RegressionCheckStatus.BLOCKED.value:
                has_blocked_check = True
                all_passed = False
                reasons.append(f"Regression check '{c_name}' was BLOCKED: {check.get('output_summary')}")
            elif c_status != RegressionCheckStatus.PASS.value:
                all_passed = False

        if has_blocked_check:
            overall_regression_status = RegressionCheckStatus.BLOCKED.value
        elif has_failed_check:
            overall_regression_status = RegressionCheckStatus.FAIL.value
        elif all_passed:
            overall_regression_status = RegressionCheckStatus.PASS.value
        else:
            overall_regression_status = RegressionCheckStatus.SKIPPED.value

        # 2. Scanner completion invariant
        if scanner_status != ScannerVerificationStatus.COMPLETED.value:
            reasons.append(f"Scanner did not complete successfully (status: {scanner_status}).")
            if scanner_status in (ScannerVerificationStatus.BLOCKED.value, ScannerVerificationStatus.SCANNER_UNAVAILABLE.value):
                return (VerificationPolicyVerdict.BLOCKED.value, reasons, overall_regression_status)
            return (VerificationPolicyVerdict.FAILED.value, reasons, overall_regression_status)

        # 3. Regression blocking or failure
        if has_blocked_check:
            return (VerificationPolicyVerdict.BLOCKED.value, reasons, overall_regression_status)

        if has_failed_check:
            return (VerificationPolicyVerdict.FAILED.value, reasons, overall_regression_status)

        # 4. Vulnerability status check
        if vulnerability_status == VulnerabilityVerificationStatus.STILL_PRESENT.value:
            reasons.append("Vulnerability is still present in post-patch scan.")
            return (VerificationPolicyVerdict.FAILED.value, reasons, overall_regression_status)

        if vulnerability_status == VulnerabilityVerificationStatus.MODIFIED_OR_MOVED.value:
            reasons.append("Vulnerability was shifted or altered in location, not eliminated.")
            return (VerificationPolicyVerdict.FAILED.value, reasons, overall_regression_status)

        if vulnerability_status in (
            VulnerabilityVerificationStatus.POSSIBLE_REGRESSION.value,
            VulnerabilityVerificationStatus.NEW_FINDING.value,
        ):
            reasons.append("Post-patch scan detected newly introduced security flaws.")
            return (VerificationPolicyVerdict.FAILED.value, reasons, overall_regression_status)

        if vulnerability_status == VulnerabilityVerificationStatus.UNCOMPARABLE.value:
            reasons.append("Insufficient evidence to reliably compare baseline with rescan.")
            return (VerificationPolicyVerdict.INCONCLUSIVE.value, reasons, overall_regression_status)

        # 5. Clean verification candidate condition
        if (
            vulnerability_status == VulnerabilityVerificationStatus.NO_LONGER_DETECTED.value
            and overall_regression_status in (RegressionCheckStatus.PASS.value, RegressionCheckStatus.SKIPPED.value)
            and test_status in (RegressionCheckStatus.PASS.value, RegressionCheckStatus.SKIPPED.value)
        ):
            reasons.append(
                "Independent rescan confirmed target vulnerability is no longer detected, with no syntax or regression errors."
            )
            return (VerificationPolicyVerdict.VERIFIED_CANDIDATE.value, reasons, overall_regression_status)

        # Fallback
        reasons.append("Verification criteria were not completely satisfied.")
        return (VerificationPolicyVerdict.INCONCLUSIVE.value, reasons, overall_regression_status)
