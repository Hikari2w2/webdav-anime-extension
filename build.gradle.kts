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
        versionName = "14.1"
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
    compileOnly("com.github.komikku-app:aniyomi-extensions-lib:13")
    compileOnly("com.squareup.okhttp3:okhttp:4.11.0")
    compileOnly("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.0")
    compileOnly("androidx.preference:preference-ktx:1.2.1")
}

dependencies {
    compileOnly("io.reactivex:rxjava:1.3.8")
    compileOnly("uy.kohesive.injekt:injekt-core:1.16.1")
}
