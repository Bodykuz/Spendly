import SwiftUI

@main
struct SpendlyApp: App {
    @StateObject private var environment = AppEnvironment.shared

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(environment)
                .environmentObject(environment.session)
                .tint(.indigo)
                .onOpenURL { url in
                    environment.handleDeepLink(url)
                }
        }
    }
}
