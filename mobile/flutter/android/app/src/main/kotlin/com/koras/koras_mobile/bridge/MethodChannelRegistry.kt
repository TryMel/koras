package com.koras.koras_mobile.bridge

import android.content.Context
import android.content.Intent
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import android.provider.Settings
import com.koras.koras_mobile.accessibility.KorasAccessibilityService
import com.koras.koras_mobile.tools.AppTool
import com.koras.koras_mobile.tools.DeviceTool
import com.koras.koras_mobile.tools.ContactTool
import com.koras.koras_mobile.tools.CalendarTool
import com.koras.koras_mobile.tools.KorasNotificationListener
import com.koras.koras_mobile.tools.PhoneTool
import com.koras.koras_mobile.tools.SmsTool
import androidx.fragment.app.FragmentActivity
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Section 10.1 & 12 — Registry des canaux de communication Flutter <-> Kotlin.
 */
class MethodChannelRegistry(
    private val context: Context,
    private val activity: FragmentActivity,
    messenger: BinaryMessenger
) :
    MethodChannel.MethodCallHandler {

    private val methodChannel = MethodChannel(messenger, "com.koras.koras_mobile/methods")
    private val accessibilityChannel = MethodChannel(messenger, "com.koras.koras_mobile/accessibility")
    private val audioChannel = MethodChannel(messenger, "com.koras.koras_mobile/audio")

    private val phoneTool = PhoneTool(context)
    private val smsTool = SmsTool(context)
    private val appTool = AppTool(context)
    private val deviceTool = DeviceTool(context)
    private val contactTool = ContactTool(context)
    private val calendarTool = CalendarTool(context)

    init {
        methodChannel.setMethodCallHandler(this)
        accessibilityChannel.setMethodCallHandler { call, result ->
            handleAccessibilityCall(call, result)
        }
        audioChannel.setMethodCallHandler { call, result ->
            handleAudioCall(call, result)
        }
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "callContact" -> {
                val contactName = call.argument<String>("contactName") ?: ""
                val phoneNumber = call.argument<String>("phoneNumber") ?: contactTool.findPhoneNumber(contactName)
                if (phoneNumber == null) {
                    result.success(false)
                    return
                }
                val success = phoneTool.makeCall(phoneNumber)
                result.success(success)
            }
            "sendSms" -> {
                val contactName = call.argument<String>("contactName") ?: ""
                val phoneNumber = call.argument<String>("phoneNumber") ?: contactTool.findPhoneNumber(contactName)
                if (phoneNumber == null) {
                    result.success(false)
                    return
                }
                val message = call.argument<String>("message") ?: ""
                val success = smsTool.sendSmsDirect(phoneNumber, message)
                result.success(success)
            }
            "openApp" -> {
                val appName = call.argument<String>("appName") ?: ""
                val packageName = call.argument<String>("packageName")
                val success = appTool.launchAppByName(appName, packageName)
                result.success(success)
            }
            "openMaps" -> {
                val destination = call.argument<String>("destination") ?: ""
                val success = appTool.openMaps(destination)
                result.success(success)
            }
            "openUrl" -> result.success(appTool.openUrl(call.argument<String>("url") ?: ""))
            "searchWeb" -> result.success(appTool.searchWeb(call.argument<String>("query") ?: ""))
            "searchContacts" -> result.success(contactTool.search(call.argument<String>("query") ?: ""))
            "getBatteryLevel" -> {
                result.success(deviceTool.getBatteryLevel())
            }
            "isNetworkAvailable" -> {
                result.success(deviceTool.isNetworkAvailable())
            }
            "getDeviceInfo" -> {
                result.success(deviceTool.getDeviceInfo())
            }
            "isAccessibilityServiceConnected" -> {
                result.success(KorasAccessibilityService.isRunning())
            }
            "openNotificationListenerSettings" -> {
                result.success(openSettings(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
            }
            "openAccessibilitySettings" -> {
                result.success(openSettings(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            }
            "authenticateBiometric" -> {
                authenticateBiometric(call.argument<String>("reason") ?: "Confirmer cette action", result)
            }
            "readNotifications" -> {
                result.success(KorasNotificationListener.latest(call.argument<Int>("limit") ?: 3))
            }
            "isNotificationListenerConnected" -> {
                result.success(KorasNotificationListener.isConnected())
            }
            "createReminder" -> {
                result.success(calendarTool.createReminder(call.argument<String>("title") ?: ""))
            }
            "createEvent" -> result.success(calendarTool.createEvent(
                call.argument<String>("title") ?: "", call.argument<String>("description")
            ))
            else -> result.notImplemented()
        }
    }

    private fun openSettings(action: String): Boolean = try {
        context.startActivity(Intent(action).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        })
        true
    } catch (_: Exception) {
        false
    }

    private fun authenticateBiometric(reason: String, result: MethodChannel.Result) {
        val authenticators = BiometricManager.Authenticators.BIOMETRIC_WEAK
        val biometricManager = BiometricManager.from(context)
        if (biometricManager.canAuthenticate(authenticators) != BiometricManager.BIOMETRIC_SUCCESS) {
            result.error(
                "BIOMETRIC_UNAVAILABLE",
                "Aucune biométrie n'est configurée sur cet appareil.",
                null
            )
            return
        }

        val prompt = BiometricPrompt(
            activity,
            ContextCompat.getMainExecutor(activity),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(authResult: BiometricPrompt.AuthenticationResult) {
                    result.success(true)
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    if (errorCode == BiometricPrompt.ERROR_NEGATIVE_BUTTON ||
                        errorCode == BiometricPrompt.ERROR_USER_CANCELED ||
                        errorCode == BiometricPrompt.ERROR_CANCELED
                    ) {
                        result.success(false)
                    } else {
                        result.error("BIOMETRIC_ERROR", errString.toString(), errorCode)
                    }
                }
            }
        )
        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Confirmer l'action")
            .setSubtitle(reason)
            .setNegativeButtonText("Annuler")
            .setAllowedAuthenticators(authenticators)
            .build()
        prompt.authenticate(promptInfo)
    }

    private fun handleAccessibilityCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "readScreenContent" -> {
                val service = KorasAccessibilityService.instance?.get()
                if (service != null) {
                    result.success(service.readNormalizedScreen())
                } else {
                    result.success(mapOf("error" to "AccessibilityService not enabled"))
                }
            }
            "performClickByLabel" -> {
                val service = KorasAccessibilityService.instance?.get()
                result.success(service?.performClickByLabel(call.argument<String>("label") ?: "") ?: false)
            }
            "isServiceEnabled" -> {
                result.success(KorasAccessibilityService.isRunning())
            }
            else -> result.notImplemented()
        }
    }

    private fun handleAudioCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "startListening", "stopListening", "speak", "stopSpeaking" -> {
                result.success(true)
            }
            else -> result.notImplemented()
        }
    }
}
