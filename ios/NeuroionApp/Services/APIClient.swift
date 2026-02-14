//
//  APIClient.swift
//  NeuroionApp
//
//  HTTP client for Homebase API. Uses ConnectionManager for configurable base URL.
//  Certificate pinning for host 10.66.66.1 (VPN) when a pin is set.
//

import CryptoKit
import Foundation
import Security

/// Host that uses certificate pinning when a pin is configured (VPN base URL).
private let pinnedHost = "10.66.66.1"
private let pinnedPublicKeyHashKey = "neuroion_vpn_pinned_public_key_hash"

/// Optional: set to base64-encoded SHA-256 of the server cert's public key (SPKI) to pin 10.66.66.1. If nil, 10.66.66.1 is trusted with default validation (for dev/self-signed).
func getVPNCertificatePin() -> Data? {
    guard let b64 = UserDefaults.standard.string(forKey: pinnedPublicKeyHashKey), !b64.isEmpty,
          let data = Data(base64Encoded: b64) else { return nil }
    return data
}

func setVPNCertificatePin(_ hash: Data?) {
    if let hash = hash {
        UserDefaults.standard.set(hash.base64EncodedString(), forKey: pinnedPublicKeyHashKey)
    } else {
        UserDefaults.standard.removeObject(forKey: pinnedPublicKeyHashKey)
    }
}

private final class CertificatePinningDelegate: NSObject, URLSessionDelegate {
    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard challenge.protectionSpace.host == pinnedHost,
              challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let serverTrust = challenge.protectionSpace.serverTrust else {
            completionHandler(.performDefaultHandling, nil)
            return
        }
        if let pin = getVPNCertificatePin() {
            guard SecTrustGetCertificateCount(serverTrust) > 0,
                  let cert = SecTrustGetCertificateAtIndex(serverTrust, 0) else {
                completionHandler(.cancelAuthenticationChallenge, nil)
                return
            }
            let key = SecCertificateCopyKey(cert)
            guard let key = key else {
                completionHandler(.cancelAuthenticationChallenge, nil)
                return
            }
            guard let keyData = SecKeyCopyExternalRepresentation(key, nil) as Data? else {
                completionHandler(.cancelAuthenticationChallenge, nil)
                return
            }
            let hash = Data(SHA256.hash(data: keyData))
            if hash == pin {
                completionHandler(.useCredential, URLCredential(trust: serverTrust))
            } else {
                completionHandler(.cancelAuthenticationChallenge, nil)
            }
        } else {
            completionHandler(.useCredential, URLCredential(trust: serverTrust))
        }
    }
}

class APIClient {
    static let shared = APIClient()
    
    private let pinningDelegate = CertificatePinningDelegate()
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

    /// Longer timeouts for streaming chat (VPN/remote can be slow; context + LLM take time)
    private static let streamRequestTimeout: TimeInterval = 300
    private static let streamResourceTimeout: TimeInterval = 600

    private let streamSession: URLSession

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = Self.requestTimeout
        config.timeoutIntervalForResource = Self.resourceTimeout
        self.session = URLSession(configuration: config, delegate: pinningDelegate, delegateQueue: nil)

        let streamConfig = URLSessionConfiguration.default
        streamConfig.timeoutIntervalForRequest = Self.streamRequestTimeout
        streamConfig.timeoutIntervalForResource = Self.streamResourceTimeout
        self.streamSession = URLSession(configuration: streamConfig, delegate: pinningDelegate, delegateQueue: nil)
    }
    
    private var baseURL: String {
        ConnectionManager.shared.effectiveBaseURL
    }

    private func logConnection(_ path: String) {
        NSLog("[Neuroion] API %@ → %@", path, baseURL)
    }

    func request<T: Decodable>(
        endpoint: String,
        method: String = "GET",
        body: Encodable? = nil,
        token: String? = nil
    ) async throws -> T {
        let path = endpoint.hasPrefix("/") ? endpoint : "/\(endpoint)"
        logConnection(path)
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
    
    /// Request that expects 204 No Content (e.g. DELETE). Does not decode body.
    func requestNoContent(
        endpoint: String,
        method: String = "DELETE",
        body: Encodable? = nil,
        token: String? = nil
    ) async throws {
        let path = endpoint.hasPrefix("/") ? endpoint : "/\(endpoint)"
        logConnection(path)
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
        let (_, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
    }

    /// Stream Server-Sent Events from an endpoint; yields parsed JSON objects from each "data:" line.
    func streamEvents(
        endpoint: String,
        method: String = "POST",
        body: Encodable? = nil,
        token: String? = nil
    ) async throws -> AsyncThrowingStream<[String: Any], Error> {
        let path = endpoint.hasPrefix("/") ? endpoint : "/\(endpoint)"
        logConnection(path)
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
