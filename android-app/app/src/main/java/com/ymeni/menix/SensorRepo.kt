package com.ymeni.menix

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.delay
import org.json.JSONObject
import java.io.File

data class SensorSnapshot(
    val ch4: Double,
    val co: Int,
    val o2: Double,
    val temp: Double,
    val humidity: Int,
    val battery: Int,
    val ts: String,
) {
    val isAlert: Boolean
        get() = ch4 >= 1.0 || co >= 50 || o2 <= 19.5 || temp >= 40 || battery <= 15
}

object SensorRepo {

    // Termux écrit dans son sandbox. Pour partager, l'utilisateur fait :
    //   ln -s ~/menix-sentinel/data /sdcard/menix-sentinel/data
    private val LIVE_FILE = File("/sdcard/menix-sentinel/data/sensors_live.json")

    fun stream(periodMs: Long = 1000): Flow<SensorSnapshot?> = flow {
        while (true) {
            emit(read())
            delay(periodMs)
        }
    }.flowOn(Dispatchers.IO)

    private fun read(): SensorSnapshot? = try {
        if (!LIVE_FILE.exists()) null
        else {
            val j = JSONObject(LIVE_FILE.readText())
            SensorSnapshot(
                ch4      = j.optDouble("ch4_pct", 0.0),
                co       = j.optInt("co_ppm", 0),
                o2       = j.optDouble("o2_pct", 20.9),
                temp     = j.optDouble("temp_c", 22.0),
                humidity = j.optInt("humidity", 50),
                battery  = j.optInt("battery", 100),
                ts       = j.optString("ts", "")
            )
        }
    } catch (e: Exception) { null }
}
