import { compareButtonLabel, setElementHidden } from "./ux_state.mjs";

"use strict";

const initialPlan = Object.freeze({ wallOffsetMm: 0, windowShiftMm: 0 });
const session = {
  current: { ...initialPlan },
  preview: null,
  previewLabel: "",
  previewDiffs: [],
  previewStale: false,
  selection: [],
  confidence: 0.96,
  history: [],
  redo: [],
  interactions: 0,
  compare: true,
};

const byId = (id) => document.getElementById(id);
const ui = {
  breadcrumb: byId("breadcrumb"),
  selectionHelp: byId("selectionHelp"),
  wallOffset: byId("wallOffset"),
  numericError: byId("numericError"),
  previewPanel: byId("previewPanel"),
  previewStateBadge: byId("previewStateBadge"),
  previewWarning: byId("previewWarning"),
  diffList: byId("diffList"),
  approveBtn: byId("approveBtn"),
  discardPreviewBtn: byId("discardPreviewBtn"),
  compareBtn: byId("compareBtn"),
  confidenceBtn: byId("confidenceBtn"),
  globalMessage: byId("globalMessage"),
  clarificationBox: byId("clarificationBox"),
  clarificationQuestion: byId("clarificationQuestion"),
  clarificationOptions: byId("clarificationOptions"),
  aiPrompt: byId("aiPrompt"),
  undoBtn: byId("undoBtn"),
  redoBtn: byId("redoBtn"),
  historyStatus: byId("historyStatus"),
  interactionStatus: byId("interactionStatus"),
  revisionLabel: byId("revisionLabel"),
  viewMode: byId("viewMode"),
  canvasWrap: byId("canvasWrap"),
  canvasBadge: byId("canvasBadge"),
  proposalLayer: byId("proposalLayer"),
  currentWall: byId("currentWall"),
  proposalWall: byId("proposalWall"),
  currentWindow: byId("currentWindow"),
  proposalWindow: byId("proposalWindow"),
  movementArrow: byId("movementArrow"),
  leftRoomLabel: byId("leftRoomLabel"),
  rightRoomLabel: byId("rightRoomLabel"),
  plannerDialog: byId("plannerDialog"),
};

function clonePlan(plan) {
  return { wallOffsetMm: plan.wallOffsetMm, windowShiftMm: plan.windowShiftMm };
}

function normalizeNumber(value) {
  const arabic = "٠١٢٣٤٥٦٧٨٩";
  const eastern = "۰۱۲۳۴۵۶۷۸۹";
  return String(value)
    .replace(/[٠-٩]/g, (digit) => arabic.indexOf(digit))
    .replace(/[۰-۹]/g, (digit) => eastern.indexOf(digit))
    .replace(",", ".")
    .trim();
}

function wallX(plan) {
  return 500 + plan.wallOffsetMm / 10;
}

function windowCoordinates(plan) {
  const shift = plan.windowShiftMm / 10;
  return [230 + shift, 350 + shift];
}

function areas(plan) {
  const delta = (plan.wallOffsetMm / 1000) * 3;
  return [12 + delta, 12 - delta];
}

function setMessage(text, kind = "info") {
  ui.globalMessage.textContent = text;
  ui.globalMessage.className = `inline-message ${kind}`;
}

function incrementInteraction() {
  session.interactions += 1;
}

function selectElement(kind, id, label) {
  if (kind === "room") {
    session.selection = [{ kind, id, label }];
  } else if (kind === "wall") {
    if (!session.selection.some((item) => item.kind === "room")) {
      setMessage("اختر الغرفة أولاً حتى نوضح الجهة التي ستتأثر.", "warning");
      return;
    }
    session.selection = session.selection.filter((item) => item.kind === "room");
    session.selection.push({ kind, id, label });
  } else {
    if (!session.selection.some((item) => item.kind === "wall")) {
      setMessage("اختر الغرفة ثم الجدار قبل تحديد الباب أو النافذة.", "warning");
      return;
    }
    session.selection = session.selection.filter((item) => item.kind !== "opening");
    session.selection.push({ kind, id, label });
  }
  incrementInteraction();
  setMessage(`العنصر النشط: ${label}. يمكنك الآن إنشاء معاينة.`);
  render();
}

