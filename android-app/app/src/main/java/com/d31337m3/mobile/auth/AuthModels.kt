package com.d31337m3.mobile.auth

data class AuthUser(
    val id: String,
    val email: String,
    val name: String,
    val isAdmin: Boolean,
    val planId: String? = null,
    val subscriptionStatus: String? = null,
)

data class AuthSession(
    val token: String,
    val user: AuthUser,
) {
    val isStaff: Boolean
        get() = user.isAdmin || user.email.endsWith("@d31337m3.com", ignoreCase = true)
}
