import Foundation

/// VoxPocket 预定义的遥测事件名称
///
/// 将 VoxPocket 特有的业务事件命名集中在此处，
/// 避免字符串字面量散落在各业务层。
/// 使用时直接引用 `TelemetryEventName.recordingStarted` 等。
public enum TelemetryEventName: String, Sendable {
    // 录音相关
    case recordingStarted = "recording.started"
    case recordingStopped = "recording.stopped"
    case recordingDuration = "recording.duration"

    // 转录相关
    case transcriptionCompleted = "transcription.completed"
    case transcriptionFailed = "transcription.failed"
    case whisperModelLoaded = "whisper.model.loaded"
    case whisperModelLoadFailed = "whisper.model.load_failed"

    // LLM 相关
    case refinementStarted = "refinement.started"
    case refinementCompleted = "refinement.completed"
    case refinementFailed = "refinement.failed"

    // 历史相关
    case undoPerformed = "history.undo"
    case redoPerformed = "history.redo"

    // 会话相关
    case sessionCreated = "session.created"
    case sessionDeleted = "session.deleted"
}