function stagePreview(nextPlan, label, diffs) {
  session.preview = clonePlan(nextPlan);
  session.previewLabel = label;
  session.previewDiffs = [...diffs];
  session.previewStale = false;
  session.compare = true;
  ui.clarificationBox.hidden = true;
  incrementInteraction();
  setMessage("تم إنشاء المعاينة. النسخة المعتمدة لم تتغير.");
  render();
}

function markPreviewStale() {
  if (!session.preview) return;
  session.previewStale = true;
  setMessage("غيّرت القيمة بعد إنشاء المعاينة. حدّث المعاينة قبل الاعتماد.", "warning");
  render();
}

function createNumericPreview() {
  const parsed = Number(normalizeNumber(ui.wallOffset.value));
  if (!Number.isFinite(parsed) || parsed < -150 || parsed > 150) {
    const suggested = Number.isFinite(parsed) ? Math.max(-150, Math.min(150, parsed)) : 50;
    ui.numericError.hidden = false;
    ui.numericError.innerHTML = `القيمة غير مسموحة. اكتب رقماً من −150 إلى 150 سم. <button type="button" id="useSuggestion">استخدم ${suggested} سم</button>`;
    byId("useSuggestion").addEventListener("click", () => {
      ui.wallOffset.value = suggested;
      ui.numericError.hidden = true;
      markPreviewStale();
    });
    setMessage("راجع مقدار الحركة؛ لم نغيّر الرقم الذي كتبته.", "warning");
    return;
  }
  if (!session.selection.some((item) => item.kind === "wall")) {
    setMessage("اختر الغرفة ثم الجدار قبل إدخال مقدار الحركة.", "warning");
    return;
  }
  ui.numericError.hidden = true;
  const offsetMm = Math.round(parsed * 10);
  const next = clonePlan(session.current);
  next.wallOffsetMm += offsetMm;
  const [beforeLeft, beforeRight] = areas(session.current);
  const [afterLeft, afterRight] = areas(next);
  stagePreview(next, `تحريك الجدار ${Math.abs(parsed)} سم`, [
    `الجدار المشترك: ${parsed > 0 ? "نحو غرفة النوم" : "نحو غرفة المعيشة"} بمقدار ${Math.abs(parsed)} سم`,
    `غرفة المعيشة: ${beforeLeft.toFixed(1)} ← ${afterLeft.toFixed(1)} م²`,
    `غرفة النوم: ${beforeRight.toFixed(1)} ← ${afterRight.toFixed(1)} م²`,
  ]);
}

function askClarification(question, options) {
  session.preview = null;
  ui.clarificationQuestion.textContent = question;
  ui.clarificationOptions.replaceChildren();
  options.forEach((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = option.label;
    button.addEventListener("click", option.action);
    ui.clarificationOptions.appendChild(button);
  });
  ui.clarificationBox.hidden = false;
  incrementInteraction();
  setMessage("نحتاج إجابة واحدة قبل إنشاء التغيير.", "warning");
  render();
}

function stageWindowMove(direction) {
  const next = clonePlan(session.current);
  const movement = direction === "A" ? -200 : 200;
  next.windowShiftMm += movement;
  stagePreview(next, "تحريك النافذة 20 سم", [
    `النافذة: تحريك 20 سم نحو الطرف ${direction === "A" ? "أ" : "ب"}`,
    "الجدار والغرف: لا تغيير في المساحة",
  ]);
}

