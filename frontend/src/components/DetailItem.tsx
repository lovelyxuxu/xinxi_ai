/**
 * 心犀AI - 详情项组件
 * =====================
 *
 * 用于展示用户的结构化信息（省份、学历、收入等），
 * 比 InfoBlock 更紧凑，适合网格布局中的小卡片。
 */
interface DetailItemProps {
  /** 字段标签（如 "省份"、"学历"） */
  label: string
  /** 字段值 */
  value: string
}

export function DetailItem({ label, value }: DetailItemProps) {
  return (
    <div className="bg-gray-50 rounded-lg px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm text-gray-700 font-medium">{value || '-'}</p>
    </div>
  )
}
