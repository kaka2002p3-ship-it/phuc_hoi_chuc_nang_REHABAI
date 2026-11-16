import 'package:flutter/material.dart';

class Exercise {
  const Exercise({
    required this.title,
    required this.category,
    required this.description,
    required this.duration,
    required this.icon,
    required this.color,
    this.isNew = false,
  });

  final String title;
  final String category;
  final String description;
  final String duration;
  final IconData icon;
  final Color color;
  final bool isNew;
}

