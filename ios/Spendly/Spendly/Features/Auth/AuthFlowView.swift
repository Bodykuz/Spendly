import SwiftUI

struct AuthFlowView: View {
    @StateObject private var vm = AuthViewModel(
        api: AppEnvironment.shared.api, session: AppEnvironment.shared.session
    )

    var body: some View {
        ZStack {
            LinearGradient(colors: [Color.indigo.opacity(0.25), Color.purple.opacity(0.15)],
                           startPoint: .topLeading, endPoint: .bottomTrailing)
                .ignoresSafeArea()
            ScrollView {
                VStack(spacing: 24) {
                    Spacer(minLength: 40)
                    header
                    form
                    Button { vm.toggleMode() } label: {
                        Text(vm.mode == .signIn
                             ? "Nie masz konta? Zarejestruj się"
                             : "Masz konto? Zaloguj się")
                    }
                    Spacer()
                    disclaimer
                }
                .padding()
            }
        }
    }

    private var header: some View {
        VStack(spacing: 8) {
            ZStack {
                Circle().fill(Color.indigo.gradient)
                    .frame(width: 84, height: 84)
                    .shadow(color: .indigo.opacity(0.4), radius: 18, y: 10)
                Image(systemName: "chart.pie.fill")
                    .font(.system(size: 38, weight: .bold))
                    .foregroundStyle(.white)
            }
            Text("Spendly").font(.largeTitle.bold())
            Text(vm.mode == .signIn ? "Witaj ponownie" : "Stwórz konto, aby zacząć")
                .foregroundStyle(.secondary)
        }
    }

    private var form: some View {
        VStack(spacing: 14) {
            if vm.mode == .signUp {
                TextField("Imię i nazwisko", text: $vm.fullName)
                    .textContentType(.name).textFieldStyle(.roundedBorder)
            }
            TextField("Email", text: $vm.email)
                .keyboardType(.emailAddress).textContentType(.emailAddress)
                .autocapitalization(.none).textFieldStyle(.roundedBorder)
            SecureField("Hasło (min. 8 znaków)", text: $vm.password)
                .textContentType(vm.mode == .signIn ? .password : .newPassword)
                .textFieldStyle(.roundedBorder)
            if let err = vm.errorMessage {
                Text(err).font(.footnote).foregroundStyle(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            Button { Task { await vm.submit() } } label: {
                HStack {
                    if vm.isLoading { ProgressView().tint(.white) }
                    Text(vm.mode == .signIn ? "Zaloguj się" : "Zarejestruj się").bold()
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(vm.canSubmit ? Color.indigo : Color.indigo.opacity(0.3))
                .foregroundStyle(.white)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .disabled(!vm.canSubmit)
        }
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20))
    }

    private var disclaimer: some View {
        Text("Łączymy Twoje banki przez licencjonowanego dostawcę PSD2. Nie przechowujemy Twoich danych logowania.")
            .font(.footnote).foregroundStyle(.secondary)
            .multilineTextAlignment(.center).padding(.horizontal)
    }
}
