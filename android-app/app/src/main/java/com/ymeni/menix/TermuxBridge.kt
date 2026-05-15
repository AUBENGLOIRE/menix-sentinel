package com.ymeni.menix

import android.content.ComponentName
import android.content.Context
import android.content.Intent

/**
 * Pont vers Termux : envoie une commande shell qui sera exécutée
 * dans l'environnement Termux (donc avec accès à python, ollama, etc.).
 *
 * Prérequis côté Termux :
 *   echo "allow-external-apps=true" >> ~/.termux/termux.properties
 */
object TermuxBridge {

    private const val TERMUX_PKG = "com.termux"
    private const val RUN_SERVICE = "com.termux.app.RunCommandService"
    private const val ACTION = "com.termux.RUN_COMMAND"

    fun run(ctx: Context, command: String, args: Array<String> = emptyArray()) {
        val intent = Intent().apply {
            setClassName(TERMUX_PKG, RUN_SERVICE)
            action = ACTION
            putExtra("com.termux.RUN_COMMAND_PATH", command)
            putExtra("com.termux.RUN_COMMAND_ARGUMENTS", args)
            putExtra("com.termux.RUN_COMMAND_WORKDIR",
                "/data/data/com.termux/files/home/menix-sentinel")
            putExtra("com.termux.RUN_COMMAND_BACKGROUND", true)
            putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0")
        }
        try {
            ctx.startForegroundService(intent)
        } catch (e: Exception) {
            // Termux pas installé ou permission RUN_COMMAND non accordée
            e.printStackTrace()
        }
    }

    // Raccourcis sémantiques
    fun torchOn(ctx: Context)  = run(ctx, "/data/data/com.termux/files/usr/bin/termux-torch", arrayOf("on"))
    fun torchOff(ctx: Context) = run(ctx, "/data/data/com.termux/files/usr/bin/termux-torch", arrayOf("off"))

    fun routerSay(ctx: Context, phrase: String) = run(
        ctx, "/data/data/com.termux/files/usr/bin/python3",
        arrayOf("/data/data/com.termux/files/home/menix-sentinel/core/router.py", phrase)
    )

    fun sos(ctx: Context)   = routerSay(ctx, "sos")
    fun photo(ctx: Context) = routerSay(ctx, "prends une photo")
    fun stop(ctx: Context)  = routerSay(ctx, "stop")
}
