# App Store release checklist — Spendly

## 1. Apple developer portal

- Enroll in Apple Developer Program (PLN ~ 500 / year) as an **organization**
  (banking apps as individuals get rejected more often)
- Create an **App ID** `com.spendly.app` with capabilities:
  - Associated Domains (optional, if you add universal links later)
  - Keychain Sharing (already default for single-target)
  - No payment / Apple Pay entitlements needed
- Create provisioning profile + distribution certificate

## 2. App Store Connect

- Create new iOS app:
  - Name: **Spendly**
  - Bundle ID: `com.spendly.app`
  - SKU: `spendly-ios-1`
  - Primary category: **Finance**
  - Secondary: **Business**
- Age rating: 4+ (no objectionable content)
- Content rights: you own (or have licensed) the bank logos — GoCardless
  provides logos; review their TOS

## 3. Privacy (critical — banking app)

- **App Privacy → Data Collection**:
  - Financial information (transactions, balances) — *linked to user*
  - Contact info (email, name) — *linked to user*
  - Identifiers (user ID)
  - Usage data (if using analytics)
  - Purposes: **App Functionality** (and **Analytics** if applicable)
  - **Data is NOT used for tracking** (no third-party ad tracking)
- **Privacy policy URL** — required. Publish at `https://spendly.app/privacy`
  and reference PSD2 (GoCardless) processing.
- **Terms of use** — required for auto-renewing subs; nice to have here.
  `https://spendly.app/terms`
- **PSD2 disclosure** inside the app:
  > *"Spendly łączy Twoje konta poprzez licencjonowanego dostawcę PSD2
  > (GoCardless Bank Account Data, UAB). Nigdy nie przechowujemy Twoich
  > danych logowania. Dostęp jest wyłącznie do odczytu i wygasa po 90 dniach."*

## 4. Required UI copy

- On the "Link bank" screen, before redirect, show:
  - Bank name & logo
  - "Zostaniesz przekierowany na stronę banku, gdzie udzielisz zgody PSD2"
  - "Access: read-only, 90 dni, historia do 24 miesięcy"
- Onboarding: explain what Spendly does **before** asking to link a bank

## 5. Review notes (to Apple)

Include in the *"Notes for the reviewer"* field:

```
Spendly is a personal finance manager that aggregates balances and transactions
from Polish banks using the official EU PSD2 Open Banking APIs via a licensed
AISP (GoCardless Bank Account Data, licence by Finansinspekcija LT/LV).
We never store or see bank credentials — users authenticate directly with their
bank inside a Safari-backed ASWebAuthenticationSession.

Test account (pre-configured, demo sandbox bank available in GoCardless):
email:    reviewer@spendly.app
password: SpendlyReview#2026

To verify the bank link flow in sandbox, choose "SANDBOXFINANCE_SFIN0000" as
the bank.
```

## 6. Screenshots

Required sizes (one set covers most modern devices):

- 6.7" (iPhone 16 Pro Max): 1290 × 2796
- 6.5" (iPhone 11 Pro Max fallback): 1242 × 2688
- 5.5" (optional, legacy)
- 12.9" iPad Pro (only if you ship iPad too)

Suggested screens:
1. Dashboard hero (total balance + cashflow chart)
2. Link bank (PL banks list)
3. Transactions with categories
4. Insights (subscriptions, recurring)
5. Budgets & goals

## 7. Common rejection pitfalls for banking apps

- Missing privacy labels → added in §3
- Broken demo credentials → provide working reviewer account
- No explanation of 3rd-party aggregator → provided in §5
- Using `UIWebView` for OAuth redirect → we use `ASWebAuthenticationSession` ✓
- Requesting unneeded permissions → we request none at launch; location/photos
  are not used
- Showing bank data without consent wall → our onboarding explains PSD2 first

## 8. Build & upload

```
cd ios/Spendly
xcodegen generate
xcodebuild -project Spendly.xcodeproj -scheme Spendly \
           -configuration Release -archivePath build/Spendly.xcarchive archive
xcodebuild -exportArchive -archivePath build/Spendly.xcarchive \
           -exportOptionsPlist ExportOptions.plist \
           -exportPath build/
xcrun altool --upload-app --type ios --file build/Spendly.ipa \
             --username YOUR_APPLE_ID --password "@keychain:AC_PASSWORD"
```

Or use Fastlane / Xcode Cloud.

## 9. Phased release

- Submit for review
- Enable **Phased release over 7 days** in App Store Connect
- Monitor Sentry + App Store analytics
