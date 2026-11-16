import 'package:flutter/material.dart';
import '../models/exercise.dart';
import '../theme/app_theme.dart';
import '../widgets/app_widgets.dart';

class PracticePreview extends StatefulWidget {
  const PracticePreview({super.key, required this.exercise});
  final Exercise exercise;

  @override
  State<PracticePreview> createState() => _PracticePreviewState();
}

class _PracticePreviewState extends State<PracticePreview> {
  int _target = 5;
  int? _pain;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Chuẩn bị buổi tập', style: TextStyle(fontWeight: FontWeight.w800)),
          backgroundColor: AppColors.page,
          surfaceTintColor: Colors.transparent,
        ),
        body: SafeArea(
          child: ListView(padding: const EdgeInsets.fromLTRB(20, 8, 20, 28), children: [
            Container(
              height: 215,
              decoration: BoxDecoration(gradient: LinearGradient(colors: [widget.exercise.color.withOpacity(.08), widget.exercise.color.withOpacity(.18)]), borderRadius: BorderRadius.circular(26)),
              child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Container(width: 86, height: 86, decoration: BoxDecoration(color: Colors.white.withOpacity(.88), shape: BoxShape.circle), child: Icon(widget.exercise.icon, size: 44, color: widget.exercise.color)),
                const SizedBox(height: 16),
                Text(widget.exercise.title, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 5),
                Text(widget.exercise.category, style: TextStyle(fontSize: 10, letterSpacing: 1, fontWeight: FontWeight.w900, color: widget.exercise.color)),
              ]),
            ),
            const SizedBox(height: 20),
            const _StepRow(number: '1', title: 'Đọc hướng dẫn', subtitle: 'Thực hiện động tác chậm và trong phạm vi thoải mái', done: true),
            const SizedBox(height: 10),
            const _StepRow(number: '2', title: 'Kiểm tra camera', subtitle: 'Đảm bảo đủ sáng và thấy rõ vùng vận động'),
            const SizedBox(height: 10),
            const _StepRow(number: '3', title: 'Bắt đầu luyện tập', subtitle: 'Hệ thống sẽ theo dõi số lần lặp đã xác nhận'),
            const SizedBox(height: 22),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(children: [
                  const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('Số lần tập mục tiêu', style: TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink)), SizedBox(height: 4), Text('Có thể chọn từ 1 đến 30 lần', style: TextStyle(fontSize: 12, color: AppColors.muted))])),
                  IconButton.filledTonal(onPressed: _target > 1 ? () => setState(() => _target--) : null, icon: const Icon(Icons.remove_rounded)),
                  SizedBox(width: 42, child: Text('$_target', textAlign: TextAlign.center, style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900, color: AppColors.ink))),
                  IconButton.filled(onPressed: _target < 30 ? () => setState(() => _target++) : null, icon: const Icon(Icons.add_rounded)),
                ]),
              ),
            ),
            const SizedBox(height: 20),
            Text('Mức đau trước khi tập', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 5),
            Text('0 = không đau · 10 = đau dữ dội', style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 12),
            Wrap(spacing: 7, runSpacing: 7, children: List.generate(11, (value) => ChoiceChip(
              label: Text('$value'),
              selected: _pain == value,
              onSelected: (_) => setState(() => _pain = value),
              selectedColor: _pain != null && _pain! >= 7 ? AppColors.coral : AppColors.primary,
              labelStyle: TextStyle(color: _pain == value ? Colors.white : AppColors.muted, fontWeight: FontWeight.w800),
              side: const BorderSide(color: AppColors.line),
            ))),
            const SizedBox(height: 20),
            if (_pain != null && _pain! >= 7)
              Container(margin: const EdgeInsets.only(bottom: 16), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: const Color(0xFFFFEEEE), border: Border.all(color: const Color(0xFFF5B6B6)), borderRadius: BorderRadius.circular(16)), child: const Row(children: [Icon(Icons.warning_amber_rounded, color: Color(0xFFB83E4A)), SizedBox(width: 10), Expanded(child: Text('Mức đau đang cao. Bạn nên dừng và liên hệ chuyên viên y tế.', style: TextStyle(color: Color(0xFF9F3540), fontWeight: FontWeight.w700)))])),
            const SafetyNote(),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: _pain == null || _pain! >= 7 ? null : () => _showCameraPreview(context),
              icon: const Icon(Icons.camera_alt_outlined),
              label: const Text('Kiểm tra camera và bắt đầu'),
            ),
          ]),
        ),
      );

  void _showCameraPreview(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 30),
        decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 42, height: 4, decoration: BoxDecoration(color: AppColors.line, borderRadius: BorderRadius.circular(4))),
          const SizedBox(height: 20),
          Container(height: 250, decoration: BoxDecoration(color: const Color(0xFF111827), borderRadius: BorderRadius.circular(22)), child: const Center(child: Column(mainAxisSize: MainAxisSize.min, children: [Icon(Icons.videocam_outlined, size: 42, color: Colors.white70), SizedBox(height: 10), Text('Khu vực xem trước camera', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w700)), SizedBox(height: 5), Text('Camera sẽ được tích hợp với backend ở bước tiếp theo', style: TextStyle(color: Colors.white38, fontSize: 11))]))),
          const SizedBox(height: 18),
          const Text('Giao diện luyện tập đã sẵn sàng', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppColors.ink)),
          const SizedBox(height: 6),
          Text('Mục tiêu: $_target lần · Đau trước tập: $_pain/10', style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 18),
          SizedBox(width: double.infinity, child: FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Đã hiểu'))),
        ]),
      ),
    );
  }
}

class _StepRow extends StatelessWidget {
  const _StepRow({required this.number, required this.title, required this.subtitle, this.done = false});
  final String number;
  final String title;
  final String subtitle;
  final bool done;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: done ? AppColors.mint.withOpacity(.08) : Colors.white, border: Border.all(color: done ? AppColors.mint.withOpacity(.4) : AppColors.line), borderRadius: BorderRadius.circular(17)),
        child: Row(children: [
          Container(width: 34, height: 34, alignment: Alignment.center, decoration: BoxDecoration(color: done ? AppColors.mint : AppColors.soft, shape: BoxShape.circle), child: done ? const Icon(Icons.check_rounded, color: Colors.white, size: 19) : Text(number, style: const TextStyle(fontWeight: FontWeight.w900, color: AppColors.muted))),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink)), const SizedBox(height: 3), Text(subtitle, style: Theme.of(context).textTheme.bodyMedium)])),
        ]),
      );
}
