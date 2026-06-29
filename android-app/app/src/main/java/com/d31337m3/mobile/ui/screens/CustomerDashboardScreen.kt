package com.d31337m3.mobile.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

private enum class CustomerSection(val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector) {
    Dashboard("Dashboard", Icons.Default.Dashboard),
    Findings("Findings", Icons.Default.Bolt),
    Support("Support", Icons.Default.ChatBubbleOutline),
    Billing("Billing", Icons.Default.AccountBalanceWallet),
    Help("Help", Icons.Default.HelpOutline),
}

@Composable
fun CustomerDashboardScreen(email: String, onSignOut: () -> Unit) {
    var selectedSection by remember { mutableIntStateOf(0) }
    val section = CustomerSection.entries[selectedSection]

    Scaffold(
        bottomBar = {
            NavigationBar(containerColor = Color(0xFF080808)) {
                CustomerSection.entries.forEachIndexed { index, entry ->
                    NavigationBarItem(
                        selected = selectedSection == index,
                        onClick = { selectedSection = index },
                        icon = { Icon(entry.icon, contentDescription = entry.label) },
                        label = { Text(entry.label) },
                    )
                }
            }
        },
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF111111)),
                shape = RoundedCornerShape(24.dp),
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text("D31337m3 Customer", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                            Text(email, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Surface(
                            color = Color(0xFF1A1A1A),
                            shape = RoundedCornerShape(999.dp),
                        ) {
                            Text(
                                text = "Customer",
                                modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                                color = Color(0xFFFF4FD8),
                                fontWeight = FontWeight.Bold,
                            )
                        }
                    }

                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        AssistChip(onClick = { }, label = { Text("87 score") }, leadingIcon = {
                            Icon(Icons.Default.Security, contentDescription = null)
                        })
                        AssistChip(onClick = { }, label = { Text("4 alerts") }, leadingIcon = {
                            Icon(Icons.Default.Favorite, contentDescription = null)
                        })
                        AssistChip(onClick = { }, label = { Text("2 open chats") }, leadingIcon = {
                            Icon(Icons.Default.ChatBubbleOutline, contentDescription = null)
                        })
                    }

                    Text(
                        text = "Track brokers, watch your reputation score, open support chats, and manage billing from one mobile view.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )

                    Button(onClick = onSignOut) {
                        Text("Sign out")
                    }
                }
            }

            TabRow(selectedTabIndex = selectedSection) {
                CustomerSection.entries.forEachIndexed { index, entry ->
                    Tab(
                        selected = selectedSection == index,
                        onClick = { selectedSection = index },
                        text = { Text(entry.label) },
                        icon = { Icon(entry.icon, contentDescription = entry.label) },
                    )
                }
            }

            when (section) {
                CustomerSection.Dashboard -> DashboardContent()
                CustomerSection.Findings -> FindingsContent()
                CustomerSection.Support -> SupportContent()
                CustomerSection.Billing -> BillingContent()
                CustomerSection.Help -> HelpContent()
            }

            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Mobile-first customer dashboard scaffold. Wire this to the orchestrator APIs next.",
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun DashboardContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        StatCard(title = "Reputation score", value = "87 / 100", caption = "Trending up 6 points this week", accent = Color(0xFF00FF41))
        StatCard(title = "Active brokers", value = "15+", caption = "Spokeo, Whitepages, Intelius, Google, Bing", accent = Color(0xFFFF4FD8))
        StatCard(title = "Next scan", value = "In 14 min", caption = "Daily scan cadence on Pro plan", accent = Color(0xFF8A8AFF))
    }
}

@Composable
private fun FindingsContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        FindingCard("Spokeo", "Removed", "Profile link cleared and cached result expired", Color(0xFF00FF41))
        FindingCard("Whitepages", "Pending", "Removal request submitted and awaiting broker review", Color(0xFFFFD166))
        FindingCard("Google", "Monitoring", "Indexed page detected in search results", Color(0xFFFF4FD8))
    }
}

@Composable
private fun SupportContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SupportThreadCard("Live chat", "Support agent replied 12 min ago", "We’ve escalated the Whitepages removal follow-up.")
        SupportThreadCard("Ticket #1842", "High priority", "Customer requested a faster turnaround on the Google de-indexing request.")
        OutlinedButton(onClick = { }, modifier = Modifier.fillMaxWidth()) {
            Text("Open new support chat")
        }
    }
}

@Composable
private fun BillingContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        StatCard(title = "Current plan", value = "Pro", caption = "$79 / month", accent = Color(0xFF00FF41))
        StatCard(title = "Discount", value = "75% off", caption = "Applied for your launch window", accent = Color(0xFFFF4FD8))
        StatCard(title = "Next payment", value = "Jul 1", caption = "Auto-renews monthly until cancelled", accent = Color(0xFF8A8AFF))
    }
}

@Composable
private fun HelpContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Quick actions", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text("Open a chat, request a callback, export your privacy report, or review the launch FAQ.")
                HorizontalDivider()
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { }) { Text("Chat support") }
                    OutlinedButton(onClick = { }) { Text("Export report") }
                }
            }
        }
    }
}

@Composable
private fun StatCard(title: String, value: String, caption: String, accent: Color) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(value, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
                BoxAccent(accent)
            }
            Text(caption, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun FindingCard(source: String, status: String, description: String, accent: Color) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(source, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(status, color = accent, fontWeight = FontWeight.Bold)
            }
            Text(description, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun SupportThreadCard(title: String, meta: String, message: String) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(meta, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(message)
        }
    }
}

@Composable
private fun BoxAccent(accent: Color) {
    Spacer(
        modifier = Modifier
            .size(width = 28.dp, height = 10.dp)
            .clip(RoundedCornerShape(999.dp))
            .background(accent),
    )
}
