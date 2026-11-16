import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/app_widgets.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key, required this.onSignOut});
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) => SafeArea(
        child: ListView(padding: const EdgeInsets.fromLTRB(20, 22, 20, 108), children: [
          Text('Hồ sơ', style: Theme.of(context).textTheme.headlineLarge),
          const SizedBox(height: 20),
          Card(child: Padding(padding: const EdgeInsets.all(18), child: Row(children: [
            Container(width: 70, height: 70, alignment: Alignment.center, decoration: const BoxDecoration(shape: BoxShape.circle, gradient: LinearGradient(colors: [AppColors.primary, AppColors.mint])), child: const Text('P', style: TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900))),
            const SizedBox(width: 14),
            const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('Phúc Nguyễn', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: AppColors.ink)), SizedBox(height: 4), Text('Người dùng RehabAI', style: TextStyle(color: AppColors.muted, fontSize: 13)), SizedBox(height: 8), Text('7 ngày luyện tập liên tiếp', style: TextStyle(color: AppColors.primary, fontSize: 12, fontWeight: FontWeight.w800))])),
            IconButton(onPressed: () {}, icon: const Icon(Icons.edit_outlined, color: AppColors.primary)),
          ]))),
          const SizedBox(height: 24),
          const SectionHeader(title: 'Cài đặt ứng dụng'),
          const SizedBox(height: 10),
          _SettingTile(icon: Icons.notifications_none_rounded, title: 'Nhắc lịch tập', subtitle: 'Nhắc nhẹ lúc 08:00 mỗi ngày', trailing: Switch(value: true, onChanged: (_) {})),
          _SettingTile(icon: Icons.dark_mode_outlined, title: 'Giao diện tối', subtitle: 'Đang dùng giao diện sáng', trailing: Switch(value: false, onChanged: (_) {})),
          _SettingTile(icon: Icons.shield_outlined, title: 'Quyền riêng tư', subtitle: 'Video không được lưu sau phiên', trailing: const Icon(Icons.chevron_right_rounded, color: AppColors.muted)),
          _SettingTile(icon: Icons.help_outline_rounded, title: 'Trợ giúp', subtitle: 'Câu hỏi thường gặp và hướng dẫn', trailing: const Icon(Icons.chevron_right_rounded, color: AppColors.muted)),
          const SizedBox(height: 22),
          const SafetyNote(),
          const SizedBox(height: 20),
          OutlinedButton.icon(onPressed: onSignOut, icon: const Icon(Icons.logout_rounded), label: const Text('Đăng xuất'), style: OutlinedButton.styleFrom(foregroundColor: AppColors.coral, minimumSize: const Size(0, 52), side: const BorderSide(color: Color(0xFFF2C2C2)), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)))),
          const SizedBox(height: 20),
          const Center(child: Text('RehabAI Mobile · phiên bản giao diện 1.0', style: TextStyle(color: AppColors.muted, fontSize: 11))),
        ]),
      );
}

class _SettingTile extends StatelessWidget {
  const _SettingTile({required this.icon, required this.title, required this.subtitle, required this.trailing});
  final IconData icon;
  final String title;
  final String subtitle;
  final Widget trailing;
  @override
  Widget build(BuildContext context) => Card(margin: const EdgeInsets.only(bottom: 8), child: ListTile(contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 3), leading: Container(width: 40, height: 40, decoration: BoxDecoration(color: AppColors.primary.withOpacity(.09), borderRadius: BorderRadius.circular(12)), child: Icon(icon, color: AppColors.primary, size: 20)), title: Text(title, style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink)), subtitle: Text(subtitle, style: const TextStyle(fontSize: 11, color: AppColors.muted)), trailing: trailing));
}
