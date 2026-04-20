import Foundation

struct APIErrorBody: Decodable {
    struct Inner: Decodable {
        let code: String?
        let message: String?
    }
    let error: Inner
}

enum APIError: LocalizedError {
    case transport(Error)
    case invalidResponse
    case server(status: Int, code: String?, message: String?)
    case unauthorized
    case decoding(Error)

    var errorDescription: String? {
        switch self {
        case .transport(let err): return err.localizedDescription
        case .invalidResponse: return "Nieprawidłowa odpowiedź serwera."
        case .server(_, _, let m): return m ?? "Błąd serwera."
        case .unauthorized: return "Sesja wygasła. Zaloguj się ponownie."
        case .decoding: return "Nie udało się odczytać danych."
        }
    }
}