function handlePrompt() {
  const prompt = ui.aiPrompt.value.trim();
  if (!prompt) {
    setMessage("اكتب طلباً قصيراً أولاً.", "warning");
    return;
  }
  const mentionsWindow = /نافذ/.test(prompt);
  const ambiguousDirection = /(يمين|يسار|للداخل|للخارج)/.test(prompt) && !/الطرف\s*[أابب]/.test(prompt);
  if (mentionsWindow && ambiguousDirection) {
    askClarification("إلى أي طرف تريد تحريك النافذة؟", [
      { label: "الطرف أ", action: () => stageWindowMove("A") },
      { label: "الطرف ب", action: () => stageWindowMove("B") },
    ]);
    return;
  }
  if (mentionsWindow) {
    const direction = /الطرف\s*ب/.test(prompt) ? "B" : "A";
    stageWindowMove(direction);
    return;
  }
  if (!session.selection.some((item) => item.kind === "wall")) {
    setMessage("حدد الجدار المقصود على المخطط قبل تفسير الطلب.", "warning");
    return;
  }
  const next = clonePlan(session.current);
  next.wallOffsetMm += 500;
  stagePreview(next, "طلب نصي: تحريك الجدار 50 سم", [
    "فهمنا الطلب: الجدار المشترك، 50 سم، نحو غرفة النوم",
    "راجع الاتجاه والقيمة قبل الاعتماد",
  ]);
}

function approvePreview() {
  if (!session.preview) return;
  if (session.previewStale) {
    setMessage("المعاينة قديمة. اضغط تحديث المعاينة أولاً.", "warning");
    return;
  }
  if (session.confidence < 0.8) {
    setMessage("يجب معايرة المقياس قبل اعتماد تعديل متري.", "warning");
    return;
  }
  const entry = {
    before: clonePlan(session.current),
    after: clonePlan(session.preview),
    label: session.previewLabel,
  };
  session.current = clonePlan(session.preview);
  session.history.push(entry);
  session.redo = [];
  session.preview = null;
  session.previewDiffs = [];
  session.previewLabel = "";
  incrementInteraction();
  setMessage(`تم اعتماد: ${entry.label}. يمكنك التراجع فوراً.`);
  render();
}

function discardPreview() {
  session.preview = null;
  session.previewDiffs = [];
  session.previewLabel = "";
  session.previewStale = false;
  setMessage("ألغينا المعاينة. النسخة المعتمدة لم تتغير.");
  render();
}

function undo() {
  if (!session.history.length) return;
  const entry = session.history.pop();
  session.current = clonePlan(entry.before);
  session.redo.push(entry);
  discardPreview();
  setMessage(`تم التراجع عن ${entry.label}.`);
}

function redo() {
  if (!session.redo.length) return;
  const entry = session.redo.pop();
  session.current = clonePlan(entry.after);
  session.history.push(entry);
  discardPreview();
  setMessage(`تمت إعادة ${entry.label}.`);
}

function toggleConfidence() {
  session.confidence = session.confidence >= 0.8 ? 0.52 : 0.96;
  incrementInteraction();
  if (session.confidence < 0.8) {
    setMessage("المقياس تقريبي؛ المعاينة متاحة لكن الاعتماد المتري متوقف حتى المعايرة.", "warning");
  } else {
    setMessage("تمت محاكاة معايرة المقياس بنجاح.");
  }
  render();
}

function chooseCandidate(button) {
  const offsetMm = Number(button.dataset.offset);
  const next = clonePlan(session.current);
  next.wallOffsetMm += offsetMm;
  next.windowShiftMm += 200;
  const profileNames = {
    minimal: "أقل تغيير",
    balanced: "التحسين المتوازن",
    priority: "أولوية غرفة المعيشة",
  };
  const name = profileNames[button.dataset.candidate];
  stagePreview(next, `تطبيق ${name}`, [
    `${name}: تحريك الجدار ${offsetMm / 10} سم`,
    "تحريك النافذة 20 سم نحو الطرف ب",
    "مرّ الاقتراح عبر نفس التحقق قبل عرضه",
  ]);
  ui.plannerDialog.close();
}

function resetSession() {
  session.current = clonePlan(initialPlan);
  session.preview = null;
  session.previewLabel = "";
  session.previewDiffs = [];
  session.previewStale = false;
  session.selection = [];
  session.confidence = 0.96;
  session.history = [];
  session.redo = [];
  session.interactions = 0;
  session.compare = true;
  ui.wallOffset.value = "50";
  ui.aiPrompt.value = "";
  ui.numericError.hidden = true;
  ui.clarificationBox.hidden = true;
  setMessage("اختر غرفة للبدء.");
  render();
}

