import Foundation

/// Central async/await HTTP client with token-refresh handling.
actor APIClient {
    private let baseURL: URL
    private let session: URLSession
    private weak var store: SessionStore?

    init(baseURL: URL, session: SessionStore, urlSession: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = urlSession
        self.store = session
    }

    // ────────────── Public helpers ──────────────

    func send<T: Decodable>(_ endpoint: Endpoint, as _: T.Type = T.self) async throws -> T {
        let data = try await sendRaw(endpoint)
        do {
            return try Self.decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func sendVoid(_ endpoint: Endpoint) async throws {
        _ = try await sendRaw(endpoint)
    }

    // ────────────── Core ──────────────

    private func sendRaw(_ endpoint: Endpoint, isRetry: Bool = false) async throws -> Data {
        var comps = URLComponents(url: baseURL.appendingPathComponent(endpoint.path),
                                  resolvingAgainstBaseURL: false)
        if !endpoint.query.isEmpty { comps?.queryItems = endpoint.query }
        guard let url = comps?.url else { throw APIError.invalidResponse }

        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue
        request.setValue(endpoint.contentType, forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if endpoint.requiresAuth, let token = await store?.accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body = endpoint.body {
            request.httpBody = body
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.transport(error)
        }
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }

        if http.statusCode == 401, endpoint.requiresAuth, !isRetry {
            if let refreshed = try? await refresh() {
                await store?.updateTokens(refreshed)
                return try await sendRaw(endpoint, isRetry: true)
            } else {
                await store?.signOut()
                throw APIError.unauthorized
            }
        }

        if (200..<300).contains(http.statusCode) {
            return data
        }

        let body = try? Self.decoder.decode(APIErrorBody.self, from: data)
        throw APIError.server(status: http.statusCode,
                              code: body?.error.code,
                              message: body?.error.message)
    }

    private func refresh() async throws -> TokenPairDTO {
        guard let rt = await store?.refreshToken else { throw APIError.unauthorized }
        let ep = API.refresh(refreshToken: rt)
        let data = try await sendRaw(ep, isRetry: true)
        return try Self.decoder.decode(TokenPairDTO.self, from: data)
    }

    static let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let isoPlain = ISO8601DateFormatter()
        isoPlain.formatOptions = [.withInternetDateTime]
        let dayFmt = DateFormatter()
        dayFmt.dateFormat = "yyyy-MM-dd"
        dayFmt.locale = Locale(identifier: "en_US_POSIX")
        d.dateDecodingStrategy = .custom { dec in
            let c = try dec.singleValueContainer()
            let s = try c.decode(String.self)
            if let date = iso.date(from: s) { return date }
            if let date = isoPlain.date(from: s) { return date }
            if let date = dayFmt.date(from: s) { return date }
            throw DecodingError.dataCorruptedError(in: c, debugDescription: "Unrecognised date \(s)")
        }
        return d
    }()
}
