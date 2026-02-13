//
//  AgendaView.swift
//  NeuroionApp
//
//  In-app agenda: model, API, month view, event list, detail, add/edit.
//  Self-contained so adding this file to the target is sufficient.
//

import Foundation
import SwiftUI

// MARK: - Agenda model and API

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

private func agendaISO8601String(from date: Date) -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime]
    formatter.timeZone = TimeZone(identifier: "UTC")!
    return formatter.string(from: date)
}

enum AgendaService {
    static func listEvents(from start: Date, to end: Date, token: String) async throws -> [AgendaEvent] {
        let startStr = agendaISO8601String(from: start)
        let endStr = agendaISO8601String(from: end)
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
            startAt: agendaISO8601String(from: startAt),
            endAt: agendaISO8601String(from: endAt),
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
            startAt: startAt.map { agendaISO8601String(from: $0) },
            endAt: endAt.map { agendaISO8601String(from: $0) },
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

// MARK: - Main agenda container

struct AgendaView: View {
    @EnvironmentObject var authManager: AuthManager
    @State private var selectedDate = Calendar.current.startOfDay(for: Date())
    @State private var events: [AgendaEvent] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showingAddEvent = false
    @State private var eventToEdit: AgendaEvent?

    private var monthStart: Date {
        let cal = Calendar.current
        let comps = cal.dateComponents([.year, .month], from: selectedDate)
        return cal.date(from: comps) ?? selectedDate
    }

    private var monthEnd: Date {
        let cal = Calendar.current
        return cal.date(byAdding: DateComponents(month: 1, day: -1), to: monthStart) ?? monthStart
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                MonthGridView(
                    selectedDate: $selectedDate,
                    events: events,
                    monthStart: monthStart
                )
                Divider()
                if let err = errorMessage {
                    Text(err)
                        .font(.caption)
                        .foregroundColor(.red)
                        .padding()
                }
                AgendaDayListView(
                    date: selectedDate,
                    events: events.filter { eventOnDay($0, selectedDate) },
                    onSelectEvent: { eventToEdit = $0 },
                    onRefresh: { Task { await loadEvents() } }
                )
                .overlay {
                    if isLoading { ProgressView().scaleEffect(1.2) }
                }
            }
            .navigationTitle("Agenda")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showingAddEvent = true
                    } label: {
                        Image(systemName: "plus.circle.fill")
                    }
                }
            }
            .sheet(isPresented: $showingAddEvent) {
                AgendaEventFormView(
                    initialDate: selectedDate,
                    onSave: { await loadEvents(); showingAddEvent = false },
                    onCancel: { showingAddEvent = false }
                )
                .environmentObject(authManager)
            }
            .sheet(item: $eventToEdit) { event in
                AgendaEventDetailView(
                    event: event,
                    onEdit: { eventToEdit = nil },
                    onDelete: { eventToEdit = nil; Task { await loadEvents() } },
                    onDismiss: { eventToEdit = nil }
                )
                .environmentObject(authManager)
            }
            .task { await loadEvents() }
            .onChange(of: selectedDate) { _, _ in
                Task { await loadEvents() }
            }
        }
    }

    private func loadEvents() async {
        guard let token = authManager.token else { return }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let start = Calendar.current.startOfDay(for: monthStart)
            var end = Calendar.current.date(byAdding: .day, value: 1, to: monthEnd) ?? monthEnd
            end = Calendar.current.date(byAdding: .month, value: 1, to: monthStart) ?? end
            events = try await AgendaService.listEvents(from: start, to: end, token: token)
        } catch {
            errorMessage = error.localizedDescription
            events = []
        }
    }

    private func eventOnDay(_ event: AgendaEvent, _ day: Date) -> Bool {
        let cal = Calendar.current
        let startOfDay = cal.startOfDay(for: day)
        let endOfDay = cal.date(byAdding: .day, value: 1, to: startOfDay)!
        return event.startAt < endOfDay && event.endAt >= startOfDay
    }
}

// MARK: - Month grid

struct MonthGridView: View {
    @Binding var selectedDate: Date
    let events: [AgendaEvent]
    let monthStart: Date

    private let calendar = Calendar.current
    private let weekdaySymbols = ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"]

