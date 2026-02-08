package ai.neuroion.android.protocol

import org.junit.Assert.assertEquals
import org.junit.Test

class NeuroionProtocolConstantsTest {
  @Test
  fun canvasCommandsUseStableStrings() {
    assertEquals("canvas.present", NeuroionCanvasCommand.Present.rawValue)
    assertEquals("canvas.hide", NeuroionCanvasCommand.Hide.rawValue)
    assertEquals("canvas.navigate", NeuroionCanvasCommand.Navigate.rawValue)
    assertEquals("canvas.eval", NeuroionCanvasCommand.Eval.rawValue)
    assertEquals("canvas.snapshot", NeuroionCanvasCommand.Snapshot.rawValue)
  }

  @Test
  fun a2uiCommandsUseStableStrings() {
    assertEquals("canvas.a2ui.push", NeuroionCanvasA2UICommand.Push.rawValue)
    assertEquals("canvas.a2ui.pushJSONL", NeuroionCanvasA2UICommand.PushJSONL.rawValue)
    assertEquals("canvas.a2ui.reset", NeuroionCanvasA2UICommand.Reset.rawValue)
  }

  @Test
  fun capabilitiesUseStableStrings() {
    assertEquals("canvas", NeuroionCapability.Canvas.rawValue)
    assertEquals("camera", NeuroionCapability.Camera.rawValue)
    assertEquals("screen", NeuroionCapability.Screen.rawValue)
    assertEquals("voiceWake", NeuroionCapability.VoiceWake.rawValue)
  }

  @Test
  fun screenCommandsUseStableStrings() {
    assertEquals("screen.record", NeuroionScreenCommand.Record.rawValue)
  }
}
