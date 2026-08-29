import { describe, expect, it } from 'vitest'

import { buildProjectReportHtml } from './projectReport'

const report = {
  generated_at: '2026-08-29T18:00:00+00:00',
  project: { id: 7, title: 'منزل <script>alert(1)</script>' },
  revision: { number: 2, label: 'توسيع غرفة المعيشة', created_at: '2026-08-29T17:00:00+00:00' },
  confidence: { scale: 1, geometry: 0.9 },
  summary: { rooms_count: 2, total_area_m2: 24, potential_issues_count: 1, compliance_score: 72 },
  rooms: [
    { id: 'room-1', label: 'غرفة المعيشة', width_m: 4.5, height_m: 3, area_m2: 13.5 },
    { id: 'room-2', label: 'غرفة النوم', width_m: 3.5, height_m: 3, area_m2: 10.5 },
  ],
  findings: [
    {
      room_id: 'room-2',
      label: 'غرفة النوم',
      status_ar: 'مشكلة محتملة',
      reason_ar: 'المساحة تحتاج مراجعة.',
      reference: 'المصدر غير موثق — يحتاج مراجعة مختص',
    },
  ],
  disclaimer_ar: 'هذا التقرير مراجعة أولية وليس اعتمادًا هندسيًا.',
}

describe('buildProjectReportHtml', () => {
  it('renders the approved revision and escapes project content', () => {
    const html = buildProjectReportHtml(report)

    expect(html).toContain('dir="rtl"')
    expect(html).toContain('النسخة المعتمدة 2')
    expect(html).toContain('13.5 م²')
    expect(html).toContain('مشكلة محتملة')
    expect(html).toContain('مراجعة أولية وليس اعتمادًا هندسيًا')
    expect(html).not.toContain('<script>alert(1)</script>')
    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
  })

  it('renders canonical room labels in Arabic', () => {
    const html = buildProjectReportHtml({
      ...report,
      rooms: [
        { ...report.rooms[0], label: 'Living Room' },
        { ...report.rooms[1], label: 'Bedroom' },
      ],
      findings: [{ ...report.findings[0], label: 'Bedroom' }],
    })

    expect(html).toContain('غرفة معيشة')
    expect(html).toContain('غرفة نوم')
    expect(html).not.toContain('Living Room')
    expect(html).not.toContain('Bedroom')
  })
})
