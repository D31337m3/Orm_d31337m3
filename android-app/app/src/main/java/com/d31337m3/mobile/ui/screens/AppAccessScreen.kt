package com.d31337m3.mobile.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

@Composable
fun AppAccessScreen(
    isLoading: Boolean,
    errorMessage: String?,
    onSignIn: (String, String) -> Unit,
) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("D31337m3 Mobile", fontWeight = FontWeight.Bold)
                Text("Sign in with your customer email or staff email to open the correct shell.")
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    modifier = Modifier.fillMaxWidth(),
                    leadingIcon = { androidx.compose.material3.Icon(Icons.Default.Person, contentDescription = null) },
                    label = { Text("Email address") },
                    placeholder = { Text("you@domain.com") },
                    singleLine = true,
                )
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    modifier = Modifier.fillMaxWidth(),
                    leadingIcon = { androidx.compose.material3.Icon(Icons.Default.Lock, contentDescription = null) },
                    label = { Text("Password") },
                    placeholder = { Text("Enter your password") },
                    singleLine = true,
                )
                Button(
                    onClick = { if (email.isNotBlank() && password.isNotBlank()) onSignIn(email, password) },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = email.contains("@") && password.isNotBlank() && !isLoading,
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(modifier = Modifier.padding(end = 10.dp))
                    } else {
                        androidx.compose.material3.Icon(Icons.Default.Lock, contentDescription = null)
                    }
                    Text(if (isLoading) "Signing in" else "Continue", modifier = Modifier.padding(start = 8.dp))
                }
                if (!errorMessage.isNullOrBlank()) {
                    Text(errorMessage, color = androidx.compose.ui.graphics.Color(0xFFFF6B6B))
                }
            }
        }

        Text(
            text = "Staff email domain: @d31337m3.com",
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center,
        )
    }
}
