//
//  AgendaEvent.swift
//  NeuroionApp
//
//  Agenda/calendar event model and API.
//

import Foundation

struct AgendaEvent: Codable, Identifiable {
    let id: Int
    let title: String
    let startAt: Date
    let endAt: Date
    let allDay: Bool
    let notes: String?
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id, title, allDay, notes
        case startAt = "start_at"
        case endAt = "end_at"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(Int.self, forKey: .id)
        title = try c.decode(String.self, forKey: .title)
        allDay = try c.decodeIfPresent(Bool.self, forKey: .allDay) ?? false
        notes = try c.decodeIfPresent(String.self, forKey: .notes)
        createdAt = try Self.decodeISO8601(c, key: .createdAt)
        updatedAt = try Self.decodeISO8601(c, key: .updatedAt)
        startAt = try Self.decodeISO8601(c, key: .startAt)
        endAt = try Self.decodeISO8601(c, key: .endAt)
    }

    private static let iso8601Formatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static let iso8601NoFraction: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    private static func decodeISO8601(_ c: KeyedDecodingContainer<CodingKeys>, key: CodingKeys) throws -> Date {
        let str = try c.decode(String.self, forKey: key)
        if let d = iso8601Formatter.date(from: str) ?? iso8601NoFraction.date(from: str) {
            return d
        }
        if str.count <= 10, let d = ISO8601DateFormatter().date(from: str + "T00:00:00Z") {
            return d
        }
        throw DecodingError.dataCorruptedError(forKey: key, in: c, debugDescription: "Invalid date: \(str)")
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(id, forKey: .id)
        try c.encode(title, forKey: .title)
        try c.encode(startAt, forKey: .startAt)
        try c.encode(endAt, forKey: .endAt)
        try c.encode(allDay, forKey: .allDay)
        try c.encodeIfPresent(notes, forKey: .notes)
        try c.encode(createdAt, forKey: .createdAt)
        try c.encode(updatedAt, forKey: .updatedAt)
    }

    init(id: Int, title: String, startAt: Date, endAt: Date, allDay: Bool, notes: String?, createdAt: Date, updatedAt: Date) {
        self.id = id
        self.title = title
        self.startAt = startAt
        self.endAt = endAt
        self.allDay = allDay
        self.notes = notes
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

struct AgendaListResponse: Codable {
    let events: [AgendaEvent]
}

struct CreateAgendaEventRequest: Codable {
    let title: String
    let startAt: String
    let endAt: String
    let allDay: Bool
    let notes: String?

    enum CodingKeys: String, CodingKey {
        case title, allDay, notes
        case startAt = "start_at"
        case endAt = "end_at"
    }
}

struct UpdateAgendaEventRequest: Codable {
    let title: String?
    let startAt: String?
    let endAt: String?
    let allDay: Bool?
    let notes: String?

    enum CodingKeys: String, CodingKey {
        case title, allDay, notes
        case startAt = "start_at"
        case endAt = "end_at"
    }
}

private func iso8601String(from date: Date) -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime]
    formatter.timeZone = TimeZone(identifier: "UTC")!
    return formatter.string(from: date)
}

// MARK: - Agenda API

enum AgendaService {
    static func listEvents(from start: Date, to end: Date, token: String) async throws -> [AgendaEvent] {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        formatter.timeZone = TimeZone(identifier: "UTC")!
        let startStr = formatter.string(from: start)
        let endStr = formatter.string(from: end)
        let endpoint = "/agenda?start=\(startStr.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? startStr)&end=\(endStr.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? endStr)"
        let response: AgendaListResponse = try await APIClient.shared.request(
            endpoint: endpoint,
            method: "GET",
            token: token
        )
        return response.events
    }

    static func getEvent(id: Int, token: String) async throws -> AgendaEvent {
        try await APIClient.shared.request(
            endpoint: "/agenda/\(id)",
            method: "GET",
            token: token
        )
    }

    static func createEvent(title: String, startAt: Date, endAt: Date, allDay: Bool, notes: String?, token: String) async throws -> AgendaEvent {
        let body = CreateAgendaEventRequest(
            title: title,
            startAt: iso8601String(from: startAt),
            endAt: iso8601String(from: endAt),
            allDay: allDay,
            notes: notes
        )
        return try await APIClient.shared.request(
            endpoint: "/agenda",
            method: "POST",
            body: body,
            token: token
        )
    }

    static func updateEvent(id: Int, title: String?, startAt: Date?, endAt: Date?, allDay: Bool?, notes: String?, token: String) async throws -> AgendaEvent {
        let body = UpdateAgendaEventRequest(
            title: title,
            startAt: startAt.map { iso8601String(from: $0) },
            endAt: endAt.map { iso8601String(from: $0) },
            allDay: allDay,
            notes: notes
        )
        return try await APIClient.shared.request(
            endpoint: "/agenda/\(id)",
            method: "PATCH",
            body: body,
            token: token
        )
    }

    static func deleteEvent(id: Int, token: String) async throws {
        try await APIClient.shared.requestNoContent(
            endpoint: "/agenda/\(id)",
            method: "DELETE",
            token: token
        )
    }
}
