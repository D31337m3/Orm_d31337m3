package com.d31337m3.mobile.auth

import android.content.Context
import android.content.SharedPreferences
import com.d31337m3.mobile.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

class BackendAuthRepository(context: Context) {
    private val client = OkHttpClient()
    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val baseUrl = BuildConfig.API_BASE_URL

    suspend fun restoreSession(): AuthSession? = withContext(Dispatchers.IO) {
        val token = prefs.getString(KEY_TOKEN, null) ?: return@withContext null
        val me = fetchCurrentUser(token) ?: run {
            clear()
            return@withContext null
        }
        AuthSession(token = token, user = me)
    }

    suspend fun login(email: String, password: String): AuthSession = withContext(Dispatchers.IO) {
        val response = postJson("$baseUrl/auth/login", JSONObject()
            .put("email", email)
            .put("password", password)
            .toString())
        val token = response.optString("token").ifBlank { response.optString("access_token") }
        if (token.isBlank()) {
            throw IOException("Login response missing token")
        }
        val user = parseUser(response.getJSONObject("user"))
        val session = AuthSession(token = token, user = user)
        save(session)
        session
    }

    suspend fun signOut() = withContext(Dispatchers.IO) {
        clear()
    }

    private fun save(session: AuthSession) {
        prefs.edit()
            .putString(KEY_TOKEN, session.token)
            .putString(KEY_EMAIL, session.user.email)
            .apply()
    }

    private fun clear() {
        prefs.edit().clear().apply()
    }

    private fun fetchCurrentUser(token: String): AuthUser? {
        val request = Request.Builder()
            .url("$baseUrl/auth/me")
            .header("Authorization", "Bearer $token")
            .get()
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) return null
            val body = response.body?.string().orEmpty()
            if (body.isBlank()) return null
            val root = JSONObject(body)
            return parseUser(root.getJSONObject("user"))
        }
    }

    private fun postJson(url: String, json: String): JSONObject {
        val requestBody = json.toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()
        client.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IOException(parseErrorMessage(body, response.code))
            }
            return if (body.isBlank()) JSONObject() else JSONObject(body)
        }
    }

    private fun parseUser(json: JSONObject): AuthUser {
        return AuthUser(
            id = json.optString("id"),
            email = json.optString("email"),
            name = json.optString("name", json.optString("email")),
            isAdmin = json.optBoolean("is_admin") || json.optBoolean("isAdmin"),
            planId = json.optString("plan_id").takeIf { it.isNotBlank() },
            subscriptionStatus = json.optString("subscription_status").takeIf { it.isNotBlank() },
        )
    }

    private fun parseErrorMessage(body: String, fallbackCode: Int): String {
        return try {
            if (body.isBlank()) {
                "Request failed ($fallbackCode)"
            } else {
                val json = JSONObject(body)
                json.optString("detail").ifBlank { "Request failed ($fallbackCode)" }
            }
        } catch (_: Exception) {
            "Request failed ($fallbackCode)"
        }
    }

    companion object {
        private const val PREFS_NAME = "d31337m3_android_auth"
        private const val KEY_TOKEN = "token"
        private const val KEY_EMAIL = "email"
    }
}
