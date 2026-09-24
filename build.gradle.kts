plugins {
    id("com.android.application") version "8.1.2"
    id("org.jetbrains.kotlin.android") version "1.9.0"
    id("org.jetbrains.kotlin.plugin.serialization") version "1.9.0"
}

android {
    namespace = "eu.kanade.tachiyomi.animeextension.all.webdav"
    compileSdk = 34

    defaultConfig {
        applicationId = "eu.kanade.tachiyomi.animeextension.all.webdav"
        minSdk = 21
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions {
        jvmTarget = "1.8"
    }
}

dependencies {
    compileOnly("com.github.komikku-app:aniyomi-extensions-lib:master-SNAPSHOT")
    compileOnly("com.squareup.okhttp3:okhttp:4.11.0")
    compileOnly("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.0")
    compileOnly("androidx.preference:preference-ktx:1.2.1")
}
