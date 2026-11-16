import 'package:flutter/material.dart';
import '../models/exercise.dart';
import '../theme/app_theme.dart';
import '../widgets/app_widgets.dart';
import 'practice_preview.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.onOpenExercises});
  final VoidCallback onOpenExercises;

  static const featured = [
    Exercise(title: 'Mở bàn tay', category: 'BÀN TAY', description: 'Theo dõi độ mở bàn tay và đếm số lần lặp.', duration: '5–8 phút', icon: Icons.back_hand_outlined, color: AppColors.primary),
    Exercise(title: 'Gập/duỗi khuỷu tay', category: 'KHUỶU TAY', description: 'Luyện một chu kỳ chuyển động chậm và ổn định.', duration: '8–10 phút', icon: Icons.accessibility_new_rounded, color: AppColors.coral),
  ];

  @override
  Widget build(BuildContext context) => SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 18, 20, 108),
              sliver: SliverList.list(children: [
                Row(children: [
                  const Expanded(child: RehabLogo(compact: true)),
                  _CircleButton(icon: Icons.notifications_none_rounded, onTap: () {}),
                  const SizedBox(width: 10),
                  const CircleAvatar(radius: 20, backgroundColor: Color(0xFFE5E8FF), child: Text('P', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w900))),
                ]),
                const SizedBox(height: 22),
                _HeroCard(onStart: () => _openPractice(context, featured.first)),
                const SizedBox(height: 18),
                const Row(children: [
                  Expanded(child: MetricCard(icon: Icons.calendar_month_outlined, label: 'Tổng buổi tập', value: '12', color: AppColors.primary)),
                  SizedBox(width: 12),
                  Expanded(child: MetricCard(icon: Icons.check_circle_outline_rounded, label: 'Đã hoàn thành', value: '9', color: AppColors.mint)),
                ]),
                const SizedBox(height: 24),
                SectionHeader(title: 'Bài tập hôm nay', subtitle: 'Tiếp tục theo kế hoạch của bạn', action: 'Xem tất cả', onAction: onOpenExercises),
                const SizedBox(height: 12),
                ...featured.map((exercise) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _ExerciseTile(exercise: exercise, onTap: () => _openPractice(context, exercise)),
                    )),
                const SizedBox(height: 10),
                const _ProgressStory(),
                const SizedBox(height: 18),
                const SafetyNote(),
              ]),
            ),
          ],
        ),
      );

  void _openPractice(BuildContext context, Exercise exercise) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => PracticePreview(exercise: exercise)));
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({required this.onStart});
  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) => Container(
        height: 255,
        decoration: BoxDecoration(
          gradient: const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Color(0xFFF0F1FF), Color(0xFFE8FBF6)]),
          borderRadius: BorderRadius.circular(28),
          border: Border.all(color: const Color(0xFFE3E6FA)),
        ),
        child: Stack(clipBehavior: Clip.hardEdge, children: [
          Positioned(right: -30, bottom: -18, top: 30, child: Image.asset('assets/images/hero-companion-3d.png', fit: BoxFit.contain)),
          Padding(
            padding: const EdgeInsets.all(22),
            child: SizedBox(
              width: 225,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Row(children: [Icon(Icons.auto_awesome_rounded, size: 15, color: AppColors.primary), SizedBox(width: 6), Text('HÀNH TRÌNH HÔM NAY', style: TextStyle(fontSize: 10, letterSpacing: 1.1, fontWeight: FontWeight.w900, color: AppColors.primary))]),
                const SizedBox(height: 13),
                Text('Chào Phúc,\nhôm nay mình cùng cố gắng nhé.', style: Theme.of(context).textTheme.headlineMedium?.copyWith(height: 1.15)),
                const Spacer(),
                FilledButton.icon(onPressed: onStart, icon: const Icon(Icons.play_arrow_rounded), label: const Text('Bắt đầu tập')),
              ]),
            ),
          ),
          Positioned(top: 18, right: 18, child: Container(width: 42, height: 42, alignment: Alignment.center, decoration: const BoxDecoration(color: AppColors.primary, shape: BoxShape.circle), child: const Text('AI', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900)))),
        ]),
      );
}

class _ExerciseTile extends StatelessWidget {
  const _ExerciseTile({required this.exercise, required this.onTap});
  final Exercise exercise;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(22),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(children: [
              Container(width: 70, height: 78, decoration: BoxDecoration(color: exercise.color.withOpacity(.1), borderRadius: BorderRadius.circular(18)), child: Icon(exercise.icon, color: exercise.color, size: 34)),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(exercise.category, style: TextStyle(fontSize: 10, letterSpacing: .9, fontWeight: FontWeight.w900, color: exercise.color)),
                const SizedBox(height: 5),
                Text(exercise.title, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 5),
                Row(children: [const Icon(Icons.schedule_rounded, size: 14, color: AppColors.muted), const SizedBox(width: 4), Text(exercise.duration, style: Theme.of(context).textTheme.bodyMedium)]),
              ])),
              Container(width: 38, height: 38, decoration: BoxDecoration(color: exercise.color, shape: BoxShape.circle), child: const Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 19)),
            ]),
          ),
        ),
      );
}

class _ProgressStory extends StatelessWidget {
  const _ProgressStory();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(gradient: const LinearGradient(colors: [Colors.white, Color(0xFFEAF9F6)]), border: Border.all(color: AppColors.line), borderRadius: BorderRadius.circular(22)),
        child: Row(children: [
          Container(width: 50, height: 50, decoration: BoxDecoration(color: const Color(0xFFFFF2CD), borderRadius: BorderRadius.circular(16)), child: const Icon(Icons.emoji_events_outlined, color: Color(0xFFD49318))),
          const SizedBox(width: 14),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('7 ngày liên tiếp', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppColors.ink)),
            const SizedBox(height: 4),
            Text('Bạn đang xây dựng một thói quen tốt.', style: Theme.of(context).textTheme.bodyMedium),
          ])),
          const Icon(Icons.auto_awesome_rounded, color: AppColors.coral),
        ]),
      );
}

class _CircleButton extends StatelessWidget {
  const _CircleButton({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => IconButton.filledTonal(onPressed: onTap, icon: Icon(icon), style: IconButton.styleFrom(backgroundColor: Colors.white, side: const BorderSide(color: AppColors.line)));
}
