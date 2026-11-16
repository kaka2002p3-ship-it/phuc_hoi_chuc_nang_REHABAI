import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/app_widgets.dart';

class ProgressScreen extends StatelessWidget {
  const ProgressScreen({super.key});

  @override
  Widget build(BuildContext context) => SafeArea(
        child: ListView(padding: const EdgeInsets.fromLTRB(20, 22, 20, 108), children: [
          Text('Tiến trình', style: Theme.of(context).textTheme.headlineLarge),
          const SizedBox(height: 6),
          Text('Theo dõi thói quen luyện tập theo thời gian.', style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: 20),
          const Row(children: [
            Expanded(child: MetricCard(icon: Icons.local_fire_department_outlined, label: 'Chuỗi ngày', value: '7 ngày', color: AppColors.coral)),
            SizedBox(width: 12),
            Expanded(child: MetricCard(icon: Icons.task_alt_rounded, label: 'Hoàn thành', value: '75%', color: AppColors.mint)),
          ]),
          const SizedBox(height: 20),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const SectionHeader(title: 'Hoạt động 7 ngày', subtitle: 'Số lần tập đã xác nhận'),
                const SizedBox(height: 20),
                const SizedBox(height: 170, child: _WeeklyChart()),
                const SizedBox(height: 14),
                Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: AppColors.primary.withOpacity(.07), borderRadius: BorderRadius.circular(14)), child: const Row(children: [Icon(Icons.trending_up_rounded, color: AppColors.primary), SizedBox(width: 10), Expanded(child: Text('Bạn tập nhiều hơn 18% so với tuần trước.', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.primaryDark)))])),
              ]),
            ),
          ),
          const SizedBox(height: 24),
          const SectionHeader(title: 'Lịch sử gần đây', action: 'Xem tất cả'),
          const SizedBox(height: 12),
          const _HistoryItem(title: 'Mở bàn tay', date: 'Hôm nay · 09:15', reps: '5/5 lần', icon: Icons.back_hand_outlined, color: AppColors.primary),
          const SizedBox(height: 10),
          const _HistoryItem(title: 'Gập/duỗi khuỷu tay', date: 'Hôm qua · 16:40', reps: '8/8 lần', icon: Icons.accessibility_new_rounded, color: AppColors.coral),
          const SizedBox(height: 10),
          const _HistoryItem(title: 'Hít thở sâu', date: '30/09/2026 · 20:10', reps: '6 chu kỳ', icon: Icons.air_rounded, color: Color(0xFF36A8D4)),
          const SizedBox(height: 20),
          const SafetyNote(),
        ]),
      );
}

class _WeeklyChart extends StatelessWidget {
  const _WeeklyChart();
  @override
  Widget build(BuildContext context) {
    const values = [3.0, 5.0, 4.0, 8.0, 6.0, 9.0, 7.0];
    const labels = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
    return Row(crossAxisAlignment: CrossAxisAlignment.end, children: List.generate(values.length, (index) => Expanded(
      child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
        Text('${values[index].toInt()}', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppColors.muted)),
        const SizedBox(height: 5),
        Container(height: values[index] * 11, margin: const EdgeInsets.symmetric(horizontal: 5), decoration: BoxDecoration(gradient: const LinearGradient(begin: Alignment.bottomCenter, end: Alignment.topCenter, colors: [AppColors.primary, Color(0xFF8A72F6)]), borderRadius: BorderRadius.circular(8))),
        const SizedBox(height: 8),
        Text(labels[index], style: const TextStyle(fontSize: 10, color: AppColors.muted)),
      ]),
    )));
  }
}

class _HistoryItem extends StatelessWidget {
  const _HistoryItem({required this.title, required this.date, required this.reps, required this.icon, required this.color});
  final String title;
  final String date;
  final String reps;
  final IconData icon;
  final Color color;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(14), child: Row(children: [
    Container(width: 48, height: 48, decoration: BoxDecoration(color: color.withOpacity(.1), borderRadius: BorderRadius.circular(15)), child: Icon(icon, color: color)),
    const SizedBox(width: 12),
    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink)), const SizedBox(height: 4), Text(date, style: Theme.of(context).textTheme.bodyMedium)])),
    Column(crossAxisAlignment: CrossAxisAlignment.end, children: [Text(reps, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AppColors.primary)), const SizedBox(height: 5), const Icon(Icons.chevron_right_rounded, color: AppColors.muted)]),
  ])));
}
