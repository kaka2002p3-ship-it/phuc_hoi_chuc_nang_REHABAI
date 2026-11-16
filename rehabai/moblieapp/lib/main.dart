import 'package:flutter/material.dart';
import 'screens/login_screen.dart';
import 'screens/main_shell.dart';
import 'theme/app_theme.dart';

void main() => runApp(const RehabAiApp());

class RehabAiApp extends StatefulWidget {
  const RehabAiApp({super.key});

  @override
  State<RehabAiApp> createState() => _RehabAiAppState();
}

class _RehabAiAppState extends State<RehabAiApp> {
  bool _signedIn = false;

  @override
  Widget build(BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'RehabAI',
        theme: buildAppTheme(),
        home: AnimatedSwitcher(
          duration: const Duration(milliseconds: 350),
          child: _signedIn
              ? MainShell(key: const ValueKey('shell'), onSignOut: () => setState(() => _signedIn = false))
              : LoginScreen(key: const ValueKey('login'), onLogin: () => setState(() => _signedIn = true)),
        ),
      );
}

