/**
 * 心犀AI - 图片上传组件
 * =======================
 *
 * 功能：
 * - 点击上传区域触发文件选择
 * - 上传前用 browser-image-compression 压缩到 ≤800px、≤500KB
 * - 支持头像模式（圆形单图）和照片模式（最多 6 张网格）
 * - 删除照片（调用 API）
 *
 * 学习要点 — browser-image-compression:
 *   import imageCompression from 'browser-image-compression'
 *   const compressed = await imageCompression(file, { maxSizeMB: 0.5, maxWidthOrHeight: 800 })
 *   压缩在浏览器端（Web Worker）执行，不占用主线程，不需要服务器参与。
 *   上传 1MB+ 的图片时可明显减少上传时间。
 *
 * 学习要点 — useRef 操作 DOM:
 *   fileInputRef.current?.click() 触发隐藏的 <input type="file"> 的点击事件
 *   这是 React 中操作真实 DOM 的标准方式——避免直接 document.getElementById()
 */
import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import imageCompression from 'browser-image-compression'
import { Upload, X, Plus, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { uploadAvatar, uploadPhoto, deletePhoto } from '@/api/client'

interface ImageUploadProps {
  /** 当前图片 URL 列表 */
  value: string[]
  /** 图片列表变化回调 */
  onChange: (urls: string[]) => void
  /** 最大图片数量 */
  maxCount?: number
  /** 头像模式（单图、圆形显示） */
  isAvatar?: boolean
  className?: string
}

// 压缩配置：800px 以内，最大 500KB
const COMPRESS_OPTIONS = {
  maxSizeMB: 0.5,
  maxWidthOrHeight: 800,
  useWebWorker: true,  // 使用 Web Worker，不阻塞 UI 主线程
}

export default function ImageUpload({
  value,
  onChange,
  maxCount = 6,
  isAvatar = false,
  className,
}: ImageUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [deletingIndex, setDeletingIndex] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    if (!isAvatar && value.length >= maxCount) return

    const file = files[0]
    setUploading(true)

    try {
      // 1. 浏览器端压缩图片（减少上传时间和服务器存储）
      const compressed = await imageCompression(file, COMPRESS_OPTIONS)

      // 2. 上传到服务器
      if (isAvatar) {
        const res = await uploadAvatar(compressed as File)
        onChange([res.data.url])
      } else {
        const res = await uploadPhoto(compressed as File)
        onChange(res.data.photos)
      }
    } catch (e: unknown) {
      console.error('图片上传失败', e)
      alert('图片上传失败，请重试')
    } finally {
      setUploading(false)
      // 清空 input，允许重复选择同一文件
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDelete = async (index: number) => {
    if (isAvatar) {
      // 头像删除只清空本地状态，不调 API（头像始终有值）
      onChange([])
      return
    }
    setDeletingIndex(index)
    try {
      const res = await deletePhoto(index)
      onChange(res.data.photos)
    } catch (e) {
      console.error('删除失败', e)
    } finally {
      setDeletingIndex(null)
    }
  }

  // === 头像模式：圆形单图 ===
  if (isAvatar) {
    const avatarUrl = value[0]
    return (
      <div className={cn("relative w-24 h-24", className)}>
        <div
          className={cn(
            "w-full h-full rounded-full overflow-hidden cursor-pointer",
            "border-2 border-primary/30 hover:border-primary/60 transition-colors",
            "bg-muted flex items-center justify-center"
          )}
          onClick={() => !uploading && fileInputRef.current?.click()}
        >
          {avatarUrl ? (
            <img src={avatarUrl} alt="头像" className="w-full h-full object-cover" />
          ) : (
            <div className="flex flex-col items-center gap-1 text-muted-foreground">
              {uploading
                ? <Loader2 size={24} className="animate-spin text-primary" />
                : <Upload size={24} />
              }
            </div>
          )}
        </div>
        {/* 删除按钮 */}
        {avatarUrl && (
          <button
            onClick={() => handleDelete(0)}
            className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-destructive text-white flex items-center justify-center shadow-md"
          >
            <X size={12} />
          </button>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={e => handleFileSelect(e.target.files)}
        />
      </div>
    )
  }

  // === 照片网格模式 ===
  return (
    <div className={cn("space-y-2", className)}>
      <div className="grid grid-cols-3 gap-2">
        <AnimatePresence>
          {value.map((url, i) => (
            <motion.div
              key={url}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.2 }}
              className="relative aspect-square rounded-lg overflow-hidden group"
            >
              <img
                src={url}
                alt={`照片${i + 1}`}
                className="w-full h-full object-cover"
              />
              {/* 删除按钮（hover 时显示） */}
              <button
                onClick={() => handleDelete(i)}
                disabled={deletingIndex === i}
                className={cn(
                  "absolute top-1 right-1 w-5 h-5 rounded-full",
                  "bg-black/60 text-white flex items-center justify-center",
                  "opacity-0 group-hover:opacity-100 transition-opacity"
                )}
              >
                {deletingIndex === i
                  ? <Loader2 size={10} className="animate-spin" />
                  : <X size={10} />
                }
              </button>
              {/* 序号角标 */}
              <div className="absolute bottom-1 left-1 w-5 h-5 rounded-full bg-black/40 text-white text-[10px] flex items-center justify-center">
                {i + 1}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* 上传按钮（未达上限时显示） */}
        {value.length < maxCount && (
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className={cn(
              "aspect-square rounded-lg",
              "border-2 border-dashed border-border",
              "hover:border-primary/50 hover:bg-primary/5",
              "flex flex-col items-center justify-center gap-1",
              "transition-colors text-muted-foreground hover:text-primary"
            )}
          >
            {uploading
              ? <Loader2 size={20} className="animate-spin text-primary" />
              : (
                <>
                  <Plus size={20} />
                  <span className="text-[11px]">{value.length}/{maxCount}</span>
                </>
              )
            }
          </button>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={e => handleFileSelect(e.target.files)}
      />
    </div>
  )
}