    private var weeks: [[Date?]] {
        var result: [[Date?]] = []
        let range = calendar.range(of: .day, in: .month, for: monthStart)!
        let firstWeekday = calendar.component(.weekday, from: monthStart)
        let pad = (firstWeekday + 5) % 7
        var row: [Date?] = Array(repeating: nil, count: pad)
        for day in range {
            if let d = calendar.date(bySetting: .day, value: day, of: monthStart) {
                row.append(d)
                if row.count == 7 {
                    result.append(row)
                    row = []
                }
            }
        }
        if !row.isEmpty {
            while row.count < 7 { row.append(nil) }
            result.append(row)
        }
        return result
    }

    private func hasEvent(on date: Date?) -> Bool {
        guard let d = date else { return false }
        return events.contains { event in
            calendar.isDate(d, inSameDayAs: event.startAt) ||
            calendar.isDate(d, inSameDayAs: event.endAt) ||
            (event.startAt < calendar.startOfDay(for: d) && event.endAt > calendar.date(byAdding: .day, value: 1, to: calendar.startOfDay(for: d))!)
        }
    }

    var body: some View {
        VStack(spacing: 8) {
            Text(monthYearString(monthStart))
                .font(.headline)
            HStack(spacing: 4) {
                ForEach(weekdaySymbols, id: \.self) { s in
                    Text(s).frame(maxWidth: .infinity).font(.caption2).foregroundColor(.secondary)
                }
            }
            ForEach(Array(weeks.enumerated()), id: \.offset) { _, row in
                HStack(spacing: 4) {
                    ForEach(Array(row.enumerated()), id: \.offset) { _, d in
                        DayCell(
                            date: d,
                            isSelected: d.map { calendar.isDate($0, inSameDayAs: selectedDate) } ?? false,
                            hasEvent: hasEvent(on: d),
                            action: { if let d = d { selectedDate = d } }
                        )
                    }
                }
            }
        }
        .padding()
    }

    private func monthYearString(_ d: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "MMMM yyyy"
        f.locale = Locale(identifier: "nl_NL")
        return f.string(from: d)
    }
}

struct DayCell: View {
    let date: Date?
    let isSelected: Bool
    let hasEvent: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack {
                if let d = date {
                    Text("\(Calendar.current.component(.day, from: d))")
                        .font(.system(size: 14, weight: isSelected ? .semibold : .regular))
                        .frame(width: 32, height: 32)
                        .background(isSelected ? Color.accentColor : Color.clear)
                        .foregroundColor(isSelected ? .white : .primary)
                        .clipShape(Circle())
                    if hasEvent && !isSelected {
                        Circle()
                            .fill(Color.accentColor)
                            .frame(width: 4, height: 4)
                            .offset(y: 12)
                    }
                } else {
                    Color.clear.frame(width: 32, height: 32)
                }
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Day event list

struct AgendaDayListView: View {
    let date: Date
    let events: [AgendaEvent]
    let onSelectEvent: (AgendaEvent) -> Void
    let onRefresh: () -> Void

    private static let timeFormatter: DateFormatter = {
        let f = DateFormatter()
        f.timeStyle = .short
        return f
    }()

    var body: some View {
        List {
            Section {
                ForEach(events.sorted(by: { $0.startAt < $1.startAt })) { event in
                    Button {
                        onSelectEvent(event)
                    } label: {
                        HStack(alignment: .top) {
                            if event.allDay {
                                Text("Hele dag")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                    .frame(width: 50, alignment: .leading)
                            } else {
                                Text(Self.timeFormatter.string(from: event.startAt))
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                    .frame(width: 50, alignment: .leading)
                            }
                            VStack(alignment: .leading, spacing: 2) {
                                Text(event.title)
                                    .font(.body)
                                if let n = event.notes, !n.isEmpty {
                                    Text(n)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                        .lineLimit(2)
                                }
                            }
                            Spacer()
                        }
                        .padding(.vertical, 4)
                    }
                }
            } header: {
                Text(dayHeaderString(date))
            }
        }
        .listStyle(.insetGrouped)
        .refreshable { await MainActor.run { onRefresh() } }
    }

    private func dayHeaderString(_ d: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "EEEE d MMMM"
        f.locale = Locale(identifier: "nl_NL")
        return f.string(from: d)
    }
}

// MARK: - Event detail

struct AgendaEventDetailView: View {
    let event: AgendaEvent
    let onEdit: () -> Void
    let onDelete: () -> Void
    let onDismiss: () -> Void
    @EnvironmentObject var authManager: AuthManager
    @State private var showDeleteConfirm = false
    @State private var showEditForm = false

    private static let dateTimeFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateStyle = .medium
        f.timeStyle = .short
        f.locale = Locale(identifier: "nl_NL")
        return f
    }()

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text(event.title)
                        .font(.headline)
                    if event.allDay {
                        Text("Hele dag")
                        Text(Self.dateTimeFormatter.string(from: event.startAt))
                            .font(.caption)
                            .foregroundColor(.secondary)
                    } else {
                        Text(Self.dateTimeFormatter.string(from: event.startAt))
                        Text(Self.dateTimeFormatter.string(from: event.endAt))
                            .foregroundColor(.secondary)
                    }
                    if let n = event.notes, !n.isEmpty {
                        Text(n)
                            .padding(.top, 4)
                    }
                }
                Section {
                    Button("Bewerken") {
                        showEditForm = true
                    }
                    Button("Verwijderen", role: .destructive) {
                        showDeleteConfirm = true
                    }
                }
            }
            .navigationTitle("Afspraak")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Sluiten") { onDismiss() }
                }
            }
            .confirmationDialog("Verwijderen?", isPresented: $showDeleteConfirm) {
                Button("Verwijder", role: .destructive) {
                    Task {
                        await deleteEvent()
                    }
                }
            } message: {
                Text("Weet je zeker dat je deze afspraak wilt verwijderen?")
            }
            .sheet(isPresented: $showEditForm) {
                AgendaEventFormView(
                    event: event,
                    onSave: { onEdit(); showEditForm = false; onDismiss() },
                    onCancel: { showEditForm = false }
                )
                .environmentObject(authManager)
            }
        }
    }

    private func deleteEvent() async {
        guard let token = authManager.token else { return }
        do {
            try await AgendaService.deleteEvent(id: event.id, token: token)
            onDelete()
        } catch {
            // Could show alert
        }
    }
}

