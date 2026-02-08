import Foundation

public enum NeuroionCameraCommand: String, Codable, Sendable {
    case list = "camera.list"
    case snap = "camera.snap"
    case clip = "camera.clip"
}

public enum NeuroionCameraFacing: String, Codable, Sendable {
    case back
    case front
}

public enum NeuroionCameraImageFormat: String, Codable, Sendable {
    case jpg
    case jpeg
}

public enum NeuroionCameraVideoFormat: String, Codable, Sendable {
    case mp4
}

public struct NeuroionCameraSnapParams: Codable, Sendable, Equatable {
    public var facing: NeuroionCameraFacing?
    public var maxWidth: Int?
    public var quality: Double?
    public var format: NeuroionCameraImageFormat?
    public var deviceId: String?
    public var delayMs: Int?

    public init(
        facing: NeuroionCameraFacing? = nil,
        maxWidth: Int? = nil,
        quality: Double? = nil,
        format: NeuroionCameraImageFormat? = nil,
        deviceId: String? = nil,
        delayMs: Int? = nil)
    {
        self.facing = facing
        self.maxWidth = maxWidth
        self.quality = quality
        self.format = format
        self.deviceId = deviceId
        self.delayMs = delayMs
    }
}

public struct NeuroionCameraClipParams: Codable, Sendable, Equatable {
    public var facing: NeuroionCameraFacing?
    public var durationMs: Int?
    public var includeAudio: Bool?
    public var format: NeuroionCameraVideoFormat?
    public var deviceId: String?

    public init(
        facing: NeuroionCameraFacing? = nil,
        durationMs: Int? = nil,
        includeAudio: Bool? = nil,
        format: NeuroionCameraVideoFormat? = nil,
        deviceId: String? = nil)
    {
        self.facing = facing
        self.durationMs = durationMs
        self.includeAudio = includeAudio
        self.format = format
        self.deviceId = deviceId
    }
}