function setSvgLine(line, x1, y1, x2, y2) {
  line.setAttribute("x1", x1);
  line.setAttribute("y1", y1);
  line.setAttribute("x2", x2);
  line.setAttribute("y2", y2);
}

function renderSelection() {
  if (!session.selection.length) {
    ui.breadcrumb.innerHTML = "<span>لم تختر عنصراً بعد</span>";
  } else {
    ui.breadcrumb.replaceChildren();
    session.selection.forEach((item) => {
      const node = document.createElement("b");
      node.textContent = item.label;
      ui.breadcrumb.appendChild(node);
    });
  }
  document.querySelectorAll("[data-select]").forEach((button) => {
    button.classList.toggle("selected", session.selection.some((item) => item.id === button.dataset.id));
  });
  byId("roomLeft").classList.toggle("selected", session.selection.some((item) => item.id === "left"));
  byId("roomRight").classList.toggle("selected", session.selection.some((item) => item.id === "right"));
  ui.currentWall.classList.toggle("selected", session.selection.some((item) => item.id === "shared"));
  ui.currentWindow.classList.toggle("selected", session.selection.some((item) => item.id === "window"));
}

function renderPlan() {
  const currentX = wallX(session.current);
  const [windowStart, windowEnd] = windowCoordinates(session.current);
  setSvgLine(ui.currentWall, currentX, 100, currentX, 500);
  setSvgLine(ui.currentWindow, windowStart, 100, windowEnd, 100);
  const [leftArea, rightArea] = areas(session.current);
  ui.leftRoomLabel.textContent = `غرفة المعيشة · ${leftArea.toFixed(1)} م²`;
  ui.rightRoomLabel.textContent = `غرفة النوم · ${rightArea.toFixed(1)} م²`;
  ui.leftRoomLabel.setAttribute("x", 120 + (currentX - 120) / 2);
  ui.rightRoomLabel.setAttribute("x", currentX + (880 - currentX) / 2);

  const showProposal = Boolean(session.preview && session.compare);
  setElementHidden(ui.proposalLayer, !showProposal);
  if (showProposal) {
    const proposalX = wallX(session.preview);
    const [proposalStart, proposalEnd] = windowCoordinates(session.preview);
    setSvgLine(ui.proposalWall, proposalX, 100, proposalX, 500);
    setSvgLine(ui.proposalWindow, proposalStart, 100, proposalEnd, 100);
    const arrowStart = currentX;
    const arrowEnd = proposalX;
    ui.movementArrow.setAttribute("d", `M${arrowStart} 300H${arrowEnd}`);
  }
}

function renderPreview() {
  const hasPreview = Boolean(session.preview);
  ui.previewPanel.hidden = !hasPreview;
  ui.compareBtn.disabled = !hasPreview;
  ui.compareBtn.textContent = compareButtonLabel(hasPreview, session.compare);
  ui.canvasWrap.classList.toggle("preview-active", Boolean(session.preview));
  ui.canvasWrap.classList.toggle("stale", session.previewStale);
  if (!session.preview) {
    ui.canvasBadge.textContent = "الحالة المعتمدة";
    ui.viewMode.textContent = "الحالة المعتمدة";
    return;
  }
  ui.diffList.replaceChildren();
  session.previewDiffs.forEach((diff) => {
    const item = document.createElement("li");
    item.textContent = diff;
    ui.diffList.appendChild(item);
  });
  const preliminary = session.confidence < 0.8;
  ui.previewWarning.hidden = !preliminary && !session.previewStale;
  if (session.previewStale) {
    ui.previewStateBadge.textContent = "تحتاج تحديثاً";
    ui.previewWarning.textContent = "غيّرت المدخلات بعد هذه المعاينة. لا يمكن اعتمادها حتى تحديثها.";
    ui.approveBtn.textContent = "تحديث المعاينة";
    ui.approveBtn.disabled = false;
  } else if (preliminary) {
    ui.previewStateBadge.textContent = "تصور مبدئي";
    ui.previewWarning.textContent = "المقياس تقريبي. عاير المقياس قبل اعتماد أي تغيير متري.";
    ui.approveBtn.textContent = "معايرة المقياس للمتابعة";
    ui.approveBtn.disabled = false;
  } else {
    ui.previewStateBadge.textContent = "جاهزة للمراجعة";
    ui.approveBtn.textContent = "اعتماد التعديل";
    ui.approveBtn.disabled = false;
  }
  ui.canvasBadge.textContent = session.previewStale ? "معاينة قديمة" : "الحالي + المقترح";
  ui.viewMode.textContent = "معاينة مؤقتة — لم تعتمد";
}

