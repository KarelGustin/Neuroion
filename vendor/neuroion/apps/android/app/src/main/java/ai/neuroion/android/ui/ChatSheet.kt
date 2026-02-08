package ai.neuroion.android.ui

import androidx.compose.runtime.Composable
import ai.neuroion.android.MainViewModel
import ai.neuroion.android.ui.chat.ChatSheetContent

@Composable
fun ChatSheet(viewModel: MainViewModel) {
  ChatSheetContent(viewModel = viewModel)
}
