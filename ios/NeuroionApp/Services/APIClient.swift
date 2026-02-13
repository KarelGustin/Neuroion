//
//  APIClient.swift
//  NeuroionApp
//
//  HTTP client for Homebase API. Uses ConnectionManager for configurable base URL.
//

import Foundation

class APIClient {
    static let shared = APIClient()
    
    private let session: URLSession
    
    /// Encoder: camelCase → snake_case for API request bodies
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()
    
    /// Decoder: snake_case → camelCase for API responses
    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()
    
    /// Request timeout (chat/LLM can be slow)
    private static let requestTimeout: TimeInterval = 45
    /// Resource (total) timeout
    private static let resourceTimeout: TimeInterval = 90

    /// Longer timeouts for streaming chat (research etc. can take minutes)
    private static let streamRequestTimeout: TimeInterval = 60
    private static let streamResourceTimeout: TimeInterval = 300

    private let streamSession: URLSession

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = Self.requestTimeout
        config.timeoutIntervalForResource = Self.resourceTimeout
        self.session = URLSession(configuration: config)

        let streamConfig = URLSessionConfiguration.default
        streamConfig.timeoutIntervalForRequest = Self.streamRequestTimeout
        streamConfig.timeoutIntervalForResource = Self.streamResourceTimeout
        self.streamSession = URLSession(configuration: streamConfig)
    }
    
    private var baseURL: String {
        ConnectionManager.shared.effectiveBaseURL
    }
    
    func request<T: Decodable>(
        endpoint: String,
        method: String = "GET",
        body: Encodable? = nil,
        token: String? = nil
    ) async throws -> T {
        let path = endpoint.hasPrefix("/") ? endpoint : "/\(endpoint)"
        guard let url = URL(string: "\(baseURL)\(path)") else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let token = token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        if let body = body {
            request.httpBody = try encoder.encode(body)
        }
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try decoder.decode(T.self, from: data)
    }

    /// Stream Server-Sent Events from an endpoint; yields parsed JSON objects from each "data:" line.
    func streamEvents(
        endpoint: String,
        method: String = "POST",
        body: Encodable? = nil,
        token: String? = nil
    ) async throws -> AsyncThrowingStream<[String: Any], Error> {
        let path = endpoint.hasPrefix("/") ? endpoint : "/\(endpoint)"
        guard let url = URL(string: "\(baseURL)\(path)") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body = body {
            request.httpBody = try encoder.encode(body)
        }

        let (bytes, response) = try await streamSession.bytes(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        return AsyncThrowingStream { continuation in
            Task {
                var buffer = [UInt8]()
                do {
                    for try await byte in bytes {
                        buffer.append(byte)
                        if buffer.suffix(2) == [0x0a, 0x0a] { // \n\n
                            if let str = String(bytes: buffer, encoding: .utf8) {
                                let blocks = str.components(separatedBy: "\n\n")
                                for block in blocks {
                                    let trimmed = block.trimmingCharacters(in: .whitespacesAndNewlines)
                                    if trimmed.hasPrefix("data: ") {
                                        let jsonStr = String(trimmed.dropFirst(6))
                                        if let data = jsonStr.data(using: .utf8),
                                           let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                                            continuation.yield(obj)
                                        }
                                    }
                                }
                            }
                            buffer.removeAll()
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }
}

enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return NSLocalizedString("Ongeldige server-URL.", comment: "API error")
        case .invalidResponse:
            return NSLocalizedString("Geen geldige reactie van de server.", comment: "API error")
        case .httpError(let code):
            if code == 401 {
                return NSLocalizedString("Niet meer ingelogd. Ga naar Instellingen om opnieuw te koppelen.", comment: "API error")
            }
            if code >= 500 {
                return NSLocalizedString("Serverfout. Probeer het later opnieuw.", comment: "API error")
            }
            return String(format: NSLocalizedString("Fout van server (code %d).", comment: "API error"), code)
        }
    }
}
