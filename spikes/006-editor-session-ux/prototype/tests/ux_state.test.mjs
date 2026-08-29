import test from "node:test";
import assert from "node:assert/strict";

import * as uxState from "../ux_state.mjs";


test("comparison button invites showing comparison when no preview exists", () => {
  assert.equal(uxState.compareButtonLabel(false, true), "إظهار قبل / بعد");
});


test("comparison button describes the next action when preview exists", () => {
  assert.equal(uxState.compareButtonLabel(true, true), "إخفاء المقترح");
  assert.equal(uxState.compareButtonLabel(true, false), "إظهار قبل / بعد");
});


test("showing an SVG proposal removes the hidden attribute", () => {
  const attributes = new Set(["hidden"]);
  const svgGroup = {
    toggleAttribute(name, force) {
      if (force) attributes.add(name);
      else attributes.delete(name);
    },
  };

  assert.equal(typeof uxState.setElementHidden, "function");
  uxState.setElementHidden(svgGroup, false);

  assert.equal(attributes.has("hidden"), false);
});
