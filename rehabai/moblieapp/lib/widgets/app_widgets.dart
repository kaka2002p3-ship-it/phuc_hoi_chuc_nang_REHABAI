import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class RehabLogo extends StatelessWidget {
  const RehabLogo({super.key, this.compact = false});
  final bool compact;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: compact ? 38 : 46,
            height: compact ? 38 : 46,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFFE6E9FF), Color(0xFFD8FAF2)]),
              borderRadius: BorderRadius.circular(compact ? 12 : 15),
            ),
            child: const Icon(Icons.volunteer_activism_rounded, color: AppColors.primary),
          ),
          const SizedBox(width: 10),
          RichText(
            text: TextSpan(
              style: TextStyle(fontSize: compact ? 20 : 24, fontWeight: FontWeight.w900, color: AppColors.ink),
              children: const [TextSpan(text: 'Rehab'), TextSpan(text: 'AI', style: TextStyle(color: AppColors.primary))],
            ),
          ),
        ],
      );
}

class SectionHeader extends StatelessWidget {
  const SectionHeader({super.key, required this.title, this.subtitle, this.action, this.onAction});
  final String title;
  final String? subtitle;
  final String? action;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              if (subtitle != null) ...[
                const SizedBox(height: 4),
                Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ]),
          ),
          if (action != null)
            TextButton(onPressed: onAction, child: Text(action!, style: const TextStyle(fontWeight: FontWeight.w700))),
        ],
      );
}

class MetricCard extends StatelessWidget {
  const MetricCard({super.key, required this.icon, required this.label, required this.value, required this.color});
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(color: color.withOpacity(.12), borderRadius: BorderRadius.circular(12)),
              child: Icon(icon, size: 20, color: color),
            ),
            const SizedBox(height: 14),
            Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: AppColors.ink)),
            const SizedBox(height: 2),
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ]),
        ),
      );
}

class SafetyNote extends StatelessWidget {
  const SafetyNote({super.key});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFFFF8E8),
          border: Border.all(color: const Color(0xFFF4D38A)),
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(Icons.health_and_safety_outlined, color: Color(0xFF9A6A12), size: 21),
          SizedBox(width: 10),
          Expanded(child: Text('Dừng tập nếu đau tăng, tê, chóng mặt hoặc khó chịu bất thường. RehabAI không thay thế tư vấn y tế.', style: TextStyle(color: Color(0xFF795B20), fontSize: 12, height: 1.45, fontWeight: FontWeight.w600))),
        ]),
      );
}
