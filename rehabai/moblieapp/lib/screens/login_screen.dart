import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/app_widgets.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onLogin});
  final VoidCallback onLogin;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _obscure = true;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 28, 24, 32),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Align(alignment: Alignment.centerLeft, child: RehabLogo()),
              const SizedBox(height: 34),
              Container(
                height: 205,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Color(0xFFECEEFF), Color(0xFFE5FAF5)]),
                  borderRadius: BorderRadius.circular(30),
                ),
                child: Stack(children: [
                  Positioned(right: -18, bottom: -8, top: 0, child: Image.asset('assets/images/hero-companion-3d.png', fit: BoxFit.contain)),
                  const Positioned(
                    left: 20,
                    top: 24,
                    width: 170,
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('Mỗi chuyển động nhỏ đều có ý nghĩa', style: TextStyle(fontSize: 22, height: 1.15, fontWeight: FontWeight.w900, color: AppColors.ink)),
                      SizedBox(height: 10),
                      Text('Luyện tập nhẹ nhàng, riêng tư và dễ theo dõi.', style: TextStyle(fontSize: 12, height: 1.45, color: AppColors.muted)),
                    ]),
                  ),
                  Positioned(
                    top: 16,
                    right: 18,
                    child: Container(
                      width: 42,
                      height: 42,
                      decoration: const BoxDecoration(color: AppColors.primary, shape: BoxShape.circle),
                      alignment: Alignment.center,
                      child: const Text('AI', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
                    ),
                  ),
                ]),
              ),
              const SizedBox(height: 28),
              Text('Chào mừng trở lại', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 6),
              Text('Đăng nhập để tiếp tục hành trình phục hồi.', style: Theme.of(context).textTheme.bodyLarge),
              const SizedBox(height: 24),
              const TextField(
                keyboardType: TextInputType.emailAddress,
                decoration: InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.mail_outline_rounded)),
              ),
              const SizedBox(height: 14),
              TextField(
                obscureText: _obscure,
                decoration: InputDecoration(
                  labelText: 'Mật khẩu',
                  prefixIcon: const Icon(Icons.lock_outline_rounded),
                  suffixIcon: IconButton(
                    onPressed: () => setState(() => _obscure = !_obscure),
                    icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                  ),
                ),
              ),
              Align(alignment: Alignment.centerRight, child: TextButton(onPressed: () {}, child: const Text('Quên mật khẩu?'))),
              FilledButton(onPressed: widget.onLogin, child: const Text('Đăng nhập')),
              const SizedBox(height: 14),
              OutlinedButton(
                onPressed: widget.onLogin,
                style: OutlinedButton.styleFrom(minimumSize: const Size(0, 52), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)), side: const BorderSide(color: AppColors.line)),
                child: const Text('Dùng giao diện demo'),
              ),
              const SizedBox(height: 24),
              const Text('Ứng dụng hỗ trợ theo dõi luyện tập, không phải thiết bị chẩn đoán y khoa.', textAlign: TextAlign.center, style: TextStyle(fontSize: 11, height: 1.4, color: AppColors.muted)),
            ]),
          ),
        ),
      );
}

