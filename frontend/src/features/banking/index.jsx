// Banking feature — placeholder module for WO-F1.
//
// The existing "Banking, borrowing & expectations" editor group
// (banking_allowed, borrowing_allowed, borrowing_limit, expectation_rule,
// manual_expected_price, eua_price) is not called out in the WO-F1
// extraction map and stays core/unmoved (those fields also feed the
// expectations kernel and CBAM gap calculation, not just banking). This
// feature module is registered now so the registry-literal composition
// order is stable ahead of WO-F2 (result-side fragments), where banking's
// solver/result surface will populate these slots.

export default {
  id: "banking",
};
