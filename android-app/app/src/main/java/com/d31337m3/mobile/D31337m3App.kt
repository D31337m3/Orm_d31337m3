package com.d31337m3.mobile

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import com.d31337m3.mobile.auth.AuthSession
import com.d31337m3.mobile.auth.BackendAuthRepository
import com.d31337m3.mobile.ui.screens.AppAccessScreen
import com.d31337m3.mobile.ui.screens.CustomerDashboardScreen
import com.d31337m3.mobile.ui.screens.StaffDashboardScreen
import com.d31337m3.mobile.ui.theme.D31337m3Theme
import kotlinx.coroutines.launch

@Composable
fun D31337m3App() {
    val context = LocalContext.current
    val authRepository = remember(context) { BackendAuthRepository(context) }
    val coroutineScope = rememberCoroutineScope()
    var session by remember { mutableStateOf<AuthSession?>(null) }
    var loading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(authRepository) {
        loading = true
        session = runCatching { authRepository.restoreSession() }.getOrNull()
        loading = false
    }

    fun signIn(email: String, password: String) {
        coroutineScope.launch {
            loading = true
            errorMessage = null
            val result = runCatching { authRepository.login(email, password) }
            session = result.getOrNull()
            errorMessage = result.exceptionOrNull()?.message
            loading = false
        }
    }

    fun signOut() {
        coroutineScope.launch {
            authRepository.signOut()
            session = null
            errorMessage = null
        }
    }

    D31337m3Theme {
        Surface(color = MaterialTheme.colorScheme.background) {
            if (loading && session == null) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else if (session == null) {
                AppAccessScreen(
                    isLoading = loading,
                    errorMessage = errorMessage,
                    onSignIn = ::signIn,
                )
            } else {
                if (session!!.isStaff) {
                    StaffDashboardScreen(
                        email = session!!.user.email,
                        onSignOut = ::signOut,
                    )
                } else {
                    CustomerDashboardScreen(
                        email = session!!.user.email,
                        onSignOut = ::signOut,
                    )
                }
            }
        }
    }
}
