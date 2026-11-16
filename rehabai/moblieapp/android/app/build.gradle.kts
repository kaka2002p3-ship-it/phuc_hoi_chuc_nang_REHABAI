plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("dev.flutter.flutter-gradle-plugin")
}

android { namespace = "com.rehabai.mobile"; compileSdk = 35
    defaultConfig { applicationId = "com.rehabai.mobile"; minSdk = 24; targetSdk = 35; versionCode = 1; versionName = "1.0.0" }
}

flutter { source = "../.." }

