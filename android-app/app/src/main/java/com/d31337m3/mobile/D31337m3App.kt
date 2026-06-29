package com.d31337m3.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import com.d31337m3.mobile.ui.screens.LaunchScreen
import com.d31337m3.mobile.ui.theme.D31337m3Theme

@Composable
fun D31337m3App() {
    D31337m3Theme {
        Surface(color = MaterialTheme.colorScheme.background) {
            LaunchScreen()
        }
    }
}