// MARK: - Add / Edit event form

struct AgendaEventFormView: View {
    var event: AgendaEvent?
    let initialDate: Date?
    let onSave: () async -> Void
    let onCancel: () -> Void

    @EnvironmentObject var authManager: AuthManager
    @State private var title: String = ""
    @State private var startDate: Date = Date()
    @State private var endDate: Date = Date().addingTimeInterval(3600)
    @State private var allDay: Bool = false
    @State private var notes: String = ""
    @State private var isSaving = false
    @State private var saveError: String?

    init(event: AgendaEvent? = nil, initialDate: Date? = nil, onSave: @escaping () async -> Void, onCancel: @escaping () -> Void) {
        self.event = event
        self.initialDate = initialDate
        self.onSave = onSave
        self.onCancel = onCancel
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Titel", text: $title)
                    Toggle("Hele dag", isOn: $allDay)
                    if allDay {
                        DatePicker("Start", selection: $startDate, displayedComponents: .date)
                        DatePicker("Einde", selection: $endDate, displayedComponents: .date)
                    } else {
                        DatePicker("Start", selection: $startDate, displayedComponents: [.date, .hourAndMinute])
                        DatePicker("Einde", selection: $endDate, displayedComponents: [.date, .hourAndMinute])
                    }
                    TextField("Notities", text: $notes, axis: .vertical)
                        .lineLimit(3...6)
                }
                if let err = saveError {
                    Section {
                        Text(err).foregroundColor(.red)
                    }
                }
            }
            .navigationTitle(event != nil ? "Bewerken" : "Nieuwe afspraak")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Annuleren") { onCancel() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Opslaan") {
                        Task { await save() }
                    }
                    .disabled(title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSaving)
                }
            }
            .onAppear {
                if let e = event {
                    title = e.title
                    startDate = e.startAt
                    endDate = e.endAt
                    allDay = e.allDay
                    notes = e.notes ?? ""
                } else if let d = initialDate {
                    startDate = d
                    endDate = Calendar.current.date(byAdding: .hour, value: 1, to: d) ?? d
                }
            }
        }
    }

    private func save() async {
        guard let token = authManager.token else { return }
        let t = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return }
        if endDate <= startDate {
            saveError = "Einde moet na start zijn."
            return
        }
        isSaving = true
        saveError = nil
        defer { isSaving = false }
        do {
            if let e = event {
                _ = try await AgendaService.updateEvent(
                    id: e.id,
                    title: t,
                    startAt: startDate,
                    endAt: endDate,
                    allDay: allDay,
                    notes: notes.isEmpty ? nil : notes,
                    token: token
                )
            } else {
                _ = try await AgendaService.createEvent(
                    title: t,
                    startAt: startDate,
                    endAt: endDate,
                    allDay: allDay,
                    notes: notes.isEmpty ? nil : notes,
                    token: token
                )
            }
            await onSave()
        } catch {
            saveError = error.localizedDescription
        }
    }
}
