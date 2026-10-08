package com.koras.koras_mobile.tools

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

/** Reads only notifications explicitly granted by the user in Android settings. */
class KorasNotificationListener : NotificationListenerService() {
    companion object {
        private var service: KorasNotificationListener? = null

        fun isConnected(): Boolean = service != null

        fun latest(limit: Int): List<Map<String, String>> = service?.activeNotifications
            ?.sortedByDescending { it.postTime }
            ?.take(limit.coerceIn(1, 10))
            ?.map(::toSafeMap)
            ?: emptyList()

        private fun toSafeMap(item: StatusBarNotification): Map<String, String> {
            val extras = item.notification.extras
            return mapOf(
                "package" to item.packageName,
                "title" to (extras.getCharSequence("android.title")?.toString() ?: ""),
                "text" to (extras.getCharSequence("android.text")?.toString() ?: ""),
                "posted_at" to item.postTime.toString(),
            )
        }
    }

    override fun onListenerConnected() { service = this }
    override fun onListenerDisconnected() { service = null }
}
