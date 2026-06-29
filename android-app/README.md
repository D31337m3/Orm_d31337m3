# D31337m3 Android Customer Dashboard

This folder is a starter Android project scaffold for the customer-facing mobile app.

## Included
- Kotlin + Jetpack Compose starter structure
- App shell entry point
- Customer/staff dashboard shells
- Compose theme files
- Gradle build files for Android Studio
- Gradle wrapper (`./gradlew`)

## Planned modules
- `feature-dashboard` for reputation, scan status, and account summary
- `feature-findings` for broker alerts and removal tracking
- `feature-support` for chat and tickets
- `feature-billing` for plan, invoices, and renewals
- `core-network` for authenticated API calls
- `core-auth` for token/session storage

## Next steps
1. Open this folder in Android Studio.
2. Sync Gradle.
3. Run `./gradlew build` on a machine with Java and the Android SDK.
4. Connect the app to the customer-facing orchestrator API.

## Notes
- This scaffold is intentionally small and easy to extend.
- The production plan and service surface are documented in `docs/android_admin_app_and_ops_services.md`.