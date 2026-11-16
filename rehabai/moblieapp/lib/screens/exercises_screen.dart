import 'package:flutter/material.dart';
import '../models/exercise.dart';
import '../theme/app_theme.dart';
import '../widgets/app_widgets.dart';
import 'practice_preview.dart';

class ExercisesScreen extends StatelessWidget {
  const ExercisesScreen({super.key});

  static const exercises = [
    Exercise(title: 'Gập/duỗi khuỷu tay', category: 'KHUỶU TAY', description: 'Theo dõi một chu kỳ chuyển động khuỷu tay trong vùng camera.', duration: '8–10 phút', icon: Icons.accessibility_new_rounded, color: AppColors.coral),
    Exercise(title: 'Mở bàn tay', category: 'BÀN TAY', description: 'Mở các ngón tay từ từ và giữ cổ tay ổn định.', duration: '5–8 phút', icon: Icons.back_hand_outlined, color: AppColors.primary),
    Exercise(title: 'Nghiêng cổ hai bên', category: 'CỔ · VAI', description: 'Thư giãn cổ nhẹ nhàng theo hướng dẫn an toàn.', duration: '4–6 phút', icon: Icons.self_improvement_rounded, color: AppColors.mint, isNew: true),
    Exercise(title: 'Hít thở sâu', category: 'THƯ GIÃN', description: 'Hít vào và thở ra theo nhịp hướng dẫn.', duration: '6 chu kỳ', icon: Icons.air_rounded, color: Color(0xFF36A8D4), isNew: true),
  ];

  @override
  Widget build(BuildContext context) => SafeArea(
        child: CustomScrollView(slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 22, 20, 108),
            sliver: SliverList.list(children: [
              Text('Bài tập', style: Theme.of(context).textTheme.headlineLarge),
              const SizedBox(height: 6),
              Text('Chọn bài phù hợp và luyện tập trong phạm vi không gây đau.', style: Theme.of(context).textTheme.bodyLarge),
              const SizedBox(height: 18),
              TextField(readOnly: true, decoration: const InputDecoration(hintText: 'Tìm bài tập', prefixIcon: Icon(Icons.search_rounded))),
              const SizedBox(height: 20),
              const _FilterRow(),
              const SizedBox(height: 18),
              ...exercises.map((exercise) => Padding(
                    padding: const EdgeInsets.only(bottom: 14),
                    child: _ExerciseCard(exercise: exercise, onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PracticePreview(exercise: exercise)))),
                  )),
              const SafetyNote(),
            ]),
          ),
        ]),
      );
}

class _FilterRow extends StatelessWidget {
  const _FilterRow();
  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: ['Tất cả', 'Bàn tay', 'Khuỷu tay', 'Thư giãn'].asMap().entries.map((entry) {
          final selected = entry.key == 0;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(selected: selected, onSelected: (_) {}, label: Text(entry.value), selectedColor: AppColors.primary, labelStyle: TextStyle(color: selected ? Colors.white : AppColors.muted, fontWeight: FontWeight.w700), side: const BorderSide(color: AppColors.line)),
          );
        }).toList()),
      );
}

class _ExerciseCard extends StatelessWidget {
  const _ExerciseCard({required this.exercise, required this.onTap});
  final Exercise exercise;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
        child: InkWell(
          borderRadius: BorderRadius.circular(22),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(children: [
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(width: 86, height: 105, decoration: BoxDecoration(gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [exercise.color.withOpacity(.08), exercise.color.withOpacity(.18)]), borderRadius: BorderRadius.circular(20)), child: Icon(exercise.icon, color: exercise.color, size: 42)),
                const SizedBox(width: 15),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [Text(exercise.category, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: .8, color: exercise.color)), if (exercise.isNew) ...[const SizedBox(width: 7), Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3), decoration: BoxDecoration(color: AppColors.mint.withOpacity(.12), borderRadius: BorderRadius.circular(20)), child: const Text('MỚI', style: TextStyle(fontSize: 8, fontWeight: FontWeight.w900, color: Color(0xFF13845C))))]]),
                  const SizedBox(height: 7),
                  Text(exercise.title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 6),
                  Text(exercise.description, maxLines: 2, overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 8),
                  Row(children: [const Icon(Icons.schedule_rounded, size: 14, color: AppColors.muted), const SizedBox(width: 4), Text(exercise.duration, style: Theme.of(context).textTheme.bodyMedium)]),
                ])),
              ]),
              const SizedBox(height: 14),
              SizedBox(width: double.infinity, child: FilledButton.icon(onPressed: onTap, icon: const Icon(Icons.play_arrow_rounded), label: const Text('Chọn bài này'))),
            ]),
          ),
        ),
      );
}
