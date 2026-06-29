package com.d31337m3.mobile.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Assignment
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
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

private enum class StaffSection(val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector) {
    Overview("Overview", Icons.Default.Dashboard),
    Support("Support", Icons.Default.ChatBubbleOutline),
    Workforce("Workforce", Icons.Default.Groups),
    Operations("Operations", Icons.Default.Build),
    Audit("Audit", Icons.Default.Assignment),
}

@Composable
fun StaffDashboardScreen(email: String, onSignOut: () -> Unit) {
    var selectedSection by remember { mutableIntStateOf(0) }
    val section = StaffSection.entries[selectedSection]

    Scaffold(
        bottomBar = {
            NavigationBar(containerColor = Color(0xFF0B0B0B)) {
                StaffSection.entries.forEachIndexed { index, entry ->
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
                            Text("D31337m3 Staff", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                            Text(email, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Surface(
                            color = Color(0xFF1A1A1A),
                            shape = RoundedCornerShape(999.dp),
                        ) {
                            Text(
                                text = "Staff",
                                modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                                color = Color(0xFF00FF41),
                                fontWeight = FontWeight.Bold,
                            )
                        }
                    }

                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        AssistChip(onClick = { }, label = { Text("8 live chats") }, leadingIcon = {
                            Icon(Icons.Default.ChatBubbleOutline, contentDescription = null)
                        })
                        AssistChip(onClick = { }, label = { Text("14 shifts") }, leadingIcon = {
                            Icon(Icons.Default.Groups, contentDescription = null)
                        })
                        AssistChip(onClick = { }, label = { Text("3 ops alerts") }, leadingIcon = {
                            Icon(Icons.Default.Shield, contentDescription = null)
                        })
                    }

                    Text(
                        text = "Use the staff shell for support, workforce, operations, and audit actions.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )

                    Button(onClick = onSignOut) {
                        Text("Sign out")
                    }
                }
            }

            TabRow(selectedTabIndex = selectedSection) {
                StaffSection.entries.forEachIndexed { index, entry ->
                    Tab(
                        selected = selectedSection == index,
                        onClick = { selectedSection = index },
                        text = { Text(entry.label) },
                        icon = { Icon(entry.icon, contentDescription = entry.label) },
                    )
                }
            }

            when (section) {
                StaffSection.Overview -> StaffOverviewContent()
                StaffSection.Support -> StaffSupportContent()
                StaffSection.Workforce -> StaffWorkforceContent()
                StaffSection.Operations -> StaffOperationsContent()
                StaffSection.Audit -> StaffAuditContent()
            }

            Text(
                text = "Staff shell appears only for @d31337m3.com logins.",
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun StaffOverviewContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        StaffStatCard("Service health", "All green", "Orchestrator and core services healthy", Color(0xFF00FF41))
        StaffStatCard("Open tickets", "23", "12 customer support tickets need review", Color(0xFFFF4FD8))
        StaffStatCard("Payroll batch", "Draft", "Next run queued for approval", Color(0xFF8A8AFF))
    }
}

@Composable
private fun StaffSupportContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        StaffListCard("Customer chat queue", listOf("chat-1091: Whitepages removal follow-up", "chat-1092: billing question", "chat-1093: urgent support escalation"))
        StaffListCard("Linked tickets", listOf("#1842 waiting on reply", "#1848 escalated to Tier 2", "#1850 awaiting customer confirmation"))
    }
}

@Composable
private fun StaffWorkforceContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        StaffStatCard("Shifts today", "14", "6 active agents on duty", Color(0xFF00FF41))
        StaffStatCard("Timesheets", "5 pending", "Approvals waiting for payroll review", Color(0xFFFFD166))
        StaffStatCard("Payroll", "Review", "Export draft before cutoff", Color(0xFFFF4FD8))
    }
}

@Composable
private fun StaffOperationsContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        StaffStatCard("Restart control", "Enabled", "Admin host controls available", Color(0xFF00FF41))
        StaffStatCard("Last reboot", "4 days ago", "Physical host reboot is locked behind confirmation", Color(0xFFFFD166))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { }) { Text("Restart service") }
            Button(onClick = { }) { Text("Restart all") }
        }
    }
}

@Composable
private fun StaffAuditContent() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        StaffListCard("Latest audit events", listOf("support reply sent", "shift approved", "billing override denied"))
    }
}

@Composable
private fun StaffStatCard(title: String, value: String, caption: String, accent: Color) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(value, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
                Spacer(
                    modifier = Modifier
                        .size(width = 28.dp, height = 10.dp)
                        .clip(RoundedCornerShape(999.dp))
                        .background(accent),
                )
            }
            Text(caption, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun StaffListCard(title: String, items: List<String>) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            items.forEach { item ->
                Text("• $item", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
