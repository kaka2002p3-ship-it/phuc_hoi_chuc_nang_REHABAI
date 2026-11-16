import { AlertTriangle, Info } from 'lucide-react';

interface ClinicalDisclaimerProps {
  className?: string;
}

export function ClinicalDisclaimer({ className = "" }: ClinicalDisclaimerProps) {
  return (
    <div className={`bg-amber-50 border border-amber-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className="text-amber-500 flex-shrink-0 mt-0.5 w-5 h-5" />
        <div className="flex-1">
          <h4 className="font-semibold text-amber-800 text-sm">
            ⚠️ Cảnh báo Quan trọng
          </h4>
          <p className="text-amber-700 text-xs mt-1 leading-relaxed">
            Đây là hệ thống <strong>nghiên cứu và demo</strong>.
            Kết quả nhận dạng bài tập <strong>không được dùng</strong> để
            chẩn đoán hoặc thay thế chỉ định điều trị của bác sĩ phục hồi chức năng.
          </p>
          <div className="flex items-center gap-2 mt-2 text-xs text-amber-600">
            <Info className="w-3 h-3" />
            <span>Độ chính xác mô hình: 43.79% ± 23.35% (LOSO cross-validation)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