function renderHistory() {
  const total = session.history.length + session.redo.length;
  ui.historyStatus.textContent = `العملية ${session.history.length} من ${total}`;
  ui.interactionStatus.textContent = `${session.interactions} تفاعل`;
  ui.undoBtn.disabled = !session.history.length;
  ui.redoBtn.disabled = !session.redo.length;
  ui.undoBtn.textContent = session.history.length ? `تراجع عن ${session.history.at(-1).label}` : "تراجع";
  ui.redoBtn.textContent = session.redo.length ? `إعادة ${session.redo.at(-1).label}` : "إعادة";
  ui.revisionLabel.textContent = session.history.length ? `النسخة المعتمدة ${session.history.length}` : "النسخة المعتمدة الأصلية";
}

function renderConfidence() {
  if (session.confidence < 0.8) {
    ui.confidenceBtn.textContent = "المقياس تقريبي 52%";
    ui.confidenceBtn.style.background = "var(--warn-bg)";
    ui.confidenceBtn.style.color = "var(--warn)";
  } else {
    ui.confidenceBtn.textContent = "المقياس مؤكد 96%";
    ui.confidenceBtn.style.background = "var(--accent-soft)";
    ui.confidenceBtn.style.color = "var(--accent)";
  }
}

function render() {
  renderSelection();
  renderPlan();
  renderPreview();
  renderHistory();
  renderConfidence();
}

function keyboardActivate(element, callback) {
  element.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      callback();
    }
  });
}

document.querySelectorAll("[data-select]").forEach((button) => {
  button.addEventListener("click", () => selectElement(button.dataset.select, button.dataset.id, button.dataset.label));
});
byId("roomLeft").addEventListener("click", () => selectElement("room", "left", "غرفة المعيشة"));
byId("roomRight").addEventListener("click", () => selectElement("room", "right", "غرفة النوم"));
ui.currentWall.addEventListener("click", () => selectElement("wall", "shared", "الجدار المشترك"));
ui.currentWindow.addEventListener("click", () => selectElement("opening", "window", "النافذة"));
keyboardActivate(byId("roomLeft"), () => selectElement("room", "left", "غرفة المعيشة"));
keyboardActivate(byId("roomRight"), () => selectElement("room", "right", "غرفة النوم"));
keyboardActivate(ui.currentWall, () => selectElement("wall", "shared", "الجدار المشترك"));
keyboardActivate(ui.currentWindow, () => selectElement("opening", "window", "النافذة"));

byId("previewNumberBtn").addEventListener("click", createNumericPreview);
ui.wallOffset.addEventListener("input", markPreviewStale);
byId("sendPromptBtn").addEventListener("click", handlePrompt);
ui.approveBtn.addEventListener("click", () => {
  if (session.previewStale) createNumericPreview();
  else if (session.confidence < 0.8) toggleConfidence();
  else approvePreview();
});
ui.discardPreviewBtn.addEventListener("click", discardPreview);
ui.compareBtn.addEventListener("click", () => { session.compare = !session.compare; render(); });
ui.undoBtn.addEventListener("click", undo);
ui.redoBtn.addEventListener("click", redo);
ui.confidenceBtn.addEventListener("click", toggleConfidence);
byId("resetBtn").addEventListener("click", resetSession);
byId("plannerBtn").addEventListener("click", () => ui.plannerDialog.showModal());
document.querySelectorAll("[data-candidate]").forEach((button) => button.addEventListener("click", () => chooseCandidate(button)));

render();
