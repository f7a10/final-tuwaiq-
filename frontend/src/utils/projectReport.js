import { roomLabelAr } from './roomLabels.js'

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function formatDate(value) {
  if (!value) return 'غير متاح'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return escapeHtml(value)
  return new Intl.DateTimeFormat('ar-SA', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function percent(value) {
  const number = Number(value)
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : 'غير متاح'
}

function score(value) {
  const number = Number(value)
  return Number.isFinite(number) ? `${Math.round(number)}%` : 'غير متاح'
}

export function buildProjectReportHtml(report) {
  const project = report?.project || {}
  const revision = report?.revision || {}
  const summary = report?.summary || {}
  const confidence = report?.confidence || {}
  const rooms = Array.isArray(report?.rooms) ? report.rooms : []
  const findings = Array.isArray(report?.findings) ? report.findings : []

  const roomRows = rooms.map(room => `
    <tr>
      <td>${escapeHtml(roomLabelAr(room.label))}</td>
      <td>${escapeHtml(room.width_m)} م</td>
      <td>${escapeHtml(room.height_m)} م</td>
      <td>${escapeHtml(room.area_m2)} م²</td>
    </tr>`).join('')
  const findingRows = findings.length
    ? findings.map(finding => `
      <article class="finding">
        <div><strong>${escapeHtml(finding.status_ar)}</strong><span>${escapeHtml(roomLabelAr(finding.label))}</span></div>
        <p>${escapeHtml(finding.reason_ar)}</p>
        <small>${escapeHtml(finding.reference)}</small>
      </article>`).join('')
    : '<p class="empty">لم تظهر مشكلة محتملة ضمن العناصر التي استطاع النظام قراءتها. لا يعني ذلك مطابقة كاملة.</p>'

  return `<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>تقرير عماد — ${escapeHtml(project.title)}</title>
  <style>
    :root { color-scheme: light; font-family: Tahoma, Arial, sans-serif; color: #1f2924; background: #fff; }
    * { box-sizing: border-box; }
    body { max-width: 920px; margin: 0 auto; padding: 34px; line-height: 1.7; }
    header { display: flex; justify-content: space-between; gap: 24px; padding-bottom: 20px; border-bottom: 3px solid #176b5b; }
    h1, h2, p { margin: 0; }
    h1 { font-size: 26px; }
    h2 { margin-bottom: 12px; font-size: 18px; }
    .brand { color: #176b5b; font-size: 22px; font-weight: 800; }
    .meta { color: #5f6d66; font-size: 12px; text-align: left; }
    .revision { margin-top: 18px; padding: 14px 18px; border: 1px solid #badbcf; border-radius: 10px; background: #eef8f4; }
    .revision strong { color: #115647; }
    .facts { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 18px 0; }
    .fact { padding: 12px; border: 1px solid #dde4df; border-radius: 9px; }
    .fact span { display: block; color: #65736c; font-size: 11px; }
    .fact strong { font-size: 17px; }
    section { margin-top: 26px; break-inside: avoid; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px; border: 1px solid #dce3df; text-align: right; }
    th { background: #f4f7f5; }
    .finding { margin-bottom: 10px; padding: 13px; border: 1px solid #ecd5aa; border-radius: 9px; background: #fffaf0; }
    .finding div { display: flex; justify-content: space-between; gap: 12px; }
    .finding strong { color: #825b17; }
    .finding p { margin-top: 5px; font-size: 13px; }
    .finding small, .empty { color: #65736c; font-size: 11px; }
    .notice { margin-top: 28px; padding: 15px; border-right: 4px solid #c48216; background: #fff9ed; color: #654b1c; font-size: 12px; }
    footer { margin-top: 28px; padding-top: 14px; border-top: 1px solid #dce3df; color: #65736c; font-size: 11px; }
    .print { min-height: 44px; margin-top: 18px; padding: 0 18px; border: 0; border-radius: 8px; background: #176b5b; color: #fff; font: inherit; font-weight: 700; cursor: pointer; }
    @media (max-width: 680px) { body { padding: 18px; } header { flex-direction: column; } .meta { text-align: right; } .facts { grid-template-columns: 1fr 1fr; } }
    @media print { @page { size: A4; margin: 14mm; } body { max-width: none; padding: 0; } .print { display: none; } }
  </style>
</head>
<body>
  <header>
    <div><div class="brand">عماد</div><h1>${escapeHtml(project.title)}</h1><p>تقرير مراجعة المخطط</p></div>
    <div class="meta">رقم المشروع: ${escapeHtml(project.id)}<br>تاريخ التقرير: ${formatDate(report?.generated_at)}</div>
  </header>

  <div class="revision"><strong>النسخة المعتمدة ${escapeHtml(revision.number)}</strong> — ${escapeHtml(revision.label)}<br><small>تاريخ النسخة: ${formatDate(revision.created_at)}</small></div>

  <div class="facts">
    <div class="fact"><span>عدد الغرف</span><strong>${escapeHtml(summary.rooms_count ?? rooms.length)}</strong></div>
    <div class="fact"><span>إجمالي المساحة</span><strong>${escapeHtml(summary.total_area_m2)} م²</strong></div>
    <div class="fact"><span>مشاكل محتملة</span><strong>${escapeHtml(summary.potential_issues_count ?? findings.length)}</strong></div>
    <div class="fact"><span>النتيجة الأولية</span><strong>${score(summary.compliance_score)}</strong></div>
  </div>

  <section>
    <h2>الغرف والقياسات في النسخة الحالية</h2>
    <table><thead><tr><th>الغرفة</th><th>العرض</th><th>الطول</th><th>المساحة</th></tr></thead><tbody>${roomRows}</tbody></table>
  </section>

  <section><h2>الملاحظات المحتملة</h2>${findingRows}</section>

  <section>
    <h2>ثقة البيانات</h2>
    <p>المقياس: ${percent(confidence.scale)} · مطابقة الرسم: ${percent(confidence.geometry)}</p>
  </section>

  <div class="notice">${escapeHtml(report?.disclaimer_ar)}</div>
  <button class="print" type="button" onclick="window.print()">طباعة أو حفظ PDF</button>
  <footer>أُنشئ هذا التقرير من Revision محفوظة في عماد. لا يتضمن التقرير أي Preview غير معتمدة.</footer>
</body>
</html>`
}

export function downloadProjectReport(report) {
  const html = buildProjectReportHtml(report)
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `emad-project-${report.project.id}-revision-${report.revision.number}.html`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
